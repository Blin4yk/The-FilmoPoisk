import asyncio
import json
import uuid
import logging
from datetime import datetime
from typing import Any

import clickhouse_connect
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError, KafkaError

from core.config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KafkaToClickHouseETL:
    """ETL-сервис для переноса пользовательских событий из Kafka в ClickHouse."""

    def __init__(self) -> None:
        self._bootstrap_servers = settings.kafka_bootstrap_servers
        self._topic = settings.kafka_user_events_topic
        self._group_id = 'user-events-etl'
        self._clickhouse_client = None

    async def _connect_to_clickhouse(self) -> None:
        """Подключиться к ClickHouse с повторными попытками."""
        client_kwargs = {
            'host': settings.clickhouse_host,
            'port': settings.clickhouse_port,
            'username': settings.clickhouse_user,
            'password': settings.clickhouse_password,
            'database': settings.clickhouse_database,
        }

        max_retries = 20
        delay_seconds = 5

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Попытка подключения к ClickHouse {attempt}/{max_retries}")
                self._clickhouse_client = clickhouse_connect.get_client(**client_kwargs)
                logger.info("Успешное подключение к ClickHouse")
                self._init_database()
                return

            except Exception as exc:
                if attempt == max_retries:
                    logger.error(f"Не удалось подключиться к ClickHouse после {max_retries} попыток")
                    raise
                logger.warning(f"Ошибка подключения: {exc}. Повтор через {delay_seconds} сек")
                await asyncio.sleep(delay_seconds)

    def _init_database(self) -> None:
        """Инициализировать базу данных и таблицу в ClickHouse."""
        try:
            check_table_query = """
            SELECT count() FROM system.tables 
            WHERE database = 'analytics' AND name = 'user_events'
            """
            table_exists = self._clickhouse_client.command(check_table_query)

            if int(table_exists) == 0:
                create_table_query = """
                CREATE TABLE IF NOT EXISTS analytics.user_events
                (
                    event_date   Date    DEFAULT toDate(timestamp),
                    timestamp    DateTime,
                    event_type   String,
                    user_id      String,
                    session_id   String,
                    page         String,
                    referrer     String,
                    element_id   String,
                    element_type String,
                    video_id     String,
                    quality_from String,
                    quality_to   String,
                    watched_full UInt8,
                    filter_type  String,
                    filter_value String,
                    duration_ms  Int64,
                    user_agent   String,
                    ip_address   String,
                    metadata     String
                )
                ENGINE = MergeTree()
                ORDER BY (event_date, user_id, session_id, timestamp)
                """
                self._clickhouse_client.command(create_table_query)
                logger.info("Таблица 'analytics.user_events' создана")
            else:
                logger.info("Таблица уже существует")

        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")

    async def _connect_to_kafka(self) -> AIOKafkaConsumer:
        """Подключиться к Kafka с повторными попытками."""
        consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap_servers,
            enable_auto_commit=True,
            group_id=self._group_id,
            auto_offset_reset='earliest',
            session_timeout_ms=10000,
            heartbeat_interval_ms=3000,
            max_poll_interval_ms=300000,
        )

        max_retries = 20
        delay_seconds = 5

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Попытка подключения к Kafka {attempt}/{max_retries}")
                await consumer.start()
                logger.info(f"Успешное подключение к топику '{self._topic}'")
                return consumer

            except (KafkaConnectionError, KafkaError) as e:
                if attempt == max_retries:
                    logger.error(f"Не удалось подключиться к Kafka после {max_retries} попыток")
                    raise
                logger.warning(f"Ошибка подключения: {e}. Повтор через {delay_seconds} сек")
                await asyncio.sleep(delay_seconds)

    async def run(self) -> None:
        """Запустить основной цикл чтения из Kafka и записи в ClickHouse."""
        await self._connect_to_clickhouse()
        consumer = await self._connect_to_kafka()

        logger.info("ETL сервис запущен. Ожидание сообщений...")

        try:
            async for msg in consumer:
                logger.debug(f"Получено сообщение: partition={msg.partition}, offset={msg.offset}")
                await self._handle_message(msg.value)
        except Exception as e:
            logger.error(f"Ошибка в цикле обработки: {e}")
            raise
        finally:
            await consumer.stop()
            if self._clickhouse_client:
                self._clickhouse_client.close()
            logger.info("ETL сервис остановлен")

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Преобразовать строку времени в datetime."""
        try:
            if 'T' in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except Exception:
            return datetime.now()

    async def _handle_message(self, value: bytes) -> None:
        """Обработать одно сообщение Kafka и сохранить его в ClickHouse."""
        try:
            event: dict[str, Any] = json.loads(value.decode('utf-8'))
            logger.info(f"Обработка события: {event.get('event_type', 'unknown')}")
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON: {e}")
            return

        await asyncio.to_thread(self._insert_event, event)

    def _insert_event(self, event: dict[str, Any]) -> None:
        """Синхронная вставка события в ClickHouse."""
        try:
            timestamp_str = event.get('timestamp')
            if timestamp_str:
                try:
                    timestamp = self._parse_timestamp(timestamp_str)
                except Exception:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()

            # Обработка UUID полей
            user_id = str(event.get('user_id', ''))
            video_id = str(event.get('video_id', ''))

            # Убираем пустые или некорректные UUID
            for field_value in [user_id, video_id]:
                if field_value and len(field_value) > 36:
                    field_value = field_value.strip('"').strip("'")
                try:
                    uuid.UUID(field_value)
                except (ValueError, AttributeError):
                    if field_value == user_id:
                        user_id = ''
                    else:
                        video_id = ''

            values = [
                timestamp,
                str(event.get('event_type', '')),
                user_id,
                str(event.get('session_id', '')),
                str(event.get('page', '')),
                str(event.get('referrer', '')),
                str(event.get('element_id', '')),
                str(event.get('element_type', '')),
                video_id,
                str(event.get('quality_from', '')),
                str(event.get('quality_to', '')),
                1 if event.get('watched_full') else 0,
                str(event.get('filter_type', '')),
                str(event.get('filter_value', '')),
                int(event.get('duration_ms', 0)),
                str(event.get('user_agent', '')),
                str(event.get('ip_address', '')),
                json.dumps(event.get('metadata') or {}),
            ]

            columns = [
                'timestamp', 'event_type', 'user_id', 'session_id', 'page',
                'referrer', 'element_id', 'element_type', 'video_id',
                'quality_from', 'quality_to', 'watched_full', 'filter_type',
                'filter_value', 'duration_ms', 'user_agent', 'ip_address', 'metadata'
            ]

            result = self._clickhouse_client.insert(
                'analytics.user_events',
                [values],
                column_names=columns,
                settings={'allow_experimental_lightweight_delete': 1}
            )

            logger.info(f"Событие сохранено. Записей: {result.written_rows}")

        except Exception as e:
            logger.error(f"Ошибка вставки в ClickHouse: {str(e)}")


async def main() -> None:
    """Точка входа для запуска ETL-сервиса."""
    logger.info("Запуск ETL сервиса Kafka -> ClickHouse...")

    try:
        etl = KafkaToClickHouseETL()
        await etl.run()
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")
    except Exception as e:
        logger.error(f"Ошибка в ETL сервисе: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())