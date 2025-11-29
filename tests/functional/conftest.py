import logging

import pytest
import requests
import time
import os
from typing import Generator



# В зависимости от сборки, если локально, то localhost:, иначе fastapi:
API_BASE_URL = os.getenv('API_URL', 'http://localhost:8000/api/v1')


class APIClient:
    """Клиент для работы с API с автоматической подстановкой базового URL"""

    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()

    def get(self, url, **kwargs):
        # Добавляем базовый URL к относительному пути
        if not url.startswith(('http://', 'https://')):
            url = f"{self.base_url}{url}"
        return self.session.get(url, **kwargs)


@pytest.fixture(scope="session")
def api_client() -> Generator:
    """Фикстура для работы с API"""
    client = APIClient(API_BASE_URL)

    # Ждем пока API будет готов принимать запросы
    max_retries = 30
    for i in range(max_retries):
        try:
            response = client.get("/films/")
            if response.status_code in [200, 404]:
                logging.warning(f"API доступно после {i + 1} попытки")
                break
            else:
                logging.warning(f"Попытка {i + 1}: статус {response.status_code}")
        except requests.exceptions.RequestException as e:
            logging.warning(f"Попытка {i + 1}/{max_retries}: {e}")

        time.sleep(2)
    else:
        pytest.fail(f"API недоступно после {max_retries} попыток")

    yield client
    client.session.close()


@pytest.fixture
def film_data():
    """Тестовые данные фильмов"""
    return {
        "star_wars": "1d825f60-9fff-4dfe-b294-1a45fa1e111d",
        "star_doors": "2d825f60-9fff-4dfe-b294-1a45fa1e112d",
        "star_hit": "3d825f60-9fff-4dfe-b294-1a45fa1e113d",
    }