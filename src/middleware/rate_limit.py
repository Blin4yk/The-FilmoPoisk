"""Middleware для ограничения количества запросов."""
from typing import Any

from core.config import settings
from db.interface.interfaces import AbstractCache
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware для ограничения количества запросов."""

    def __init__(self, app: Any, cache: AbstractCache | None = None):
        """
        Инициализация middleware.

        Args:
            app: ASGI приложение
            cache: Кэш для хранения счетчиков (если None, будет получен из зависимости)
        """
        super().__init__(app)
        self.cache = cache
        self.rate_limit_per_minute = settings.rate_limit_per_minute
        self.rate_limit_per_hour = settings.rate_limit_per_hour

    async def dispatch(self, request: Request, call_next):
        """
        Проверить лимит запросов и обработать запрос.

        Args:
            request: Входящий запрос
            call_next: Следующий middleware/handler

        Returns:
            Ответ или ошибка 429 при превышении лимита
        """
        # Получаем IP адрес клиента
        client_ip = request.client.host if request.client else 'unknown'

        # Используем переданный кэш или получаем из модуля
        cache = self.cache
        if cache is None:
            from db.redis import redis

            if redis is None:
                # Если Redis недоступен, пропускаем rate limiting (graceful degradation)
                return await call_next(request)
            # Используем абстракцию AbstractCache (DIP)
            from db.interface.interfaces import AbstractCache
            from db.redis import RedisCache

            cache = RedisCache(redis)

        # Проверяем лимит в минуту
        minute_key = f'rate_limit:minute:{client_ip}'
        minute_count = await cache.get(minute_key)
        if minute_count:
            minute_count = int(minute_count)
            if minute_count >= self.rate_limit_per_minute:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        'detail': 'Превышен лимит запросов. Попробуйте позже.',
                        'retry_after': 60,
                    },
                    headers={'Retry-After': '60'},
                )
        else:
            minute_count = 0

        # Проверяем лимит в час
        hour_key = f'rate_limit:hour:{client_ip}'
        hour_count = await cache.get(hour_key)
        if hour_count:
            hour_count = int(hour_count)
            if hour_count >= self.rate_limit_per_hour:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        'detail': 'Превышен лимит запросов в час. Попробуйте позже.',
                        'retry_after': 3600,
                    },
                    headers={'Retry-After': '3600'},
                )
        else:
            hour_count = 0

        # Увеличиваем счетчики
        await cache.set(minute_key, str(minute_count + 1), expire=60)
        await cache.set(hour_key, str(hour_count + 1), expire=3600)

        # Обрабатываем запрос
        return await call_next(request)

