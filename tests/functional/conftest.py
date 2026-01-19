import logging
import os
import time
from http import HTTPStatus
from typing import Generator

import pytest
import requests

# В зависимости от сборки, если локально, то localhost:, иначе fastapi:
API_BASE_URL = os.getenv('API_URL', 'http://localhost:8000/api/v1')


class APIClient:
    """Клиент для работы с API с автоматической подстановкой базового URL"""

    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()

    def _make_url(self, url):
        """Создает полный URL из относительного пути"""
        if not url.startswith(('http://', 'https://')):
            url = f'{self.base_url}{url}'
        return url

    def get(self, url, **kwargs):
        """GET запрос"""
        url = self._make_url(url)
        return self.session.get(url, **kwargs)

    def post(self, url, **kwargs):
        """POST запрос"""
        url = self._make_url(url)
        return self.session.post(url, **kwargs)

    def patch(self, url, **kwargs):
        """PATCH запрос"""
        url = self._make_url(url)
        return self.session.patch(url, **kwargs)

    def put(self, url, **kwargs):
        """PUT запрос"""
        url = self._make_url(url)
        return self.session.put(url, **kwargs)

    def delete(self, url, **kwargs):
        """DELETE запрос"""
        url = self._make_url(url)
        return self.session.delete(url, **kwargs)


@pytest.fixture(scope='session')
def api_client() -> Generator:
    """Фикстура для работы с API"""
    client = APIClient(API_BASE_URL)

    # Ждем пока API будет готов принимать запросы
    max_retries = 30
    for i in range(max_retries):
        try:
            response = client.get('/films/')
            if response.status_code in [200, 404]:
                logging.warning(f'API доступно после {i + 1} попытки')
                break
            else:
                logging.warning(f'Попытка {i + 1}: статус {response.status_code}')
        except requests.exceptions.RequestException as e:
            logging.warning(f'Попытка {i + 1}/{max_retries}: {e}')

        time.sleep(2)
    else:
        pytest.fail(f'API недоступно после {max_retries} попыток')

    yield client
    client.session.close()


@pytest.fixture
def film_data():
    """Тестовые данные фильмов"""
    return {
        'star_wars': '1d825f60-9fff-4dfe-b294-1a45fa1e111d',
        'star_doors': '2d825f60-9fff-4dfe-b294-1a45fa1e112d',
        'star_hit': '3d825f60-9fff-4dfe-b294-1a45fa1e113d',
    }


@pytest.fixture
def test_user(api_client):
    """Fixture to create a test user."""
    import uuid

    username = f'test_user_{uuid.uuid4().hex[:8]}'
    email = f'{username}@example.com'
    password = 'test_password123'

    data = {
        'username': username,
        'email': email,
        'password': password,
    }
    response = api_client.post('/auth/register', json=data)
    # Изменено: ожидаем 201 (Created) вместо 200 (OK)
    assert response.status_code == HTTPStatus.CREATED
    data['id'] = response.json()['id']
    return data


@pytest.fixture
def authenticated_client(api_client, test_user):
    """Fixture that returns authenticated client data."""
    return test_user
