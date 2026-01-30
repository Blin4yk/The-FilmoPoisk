from abc import ABC, abstractmethod

import requests
from jose import jwt
from requests_oauthlib import OAuth2Session

from core.config import oauth_settings
from core.security import get_password_hash
from db.postgres import AsyncSessionLocal
from db.repositories.user_repository import UserRepository


class OAuthProvider(ABC):
    """Абстрактный класс для OAuth провайдеров"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Имя провайдера (yandex, google, vk и т.д.)"""
        pass

    @abstractmethod
    def get_authorization_url(self, redirect_uri: str) -> str:
        """Получить URL для авторизации"""
        pass

    @abstractmethod
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> dict[str, any]:
        """Обменять код на токен"""
        pass

    @abstractmethod
    async def get_user_info(self, access_token: str) -> dict[str, any]:
        """Получить информацию о пользователе"""
        pass


class YandexOAuthProvider(OAuthProvider):
    """Реализация OAuth для Яндекс"""

    def __init__(self):
        self.provider_name = "yandex"
        self.client_id = oauth_settings.oauth_yandex_client_id
        self.client_secret = oauth_settings.oauth_yandex_client_secret
        self.authorization_base_url = "https://oauth.yandex.ru/authorize"
        self.token_url = "https://oauth.yandex.ru/token"
        self.user_info_url = "https://login.yandex.ru/info"

    @property
    def provider_name(self) -> str:
        return self.provider_name

    def get_authorization_url(self, redirect_uri: str) -> str:
        oauth = OAuth2Session(
            self.client_id,
            redirect_uri=redirect_uri,
            scope=["login:email", "login:info"]
        )
        authorization_url, _ = oauth.authorization_url(self.authorization_base_url)
        return authorization_url

    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> dict[str, any]:
        oauth = OAuth2Session(self.client_id, redirect_uri=redirect_uri)
        token = oauth.fetch_token(
            self.token_url,
            client_secret=self.client_secret,
            code=code
        )
        return token

    async def get_user_info(self, access_token: str) -> dict[str, any]:
        # Получаем JWT токен с информацией о пользователе
        jwt_url = "https://login.yandex.ru/info?format=jwt"
        headers = {"Authorization": f"OAuth {access_token}"}
        response = requests.get(jwt_url, headers=headers)
        response.raise_for_status()

        # Декодируем JWT
        payload = jwt.decode(
            response.text,
            self.client_secret,
            algorithms=["HS256"]
        )

        return {
            "email": payload.get("email"),
            "display_name": payload.get("display_name"),
        }

    @provider_name.setter
    def provider_name(self, value):
        self._provider_name = value


class OAuthProviderFactory:
    """Фабрика для создания провайдеров OAuth"""

    _providers = {}

    @classmethod
    def register_provider(cls, provider_name: str, provider_class):
        """Зарегистрировать провайдер"""
        cls._providers[provider_name] = provider_class

    @classmethod
    def get_provider(cls, provider_name: str) -> OAuthProvider:
        """Получить экземпляр провайдера"""
        if provider_name not in cls._providers:
            raise ValueError(f"Провайдер {provider_name} не поддерживается")

        return cls._providers[provider_name]()

    @classmethod
    def get_available_providers(cls) -> list:
        """Получить список доступных провайдеров"""
        return list(cls._providers.keys())


# Регистрируем провайдер Яндекс
OAuthProviderFactory.register_provider("yandex", YandexOAuthProvider)


async def register_oauth_user(
        user_data: dict[str, any],
        password: str | None = None
) -> tuple[bool, any]:
    """
    Регистрация пользователя через OAuth

    Args:
        user_data: Данные пользователя от провайдера
        password: Пароль (опционально)

    Returns:
        Tuple[создан ли новый пользователь, данные пользователя]
    """
    async with AsyncSessionLocal() as session:
        user_repo = UserRepository(session)

        email = user_data["email"]

        # Сначала ищем по email
        existing_user = None
        if email:
            existing_user = await user_repo.get_by_email(email=email)

        if existing_user:
            return False, existing_user

        # Создаем нового пользователя
        display_name = user_data["display_name"]

        hashed_password = get_password_hash(password)

        new_user = await user_repo.create(
            username=display_name,
            email=email,
            password_hash=hashed_password,
            # TODO: Добавить поля для OAuth (provider_id, provider_name и т.д.)
        )

        return True, new_user