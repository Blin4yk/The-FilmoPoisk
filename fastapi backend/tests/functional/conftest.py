import pytest
import requests
import time
from typing import Generator

API_BASE_URL = "http://app:8000/api/v1"


@pytest.fixture(scope="session")
def api_client() -> Generator:
    """Фикстура для работы с API"""
    session = requests.Session()
    session.base_url = API_BASE_URL

    # Ждем пока API будет готов принимать запросы
    max_retries = 3
    for i in range(max_retries):
        try:
            response = session.get(f"{API_BASE_URL}/films/")
            if response.status_code in [200, 404]:  # 404 тоже ок - значит эндпоинт работает
                break
        except requests.exceptions.ConnectionError:
            pass

        time.sleep(2)
    else:
        pytest.fail("API недоступно")

    yield session
    session.close()


@pytest.fixture
def film_data():
    """Тестовые данные фильмов"""
    return {
        "matrix": "film-1",
        "matrix_reloaded": "film-2",
        "star_wars": "film-3",
        "inception": "film-4"
    }