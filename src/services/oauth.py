"""Сервис для OAuth аутентификации через социальные сети."""
import logging
import secrets
from datetime import datetime, timedelta
from starlette.exceptions import HTTPException
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
import requests
from jose import jwt
from core.config import settings
from core.jwt import jwt_service
from core.security import get_password_hash
from db.interface.interfaces import AbstractCache
from db.postgres import AsyncSessionLocal
from db.repositories.login_history_repository import LoginHistoryRepository
from db.repositories.refresh_token_repository import RefreshTokenRepository
from db.repositories.role_repository import RoleRepository
from db.repositories.user_repository import UserRepository
from models.user import User

logger = logging.getLogger(__name__)


def jwt_token(token: str):
    jwt_url = "https://login.yandex.ru/info?format=jwt"
    headers = {"Authorization": f"OAuth {token}"}
    response = requests.get(jwt_url, headers=headers)

    return response.text


def user_info(jwt_token: str):
    payload = jwt.decode(jwt_token, settings.oauth_yandex_client_secret, algorithms=["HS256"])

    dict_info = {
        "display_name": payload["display_name"],
        "email": payload["email"],
        "exp": payload["exp"],
    }

    return dict_info

async def register_yandex_user(access_token: str, password: str):
    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)
        user_data = user_info(jwt_token(access_token))
        email = user_data["email"]
        username = user_data["display_name"]


        exiting_user = await user_repo.get_by_email(email=email)

        if exiting_user:
            raise HTTPException(status_code=409, detail="Email already registered")
        hashed_password = get_password_hash(password)
        await user_repo.create(username=username, email=email, password_hash=hashed_password)

class OAuthService:
    """Сервис для OAuth аутентификации."""

    def __init__(self, session: AsyncSession, cache: AbstractCache):
        self.session = session
        self.cache = cache
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.login_history_repo = LoginHistoryRepository(session)
        self.refresh_token_repo = RefreshTokenRepository(session)

    async def authenticate_yandex(
            self, code: str, ip_address: str | None = None, user_agent: str | None = None
    ) -> tuple[User, str, str] | None:
        """Аутентификация через Yandex OAuth."""
        try:
            async with httpx.AsyncClient() as client:
                # Обмен кода на токен
                token_resp = await client.post(
                    'https://oauth.yandex.ru/token',
                    data={
                        'grant_type': 'authorization_code',
                        'code': code,
                        'client_id': settings.oauth_yandex_client_id,
                        'client_secret': settings.oauth_yandex_client_secret,
                    },
                )
                if token_resp.status_code != 200:
                    return None

                token_data = token_resp.json()
                access_token = token_data.get('access_token')
                if not access_token:
                    return None

                # Получение информации о пользователе
                user_resp = await client.get(
                    'https://login.yandex.ru/info',
                    headers={'Authorization': f'OAuth {access_token}'},
                )
                if user_resp.status_code != 200:
                    return None

                user_info = user_resp.json()
                email = user_info.get('default_email')
                username = user_info.get('login') or user_info.get('display_name', 'yandex_user')
                yandex_id = user_info.get('id')

                if not email or not yandex_id:
                    return None

                user = await self._get_or_create_user(email, f'{username}_{str(yandex_id)[:8]}')
                return await self._create_tokens(user, ip_address, user_agent)

        except Exception as e:
            logger.error(f'Ошибка OAuth Yandex: {e}', exc_info=True)
            return None

    async def _get_or_create_user(self, email: str, username: str) -> User:
        """Получить или создать пользователя."""
        user = await self.user_repo.get_by_email(email)
        if not user:
            password_hash = get_password_hash(secrets.token_urlsafe(32))
            user = await self.user_repo.create(
                username=username, email=email, password_hash=password_hash
            )
        return user

    async def _create_tokens(
            self, user: User, ip_address: str | None = None, user_agent: str | None = None
    ) -> tuple[User, str, str]:
        """Создать JWT токены для пользователя."""
        roles = await self.role_repo.get_user_roles(user.id)
        role_names = [role.name for role in roles]
        generation = await self._get_user_generation(user.id)

        access_token = jwt_service.create_access_token(
            user_id=str(user.id),
            username=user.username,
            is_superuser=user.is_superuser,
            roles=role_names,
            generation=generation,
        )
        refresh_token, jti = jwt_service.create_refresh_token(str(user.id))

        expires_at = datetime.utcnow() + timedelta(days=jwt_service.refresh_token_expire_days)
        await self.refresh_token_repo.create(user.id, jti, expires_at)
        await self.login_history_repo.create(user.id, ip_address, user_agent)

        return user, access_token, refresh_token

    async def _get_user_generation(self, user_id: UUID) -> int:
        """Получить номер поколения пользователя."""
        cache_key = f'user:generation:{user_id}'
        cached = await self.cache.get(cache_key)
        return int(cached) if cached else 0
