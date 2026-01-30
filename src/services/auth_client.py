"""Универсальная OAuth реализация по аналогии со статьей Мигеля Гринберга"""

from abc import ABC, abstractmethod
import aiohttp
from urllib.parse import urlencode
from core.config import settings


class OAuthSignIn(ABC):
    """Абстрактный базовый класс для OAuth провайдеров (аналог из статьи)"""

    def __init__(self):
        self.provider_name = self.__class__.__name__.replace('SignIn', '').lower()
        credentials = self._get_credentials()
        self.client_id = credentials.get('id')
        self.client_secret = credentials.get('secret')

    def _get_credentials(self) -> dict[str, str]:
        """Получить credentials из настроек (аналог из статьи)"""
        # В settings можно хранить так же, как в статье:
        # OAUTH_CREDENTIALS = {
        #     'yandex': {'id': '...', 'secret': '...'},
        #     'google': {'id': '...', 'secret': '...'}
        # }
        return getattr(settings, 'oauth_credentials', {}).get(self.provider_name, {})

    @abstractmethod
    async def authorize(self, callback_url: str) -> str:
        """Получить URL для перенаправления на авторизацию (аналог authorize())"""
        ...

    @abstractmethod
    async def callback(self, callback_url: str, **kwargs) -> tuple[str, str | None, str | None]:
        """
        Обработать callback от провайдера (аналог callback()).

        Returns:
            Tuple[social_id, email, username]
        """
        ...


class YandexSignIn(OAuthSignIn):
    """Реализация OAuth для Яндекс (аналог FacebookSignIn/TwitterSignIn из статьи)"""

    def __init__(self):
        super().__init__()
        self.authorize_url = "https://oauth.yandex.ru/authorize"
        self.token_url = "https://oauth.yandex.ru/token"
        self.user_info_url = "https://login.yandex.ru/info"

    async def authorize(self, callback_url: str) -> str:
        """Получить URL для авторизации в Яндекс"""
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": callback_url,
            "force_confirm": "true",  # Всегда запрашивать подтверждение
        }

        return f"{self.authorize_url}?{urlencode(params)}"

    async def callback(self, callback_url: str, **kwargs) -> tuple[str, str | None, str | None]:
        """Обработать callback от Яндекс"""
        code = kwargs.get('code')
        if not code:
            raise ValueError("Код авторизации не предоставлен")

        # Получаем access token
        token_data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        async with aiohttp.ClientSession() as session:
            # Получаем access token
            async with session.post(self.token_url, data=token_data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ошибка получения токена: {error_text}")

                token_response = await response.json()
                access_token = token_response.get("access_token")

                if not access_token:
                    raise Exception("Access token не получен")

            # Получаем информацию о пользователе
            headers = {"Authorization": f"OAuth {access_token}"}
            async with session.get(self.user_info_url, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Ошибка получения информации: {error_text}")

                user_info = await response.json()

                social_id = str(user_info.get("id"))
                email = user_info.get("default_email")
                username = user_info.get("login")

                return social_id, email, username