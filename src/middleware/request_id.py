"""Middleware для обработки x-request-id заголовка."""
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware для добавления и передачи x-request-id заголовка."""

    async def dispatch(self, request: Request, call_next):
        """
        Обработать запрос и добавить x-request-id если его нет.

        Args:
            request: Входящий запрос
            call_next: Следующий middleware/handler

        Returns:
            Ответ с заголовком x-request-id
        """
        # Получаем x-request-id из заголовков или создаем новый
        request_id = request.headers.get('x-request-id')
        if not request_id:
            request_id = str(uuid.uuid4())

        # Добавляем в state для использования в обработчиках
        request.state.request_id = request_id

        # Вызываем следующий middleware/handler
        response: Response = await call_next(request)

        # Добавляем x-request-id в заголовки ответа
        response.headers['x-request-id'] = request_id

        return response


