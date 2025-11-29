import os
import sys
import time

import requests

from tests.logger import LOGGING


def wait_for_elasticsearch():
    es_url = os.getenv('ELASTICSEARCH_URL', 'http://elasticsearch-with-dump:9200')
    health_url = f"{es_url}/_cluster/health"

    LOGGING(f"Ожидание Elasticsearch {health_url}...")

    for i in range(30):
        try:
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') in ['green', 'yellow']:
                    LOGGING("Elasticsearch is ready!")
                    return True
        except requests.exceptions.RequestException as e:
            LOGGING(f"Попытка {i + 1}/30: Elasticsearch не готов - {e}")

        time.sleep(5)

    LOGGING("Таймаут ожидания Elasticsearch")
    return False


def wait_for_redis():
    import redis
    redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')

    LOGGING(f"Ожидание Redis {redis_url}...")

    for i in range(30):
        try:
            r = redis.from_url(redis_url)
            r.ping()
            LOGGING("Redis is ready!")
            return True
        except Exception as e:
            LOGGING(f"Попытка {i + 1}/30: Redis не готов - {e}")

        time.sleep(5)

    LOGGING("Таймаут ожидания Redis")
    return False


def wait_for_app(max_retries=30, delay=5):
    """Ожидание готовности приложения"""
    # Используем правильный docs_url
    app_url = "http://fastapi:8000/api/openapi"
    for i in range(max_retries):
        try:
            response = requests.get(app_url, timeout=5)
            if response.status_code == 200:
                LOGGING("App готов!")
                return True
            else:
                LOGGING(f"Попытка {i + 1}: App вернул статус {response.status_code}")
        except requests.exceptions.RequestException as e:
            LOGGING(f"Попытка {i + 1}/{max_retries}: App не готов - {e}")

        time.sleep(delay)

    LOGGING("Таймаут ожидания App")
    return False


if __name__ == "__main__":
    LOGGING("Запуск health check...")

    # Ждем все сервисы
    es_ready = wait_for_elasticsearch()
    redis_ready = wait_for_redis()
    app_ready = wait_for_app()

    if es_ready and redis_ready and app_ready:
        LOGGING("Все сервисы подняты. Запускаем тесты...")
    else:
        LOGGING("Некоторые сервисы не запустились")
        sys.exit(1)
