"""Точка входа для запуска воркера нотификаций."""

import asyncio

from aiokafka import AIOKafkaConsumer

from core.config import kafka_settings
from db import kafka
from db.mongo import close_mongo, init_mongo
from workers.notification_worker import NotificationWorker


async def main() -> None:
    """Запустить воркер чтения очереди нотификаций."""
    consumer = AIOKafkaConsumer(
        kafka_settings.kafka_notifications_topic,
        bootstrap_servers=kafka_settings.kafka_bootstrap_servers,
        group_id='notification-workers',
        auto_offset_reset='earliest',
    )

    mongo_initialized = False
    try:
        await kafka.init_kafka_producer()
        if kafka.kafka_producer is None:
            raise RuntimeError('Kafka producer не инициализирован для воркера нотификаций')

        mongo_db = await init_mongo()
        mongo_initialized = True

        worker = NotificationWorker(
            consumer=consumer,
            producer=kafka.kafka_producer,
            mongo_db=mongo_db,
            auth_service_url=kafka_settings.auth_service_url,
        )
        await worker.run_forever()
    finally:
        await consumer.stop()
        await kafka.close_kafka_producer()
        if mongo_initialized:
            await close_mongo()


if __name__ == '__main__':
    asyncio.run(main())
