"""Инфраструктурный слой для работы с Kafka."""

import asyncio
from typing import Final

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError

from core.config import kafka_settings
from db.interface.interfaces import AbstractEventPublisher


class KafkaEventPublisher(AbstractEventPublisher):
    """Реализация AbstractEventPublisher для Kafka."""

    def __init__(self, producer: AIOKafkaProducer) -> None:
        self._producer = producer

    async def publish(self, topic: str, key: str | None, value: bytes) -> None:
        key_bytes = key.encode('utf-8') if key is not None else None
        await self._producer.send_and_wait(topic, value=value, key=key_bytes)


kafka_producer: AIOKafkaProducer | None = None

_MAX_RETRIES: Final[int] = 10
_RETRY_DELAY_SECONDS: Final[int] = 3


async def init_kafka_producer() -> None:
    """Инициализировать глобальный AIOKafkaProducer"""
    global kafka_producer
    if kafka_producer is not None:
        return

    producer = AIOKafkaProducer(
        bootstrap_servers=kafka_settings.kafka_bootstrap_servers,
        value_serializer=lambda v: v,
    )

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            await producer.start()
            kafka_producer = producer
            break
        except KafkaConnectionError:
            if attempt == _MAX_RETRIES:
                raise
            await asyncio.sleep(_RETRY_DELAY_SECONDS)


async def close_kafka_producer() -> None:
    """Корректно завершить работу продьюсера Kafka."""
    global kafka_producer
    if kafka_producer is None:
        return

    await kafka_producer.stop()
    kafka_producer = None


async def get_event_publisher() -> AbstractEventPublisher:
    """Фабрика зависимостей для получения продьюсера событий."""
    if kafka_producer is None:
        raise RuntimeError('Kafka producer не инициализирован')

    return KafkaEventPublisher(kafka_producer)

