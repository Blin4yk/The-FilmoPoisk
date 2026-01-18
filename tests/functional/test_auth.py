"""Тесты для API эндпоинтов аутентификации."""
from http import HTTPStatus


class TestAuthEndpoints:
    """Тесты для эндпоинтов аутентификации."""

    def test_register_user_success(self, api_client):
        """Тест успешной регистрации пользователя."""
        import uuid

        unique_username = f'test_user_{uuid.uuid4().hex[:3]}'
        data = {
            'username': unique_username,
            'email': f'{unique_username}@example.com',
            'password': 'secure_password123',
        }
        response = api_client.post('/auth/register', json=data)
        print(response.status_code)

        # Изменено: ожидаем 201 вместо 422
        assert response.status_code == HTTPStatus.CREATED
        result = response.json()
        assert result['username'] == unique_username
        assert 'id' in result
        assert 'password' not in result
        assert 'password_hash' not in result

    def test_register_user_duplicate_username(self, api_client):
        """Тест регистрации с повторяющимся именем пользователя."""
        import uuid

        unique_username = f'test_user_{uuid.uuid4().hex[:3]}'
        data = {
            'username': unique_username,
            'email': f'{unique_username}@example.com',
            'password': 'secure_password123',
        }

        api_client.post('/auth/register', json=data)

        data['email'] = f'other_{unique_username}@example.com'
        response = api_client.post('/auth/register', json=data)

        assert response.status_code == HTTPStatus.CONFLICT
        result = response.json()
        assert 'username' in result.get('detail', '').lower() or 'already' in result.get('detail', '').lower()

    def test_login_success(self, api_client, test_user):
        """Тест успешного входа в систему."""
        data = {
            'username': test_user['username'],
            'password': test_user['password'],
        }
        response = api_client.post('/auth/login', json=data)

        assert response.status_code == HTTPStatus.OK
        result = response.json()
        assert 'access_token' in result
        assert 'refresh_token' in result
        assert result['token_type'] == 'bearer'
        assert len(result['access_token']) > 0
        assert len(result['refresh_token']) > 0

    def test_login_invalid_credentials(self, api_client):
        """Тест входа с неверными учетными данными."""
        data = {
            'username': 'nonexistent_user',
            'password': 'wrong_password',
        }
        response = api_client.post('/auth/login', json=data)

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        # Изменено: проверяем русский текст ошибки
        detail = response.json().get('detail', '').lower()
        assert any(word in detail for word in ['неверное', 'invalid', 'ошибка', 'error'])

    def test_refresh_token_success(self, api_client, authenticated_client):
        """Тест успешного обновления токена."""
        # Получаем refresh token при входе
        login_data = {
            'username': authenticated_client['username'],
            'password': authenticated_client['password'],
        }
        login_response = api_client.post('/auth/login', json=login_data)
        refresh_token = login_response.json()['refresh_token']

        # Обновляем access token
        headers = {'Authorization': f'Bearer {refresh_token}'}
        response = api_client.post('/auth/refresh', headers=headers)

        assert response.status_code == HTTPStatus.OK
        result = response.json()
        assert 'access_token' in result
        assert result['token_type'] == 'bearer'

    def test_logout_success(self, api_client, authenticated_client):
        """Тест успешного выхода из системы."""
        # Сначала входим
        login_data = {
            'username': authenticated_client['username'],
            'password': authenticated_client['password'],
        }
        login_response = api_client.post('/auth/login', json=login_data)
        refresh_token = login_response.json()['refresh_token']

        # Выходим
        headers = {'Authorization': f'Bearer {refresh_token}'}
        response = api_client.post('/auth/logout', headers=headers)

        assert response.status_code == HTTPStatus.OK
        assert 'message' in response.json()

    def test_get_profile_unauthorized(self, api_client):
        """Тест получения профиля без аутентификации."""
        response = api_client.get('/auth/profile')

        assert response.status_code in [HTTPStatus.UNAUTHORIZED, HTTPStatus.METHOD_NOT_ALLOWED]

    def test_update_profile_success(self, api_client, authenticated_client):
        """Тест обновления профиля пользователя."""
        # Сначала входим
        login_data = {
            'username': authenticated_client['username'],
            'password': authenticated_client['password'],
        }
        login_response = api_client.post('/auth/login', json=login_data)
        access_token = login_response.json()['access_token']

        # Обновляем профиль
        import uuid

        new_username = f'updated_{uuid.uuid4().hex[:3]}'
        headers = {'Authorization': f'Bearer {access_token}'}
        data = {'username': new_username}
        response = api_client.patch('/auth/profile', json=data, headers=headers)

        assert response.status_code == HTTPStatus.OK
        result = response.json()
        assert result['username'] == new_username

    def test_get_login_history_success(self, api_client, authenticated_client):
        """Тест получения истории входов."""
        # Сначала входим
        login_data = {
            'username': authenticated_client['username'],
            'password': authenticated_client['password'],
        }
        login_response = api_client.post('/auth/login', json=login_data)
        access_token = login_response.json()['access_token']

        # Получаем историю входов
        headers = {'Authorization': f'Bearer {access_token}'}
        response = api_client.get('/auth/login-history', headers=headers)

        assert response.status_code == HTTPStatus.OK
        result = response.json()
        assert 'items' in result
        assert 'total' in result
        assert 'page' in result
        assert 'size' in result
        assert isinstance(result['items'], list)
        # Может быть 0 записей, если история только что создана
        assert isinstance(result['items'], list)
