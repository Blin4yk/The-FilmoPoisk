import pytest
import time


class TestFilmPerformance:
    """Тесты производительности"""

    @pytest.mark.performance
    def test_response_time_film_details(self, api_client, film_data):
        """Тест времени ответа для деталей фильма"""
        start_time = time.time()
        response = api_client.get(f"/films/{film_data['star_wars']}")
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Ответ менее 1 секунды

    @pytest.mark.performance
    def test_response_time_films_list(self, api_client):
        """Тест времени ответа для списка фильмов"""
        start_time = time.time()
        response = api_client.get("/films/")
        end_time = time.time()

        assert response.status_code == 200
        assert (end_time - start_time) < 2.0  # Ответ менее 2 секунд