import os
import sys
import time

import requests


def wait_for_elasticsearch():
    es_url = os.getenv('ELASTICSEARCH_URL', 'http://elasticsearch-with-dump:9200')
    health_url = f"{es_url}/_cluster/health"

    print(f"Waiting for Elasticsearch at {health_url}...")

    for i in range(30):
        try:
            response = requests.get(health_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') in ['green', 'yellow']:
                    print("Elasticsearch is ready!")
                    return True
        except requests.exceptions.RequestException as e:
            print(f"Attempt {i + 1}/30: Elasticsearch not ready yet - {e}")

        time.sleep(5)

    print("Timeout waiting for Elasticsearch")
    return False


def wait_for_redis():
    import redis
    redis_url = os.getenv('REDIS_URL', 'redis://redis:6379')

    print(f"Waiting for Redis at {redis_url}...")

    for i in range(30):
        try:
            r = redis.from_url(redis_url)
            r.ping()
            print("Redis is ready!")
            return True
        except Exception as e:
            print(f"Attempt {i + 1}/30: Redis not ready yet - {e}")

        time.sleep(5)

    print("Timeout waiting for Redis")
    return False


def wait_for_app(max_retries=30, delay=5):
    """Ожидание готовности приложения"""
    # Используем правильный docs_url
    app_url = "http://fastapi:8000/api/openapi"
    for i in range(max_retries):
        try:
            response = requests.get(app_url, timeout=5)
            if response.status_code == 200:
                print("App готов!")
                return True
            else:
                print(f"Попытка {i + 1}: App вернул статус {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Попытка {i + 1}/{max_retries}: App не готов - {e}")

        time.sleep(delay)

    print("Timeout waiting for App")
    return False


if __name__ == "__main__":
    print("Запуск health check...")

    # Ждем все сервисы
    es_ready = wait_for_elasticsearch()
    redis_ready = wait_for_redis()
    app_ready = wait_for_app()

    if es_ready and redis_ready and app_ready:
        print("Все сервисы подняты. Запускаем тесты...")
    else:
        print("Некоторые сервисы не запустились")
        sys.exit(1)
