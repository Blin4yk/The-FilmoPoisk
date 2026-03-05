"""Инфраструктура очередей для сервиса нотификаций."""

from aiokafka import AIOKafkaProducer

from db import kafka


class NotificationPublisher:
    """Адаптер Kafka-продьюсера для публикации сообщений о нотификациях."""

    def __init__(self, producer: AIOKafkaProducer) -> None:
        self._producer = producer

    async def publish(self, topic: str, key: str | None, value: bytes) -> None:
        """Опубликовать сообщение в Kafka-топик."""
        key_bytes = key.encode('utf-8') if key is not None else None
        await self._producer.send_and_wait(topic, key=key_bytes, value=value)


async def get_notification_publisher() -> NotificationPublisher:
    """Вернуть инициализированный паблишер очереди нотификаций."""
    if kafka.kafka_producer is None:
        raise RuntimeError('Kafka producer не инициализирован')
    return NotificationPublisher(kafka.kafka_producer)
