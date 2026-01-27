"""HTTP клиент для интеграции с Auth-сервисом с поддержкой graceful degradation."""
import logging
from typing import Any
from uuid import UUID

from core.config import settings


logger = logging.getLogger(__name__)


class AuthServiceClient:
    """HTTP клиент для взаимодействия с Auth-сервисом (SRP - только работа с Auth API)."""

    def __init__(self, base_url: str | None = None, timeout: float = 5.0):
        """
        Инициализация клиента Auth-сервиса.

        Args:
            base_url: Базовый URL Auth-сервиса. Если None, используется из настроек.
            timeout: Таймаут запросов в секундах
        """
        self.base_url = base_url or getattr(
            settings, 'auth_service_url', 'http://localhost:8000'
        )
        self.http_client = BaseHTTPClient(self.base_url, timeout)

    async def verify_token(
        self, token: str, request_id: str | None = None
    ) -> dict[str, Any] | None:
        """
        Проверить токен через Auth-сервис.

        Args:
            token: JWT токен для проверки
            request_id: ID запроса для трассировки

        Returns:
            Словарь с данными пользователя или None при ошибке/недоступности сервиса
        """
        headers = {}
        if request_id:
            headers['x-request-id'] = request_id
        headers['Authorization'] = f'Bearer {token}'

        try:
            response = await self.http_client.get('/api/v1/auth/verify', headers=headers)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.warning('Токен невалиден')
                return None
            else:
                logger.warning(
                    f'Неожиданный статус от Auth-сервиса: {response.status_code}'
                )
                return None
        except (HTTPClientTimeoutError, HTTPClientConnectionError):
            # Graceful degradation - возвращаем None вместо исключения
            return None
        except HTTPClientError as e:
            logger.error(f'Ошибка при обращении к Auth-сервису: {e}')
            return None

    async def get_user_info(
        self, user_id: UUID, request_id: str | None = None
    ) -> dict[str, Any] | None:
        """
        Получить информацию о пользователе.

        Args:
            user_id: UUID пользователя
            request_id: ID запроса для трассировки

        Returns:
            Словарь с данными пользователя или None при ошибке/недоступности сервиса
        """
        headers = {}
        if request_id:
            headers['x-request-id'] = request_id

        try:
            response = await self.http_client.get(
                f'/api/v1/auth/users/{user_id}', headers=headers
            )
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.warning(f'Пользователь {user_id} не найден')
                return None
            else:
                logger.warning(
                    f'Неожиданный статус от Auth-сервиса: {response.status_code}'
                )
                return None
        except (HTTPClientTimeoutError, HTTPClientConnectionError):
            # Graceful degradation
            return None
        except HTTPClientError as e:
            logger.error(f'Ошибка при обращении к Auth-сервису: {e}')
            return None

    async def check_permission(
        self,
        user_id: UUID,
        permission: str,
        request_id: str | None = None,
    ) -> bool:
        """
        Проверить разрешение пользователя.

        Args:
            user_id: UUID пользователя
            permission: Название разрешения
            request_id: ID запроса для трассировки

        Returns:
            True если разрешение есть, False если нет или сервис недоступен
        """
        headers = {}
        if request_id:
            headers['x-request-id'] = request_id

        try:
            response = await self.http_client.post(
                '/api/v1/auth/check-permission',
                headers=headers,
                json={'user_id': str(user_id), 'permission': permission},
            )
            if response.status_code == 200:
                result = response.json()
                return result.get('has_permission', False)
            else:
                logger.warning(
                    f'Неожиданный статус от Auth-сервиса: {response.status_code}'
                )
                return False
        except (HTTPClientTimeoutError, HTTPClientConnectionError):
            # Graceful degradation - возвращаем False
            return False
        except HTTPClientError as e:
            logger.error(f'Ошибка при обращении к Auth-сервису: {e}')
            return False

    async def close(self):
        """Закрыть HTTP клиент."""
        await self.http_client.close()

