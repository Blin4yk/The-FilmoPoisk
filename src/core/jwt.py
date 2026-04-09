"""Утилиты для раболты с JWT-токенами"""
import uuid
from datetime import datetime, timedelta, timezone

from core.config import settings
from jose import JWTError, jwt


class JWTService:
    """Сервис для операций с JWT токенами"""

    def __init__(self):
        """Инициализация JWT сервиса с настройками"""
        self.secret_key = settings.jwt_secret_key.get_secret_value()
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.access_token_expire_minutes
        self.refresh_token_expire_days = settings.refresh_token_expire_days

    def create_access_token(
        self,
        user_id: str,
        username: str,
        is_superuser: bool,
        roles: list[str],
        generation: int = 0,
    ) -> str:
        """
        Создать JWT access токен

        Returns:
            Закодированный JWT токен
        """
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=self.access_token_expire_minutes
        )
        payload = {
            'sub': user_id,
            'username': username,
            'is_superuser': is_superuser,
            'roles': roles,
            'generation': generation,
            'exp': expire,
            'iat': datetime.now(timezone.utc),
            'type': 'access',
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: str) -> tuple[str, str]:
        """
        Создать JWT refresh токен с JTI.

        Args:
            user_id: UUID пользователя в виде строки

        Returns:
            Кортеж из (токен, jti)
        """
        expire = datetime.now(timezone.utc) + timedelta(
            days=self.refresh_token_expire_days
        )
        jti = str(uuid.uuid4())
        payload = {
            'sub': user_id,
            'jti': jti,
            'exp': expire,
            'iat': datetime.now(timezone.utc),
            'type': 'refresh',
        }
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token, jti

    def decode_token(self, token: str) -> dict[str, any] | None:
        """
        Декодировать и валидировать JWT токен.

        Args:
            token: JWT токен в виде строки

        Returns:
            Декодированный payload или None если токен невалиден
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            return None

    def verify_token(
        self, token: str, token_type: str = 'access'
    ) -> dict[str, any] | None:
        """
        Проверить токен и его тип.

        Args:
            token: JWT токен в виде строки
            token_type: Ожидаемый тип токена ('access' или 'refresh')

        Returns:
            Декодированный payload или None если токен невалиден
        """
        payload = self.decode_token(token)
        if payload and payload.get('type') == token_type:
            exp = payload.get('exp')
            if exp and datetime.now(timezone.utc).timestamp() > exp:
                return None
            return payload
        return None


jwt_service = JWTService()
