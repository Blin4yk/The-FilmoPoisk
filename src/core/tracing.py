"""Настройка трассировки с Jaeger."""
import logging
from typing import Any

from core.config import settings
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


def setup_tracing(app: Any) -> None:
    """
    Настроить трассировку для приложения.

    Args:
        app: FastAPI приложение
    """
    try:
        # Создаем ресурс с именем сервиса
        resource = Resource.create({SERVICE_NAME: settings.jaeger_service_name})

        # Создаем провайдер трассировки
        trace.set_tracer_provider(TracerProvider(resource=resource))

        # Настраиваем экспортер Jaeger через UDP агент
        # В Docker используем имя сервиса 'jaeger' вместо 'localhost'
        jaeger_exporter = JaegerExporter(
            agent_host_name=settings.jaeger_agent_host,
            agent_port=settings.jaeger_agent_port,
        )

        # Добавляем процессор для экспорта спанов
        span_processor = BatchSpanProcessor(jaeger_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)

        # Инструментируем FastAPI
        FastAPIInstrumentor.instrument_app(app)

        # Инструментируем httpx для трассировки HTTP запросов
        HTTPXClientInstrumentor().instrument()

        logger.info('Трассировка Jaeger настроена успешно')
    except Exception as e:
        logger.warning(f'Не удалось настроить трассировку Jaeger: {e}')


def get_tracer(name: str | None = None):
    """
    Получить трейсер для создания спанов.

    Args:
        name: Имя трейсера (по умолчанию используется имя сервиса)

    Returns:
        Tracer объект
    """
    return trace.get_tracer(name or settings.jaeger_service_name)

