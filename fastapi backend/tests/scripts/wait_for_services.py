import logging
import sys
import time

import requests
from redis import Redis


def wait_for_elasticsearch(max_retries=30, delay=2):
    """Ожидание готовности Elasticsearch"""
    es_url = "http://elasticsearch:9200"
    for i in range(max_retries):
        try:
            response = requests.get(es_url)
            if response.status_code == 200:
                logging.log(1, msg="Elasticsearch готов")
                return
        except requests.exceptions.ConnectionError:
            pass

        logging.log(1, msg=f"Ожидание Elasticsearch... ({i + 1}/{max_retries})")
        time.sleep(delay)

    logging.error("Ошибка запуска Elasticsearch")
    sys.exit(1)


def wait_for_redis(max_retries=30, delay=2):
    """Ожидание готовности Redis"""
    redis_client = Redis(host='redis', port=6379, socket_connect_timeout=1)
    for i in range(max_retries):
        try:
            if redis_client.ping():
                logging.log(1, msg="Redis готов")
                return
        except:
            pass

        logging.log(1, msg=f"Ожидание Redis... ({i + 1}/{max_retries})")
        time.sleep(delay)

    logging.error(msg="Ошибка запуска Redis")
    sys.exit(1)


def wait_for_app(max_retries=30, delay=2):
    """Ожидание готовности приложения"""
    app_url = "http://app:8000/health"
    for i in range(max_retries):
        try:
            response = requests.get(app_url)
            if response.status_code == 200:
                logging.log(1, msg="App готов")
                return
        except requests.exceptions.ConnectionError:
            pass

        logging.log(1, msg=f"Ожидание App... ({i + 1}/{max_retries})")
        time.sleep(delay)

    logging.error("Ошибка запуска App")
    sys.exit(1)


if __name__ == "__main__":
    logging.log(1, msg="Запуск health check...")
    wait_for_elasticsearch()
    wait_for_redis()
    wait_for_app()
    logging.log(1, msg="Все сервисы подняты. Запускаем тесты...")
