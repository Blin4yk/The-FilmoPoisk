from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import clickhouse_connect
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError


class KafkaToClickHouseETL:
    """ETL-сервис для переноса пользовательских событий из Kafka в ClickHouse."""

    def __init__(self) -> None:
        self._bootstrap_servers = 'kafka:9092'
        self._topic = 'user_events'
        self._group_id = 'user-events-etl'

        client_kwargs: dict[str, object] = {
            'host': 'clickhouse',
            'port': 8123,
            'username': 'user',
            'password': '12345',
        }

        max_retries = 10
        delay_seconds = 3
        last_error: Exception | None = None

        # for attempt in range(1, max_retries + 1):
        #     try:
        #         self._clickhouse_client = clickhouse_connect.get_client(**client_kwargs)
        #         last_error = None
        #         break
        #     except Exception as exc:  # noqa: BLE001
        #         last_error = exc
        #         if attempt == max_retries:
        #             raise
        #         print(f"Attempt {attempt}/{max_retries} to connect to ClickHouse failed: {exc}")
        #         time.sleep(delay_seconds)
        #
        # if last_error is not None:
        #     # Если по какой-то причине не вышли из цикла, пробрасываем последнюю ошибку
        #     raise last_error
        #
        # # 2. Инициализируем базу данных и таблицу
        # self._init_database()

        # 3. Теперь переподключаемся к базе analytics
        client_kwargs['database'] = 'analytics'
        for attempt in range(1, max_retries + 1):
            try:
                self._clickhouse_client = clickhouse_connect.get_client(**client_kwargs)
                last_error = None
                print("Successfully connected to ClickHouse database 'analytics'")
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt == max_retries:
                    raise
                print(f"Attempt {attempt}/{max_retries} to connect to analytics database failed: {exc}")
                time.sleep(delay_seconds)

        if last_error is not None:
            raise last_error

    def _init_database(self) -> None:
        """Инициализировать базу данных и таблицу в ClickHouse."""
        try:
            # Создаем базу данных если не существует
            self._clickhouse_client.command('CREATE DATABASE IF NOT EXISTS analytics')
            print("Database 'analytics' created or already exists")

            # Создаем таблицу если не существует
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
            print("Table 'analytics.user_events' created or already exists")

        except Exception as e:
            print(f"Error initializing database: {e}")
            # Не бросаем исключение дальше, чтобы ETL мог попробовать работать дальше
            # Возможно таблица уже создана другим инстансом

    async def run(self) -> None:
        """Запустить основной цикл чтения из Kafka и записи в ClickHouse."""
        consumer = AIOKafkaConsumer(
            self._topic,
            bootstrap_servers=self._bootstrap_servers,
            enable_auto_commit=True,
            group_id=self._group_id,
            auto_offset_reset='earliest',
        )

        max_retries = 10
        delay_seconds = 3

        await consumer.start()
        print(f"Subscribed topics: {consumer.subscription()}")
        print(f"Available topics: {await consumer.topics()}")

        # for attempt in range(1, max_retries + 1):
        #     try:
        #         await consumer.start()
        #         print(f"Successfully connected to Kafka topic '{self._topic}'")
        #         break
        #
        #     except KafkaConnectionError as e:
        #         if attempt == max_retries:
        #             print(f"Failed to connect to Kafka after {max_retries} attempts: {e}")
        #             raise
        #         print(f"Attempt {attempt}/{max_retries} to connect to Kafka failed, retrying...")
        #         await asyncio.sleep(delay_seconds)

        print("Connection established")

        try:
            async for msg in consumer:
                await self._handle_message(msg.value)
        finally:
            await consumer.stop()
            self._clickhouse_client.close()

    async def _handle_message(self, value: bytes) -> None:
        """Обработать одно сообщение Kafka и сохранить его в ClickHouse."""
        try:
            event: dict[str, Any] = json.loads(value.decode('utf-8'))
            print(event)
        except json.JSONDecodeError:
            # В реальном проекте здесь можно добавить логирование невалидных сообщений
            print("Failed to decode JSON message")
            return

        await asyncio.to_thread(self._insert_event, event)

    def _insert_event(self, event: dict[str, Any]) -> None:
        """Синхронная вставка события в ClickHouse (вызывается из отдельного потока)."""
        # Таблица предполагается следующей (DDL пример):
        # CREATE TABLE IF NOT EXISTS user_events (
        #     event_date      Date         DEFAULT toDate(timestamp),
        #     timestamp       DateTime,
        #     event_type      String,
        #     user_id         String,
        #     session_id      String,
        #     page            String,
        #     referrer        String,
        #     element_id      String,
        #     element_type    String,
        #     video_id        String,
        #     quality_from    String,
        #     quality_to      String,
        #     watched_full    UInt8,
        #     filter_type     String,
        #     filter_value    String,
        #     duration_ms     Int64,
        #     user_agent      String,
        #     ip_address      String,
        #     metadata        String
        # ) ENGINE = MergeTree()
        # ORDER BY (event_date, user_id, session_id, timestamp);

        try:
            # Подготовка данных для вставки
            row = {
                'timestamp': event.get('timestamp'),
                'event_type': event.get('event_type', ''),
                'user_id': (event.get('user_id') or '') if event.get('user_id') else '',
                'session_id': event.get('session_id', ''),
                'page': event.get('page') or '',
                'referrer': event.get('referrer') or '',
                'element_id': event.get('element_id') or '',
                'element_type': event.get('element_type') or '',
                'video_id': (event.get('video_id') or '') if event.get('video_id') else '',
                'quality_from': event.get('quality_from') or '',
                'quality_to': event.get('quality_to') or '',
                'watched_full': 1 if event.get('watched_full') else 0,
                'filter_type': event.get('filter_type') or '',
                'filter_value': event.get('filter_value') or '',
                'duration_ms': int(event.get('duration_ms') or 0),
                'user_agent': event.get('user_agent') or '',
                'ip_address': event.get('ip_address') or '',
                'metadata': json.dumps(event.get('metadata') or {}),
            }
            print(row.values())

            # Проверяем обязательные поля
            if not row['timestamp']:
                print("Warning: event missing timestamp")
                return

            self._clickhouse_client.insert(
                'user_events',
                [row],
                column_names=list(row.keys()),
            )

        except Exception as e:
            print(f"Error inserting event to ClickHouse: {e}")
            # Можно добавить логику для dead letter queue или повторных попыток


async def main() -> None:
    """Точка входа для запуска ETL-сервиса."""
    try:
        etl = KafkaToClickHouseETL()
        await etl.run()
    except Exception as e:
        print(f"ETL service failed with error: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())