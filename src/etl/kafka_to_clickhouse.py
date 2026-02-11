import asyncio
import json
import uuid
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any

import clickhouse_connect
from aiokafka import AIOKafkaConsumer, TopicPartition
from aiokafka.errors import KafkaConnectionError, KafkaError


from core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KafkaToClickHouseETL:
    """ETL-сервис с пакетной записью в ClickHouse и ручным коммитом смещений Kafka."""

    def __init__(self) -> None:
        self._bootstrap_servers = settings.kafka_bootstrap_servers
        self._topic = settings.kafka_user_events_topic
        self._group_id = 'user-events-etl'
        self._clickhouse_client = None
        self._consumer = None

        # Параметры батчинга
        self._batch_max_size = 1000
        self._batch_max_seconds = 5.0
        self._batch: list[dict[str, Any]] = []
        self._last_batch_time = 0.0
        self._pending_offsets: dict[TopicPartition, int] = {}
        self._batch_lock = asyncio.Lock()

    async def _connect_to_clickhouse(self) -> None:
        """Подключение к ClickHouse с повторными попытками."""
        client_kwargs = {
            'host': settings.clickhouse_host,
            'port': settings.clickhouse_port,
            'username': settings.clickhouse_user,
            'password': settings.clickhouse_password,
            'database': settings.clickhouse_database,
        }

        max_retries = 20
        delay = 5

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Попытка подключения к ClickHouse {attempt}/{max_retries}")
                self._clickhouse_client = clickhouse_connect.get_client(**client_kwargs)
                logger.info("Успешное подключение к ClickHouse")
                self._init_database()
                return
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"Не удалось подключиться к ClickHouse после {max_retries} попыток")
                    raise
                logger.warning(f"Ошибка: {e}. Повтор через {delay} сек")
                await asyncio.sleep(delay)

    def _init_database(self) -> None:
        """Инициализация таблицы в ClickHouse, если её нет."""
        try:
            check_query = """
            SELECT count() FROM system.tables 
            WHERE database = 'analytics' AND name = 'user_events'
            """
            exists = self._clickhouse_client.command(check_query)

            if int(exists) == 0:
                create_query = """
                CREATE TABLE IF NOT EXISTS analytics.user_events
                (
                    event_date   Date DEFAULT toDate(timestamp),
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
                self._clickhouse_client.command(create_query)
                logger.info("Таблица 'analytics.user_events' создана")
            else:
                logger.info("Таблица уже существует")
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            raise

    async def _connect_to_kafka(self) -> AIOKafkaConsumer:
        """Подключение к Kafka с ручным управлением смещениями."""
        consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap_servers,
            enable_auto_commit=False,
            group_id=self._group_id,
            auto_offset_reset='earliest',
            session_timeout_ms=10000,
            heartbeat_interval_ms=3000,
            max_poll_interval_ms=300000,
            max_poll_records=self._batch_max_size,  # максимум записей за один poll
        )

        max_retries = 20
        delay = 5

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
                logger.warning(f"Ошибка: {e}. Повтор через {delay} сек")
                await asyncio.sleep(delay)

    async def _flush_batch(self) -> None:
        """
        Отправка текущего батча в ClickHouse и коммит смещений при успехе.
        Выполняется под защитой блокировки.
        """
        async with self._batch_lock:
            if not self._batch:
                return

            events = self._batch.copy()
            offsets = self._pending_offsets.copy()
            batch_size = len(events)

            logger.info(f"Отправка батча из {batch_size} событий в ClickHouse...")

            try:
                # Вставка в ClickHouse
                await asyncio.to_thread(self._insert_batch, events)
                logger.info(f"Батч из {batch_size} событий сохранён")

                # Коммит смещений в Kafka
                await self._consumer.commit(offsets)
                logger.debug(f"Смещения закоммичены: {offsets}")

                self._batch.clear()
                self._pending_offsets.clear()
                self._last_batch_time = asyncio.get_event_loop().time()

            except Exception as e:
                logger.error(f"Ошибка вставки батча: {e}. Повторная попытка позже.")
                raise

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Безопасный парсинг временной метки."""
        try:
            if 'T' in timestamp_str:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except Exception:
            return datetime.now()

    def _prepare_row(self, event: dict[str, Any]) -> list[Any]:
        """Преобразование события в строку для вставки."""
        ts_str = event.get('timestamp')
        timestamp = self._parse_timestamp(ts_str) if ts_str else datetime.now()

        user_id = str(event.get('user_id', ''))
        video_id = str(event.get('video_id', ''))

        for val in (user_id, video_id):
            if val and len(val) > 36:
                val = val.strip('"').strip("'")
            try:
                uuid.UUID(val)
            except (ValueError, AttributeError):
                if val == user_id:
                    user_id = ''
                else:
                    video_id = ''

        return [
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

    def _insert_batch(self, events: list[dict[str, Any]]) -> None:
        """Синхронная вставка пачки событий в ClickHouse."""
        columns = [
            'timestamp', 'event_type', 'user_id', 'session_id', 'page',
            'referrer', 'element_id', 'element_type', 'video_id',
            'quality_from', 'quality_to', 'watched_full', 'filter_type',
            'filter_value', 'duration_ms', 'user_agent', 'ip_address', 'metadata'
        ]

        rows = [self._prepare_row(event) for event in events]

        result = self._clickhouse_client.insert(
            'analytics.user_events',
            rows,
            column_names=columns,
            settings={'allow_experimental_lightweight_delete': 1}
        )

        if result.written_rows != len(events):
            raise ValueError(f"Вставлено {result.written_rows} строк вместо {len(events)}")

    async def _periodic_flush(self) -> None:
        """Фоновая задача: принудительный сброс по таймауту."""
        while True:
            await asyncio.sleep(self._batch_max_seconds)
            # Проверка условие без захвата блокировки
            if self._batch and (asyncio.get_event_loop().time() - self._last_batch_time) >= self._batch_max_seconds:
                logger.info(f"Таймаут: сброс батча из {len(self._batch)} событий")
                await self._flush_batch()

    async def run(self) -> None:
        """Основной цикл ETL: чтение пачек из Kafka и накопление батча."""
        await self._connect_to_clickhouse()

        self._consumer = await self._connect_to_kafka()
        self._last_batch_time = asyncio.get_event_loop().time()

        flush_task = asyncio.create_task(self._periodic_flush())

        logger.info("ETL сервис запущен. Режим: getmany, пакетная запись, ручной коммит.")

        try:
            while True:
                # Получаем пачку сообщений
                batch_dict = await self._consumer.getmany(
                    timeout_ms=1000,
                    max_records=self._batch_max_size
                )

                if not batch_dict:
                    await asyncio.sleep(0.1)
                    continue

                # Обрабатываем все полученные сообщения
                tp_to_max_offset = defaultdict(int)

                for tp, messages in batch_dict.items():
                    for msg in messages:
                        try:
                            event = json.loads(msg.value.decode('utf-8'))
                        except json.JSONDecodeError:
                            logger.warning(f"Ошибка декодирования JSON, offset={msg.offset}")
                            continue

                        async with self._batch_lock:
                            self._batch.append(event)
                            # Запоминаем максимальное смещение для данной партиции
                            tp_to_max_offset[tp] = max(tp_to_max_offset[tp], msg.offset + 1)

                # глобальный словарь ожидающих коммита смещений
                async with self._batch_lock:
                    for tp, offset in tp_to_max_offset.items():
                        self._pending_offsets[tp] = max(self._pending_offsets.get(tp, 0), offset)

                    # сбрасываем батч
                    if len(self._batch) >= self._batch_max_size:
                        logger.info(f"Достигнут лимит размера: {len(self._batch)} событий")
                        await self._flush_batch()

        except Exception as e:
            logger.error(f"Критическая ошибка в цикле ETL: {e}")
            raise
        finally:
            # Финальный сброс перед остановкой
            await self._flush_batch()
            flush_task.cancel()
            await self._consumer.stop()
            if self._clickhouse_client:
                self._clickhouse_client.close()
            logger.info("ETL сервис остановлен")


async def main() -> None:
    """Точка входа."""
    logger.info("Запуск ETL сервиса Kafka -> ClickHouse (batch + manual commit + getmany)")

    try:
        etl = KafkaToClickHouseETL()
        await etl.run()
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())