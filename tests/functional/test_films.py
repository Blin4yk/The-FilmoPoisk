from http import HTTPStatus


class TestFilmEndpoints:
    """Тесты для эндпоинтов фильмов"""

    def test_get_film_details_success(self, api_client, film_data):
        """Тест получения деталей фильма по ID"""
        response = api_client.get(f"/films/{film_data['star_wars']}")

        assert response.status_code == HTTPStatus.OK
        data = response.json()

        assert data["id"] == film_data["star_wars"]
        assert data["title"] == "Star Wars: Episode IV - A New Hope"
        assert data["imdb_rating"] == 8.6
        # Проверяем структуру согласно новой схеме
        assert "description" in data
        assert "genres" in data
        assert "actors" in data
        assert "writers" in data
        assert "directors" in data

        # Проверяем что жанры содержат Action
        genre_names = [genre["name"] for genre in data["genres"]]
        assert "Action" in genre_names

    def test_get_film_details_not_found(self, api_client):
        """Тест получения несуществующего фильма"""
        response = api_client.get("/films/non-existent-id")

        assert response.status_code == HTTPStatus.NOT_FOUND
        data = response.json()
        assert data["detail"] == "Фильм не найден или доступ запрещен. Новые фильмы требуют роль subscriber."

    def test_get_films_list_default(self, api_client):
        """Тест получения списка фильмов с параметрами по умолчанию"""
        response = api_client.get("/films/")

        assert response.status_code == HTTPStatus.OK
        data = response.json()

        assert isinstance(data, list)
        assert len(data) > 0

        # Проверяем структуру ответа согласно FilmShort
        film = data[0]
        assert "id" in film
        assert "title" in film
        assert "imdb_rating" in film

    def test_get_films_list_with_sorting(self, api_client):
        """Тест сортировки по рейтингу"""
        response = api_client.get("/films/", params={"sort": "-imdb_rating"})

        assert response.status_code == HTTPStatus.OK
        data = response.json()

        # Проверяем что фильмы отсортированы по убыванию рейтинга
        ratings = [film["imdb_rating"] for film in data if film["imdb_rating"] is not None]
        assert ratings == sorted(ratings, reverse=True)

    def test_films_search_success(self, api_client):
        """Тест поиска фильмов"""
        response = api_client.get("/films/search/", params={"query": "door"})

        assert response.status_code == HTTPStatus.OK
        data = response.json()

        assert len(data) > 0
        for film in data:
            assert "door" in film["title"].lower()

    def test_films_search_empty_query(self, api_client):
        """Тест поиска с пустым запросом"""
        response = api_client.get("/films/search/", params={"query": ""})

        assert response.status_code == 422


    def test_films_search_no_results(self, api_client):
        """Тест поиска без результатов"""
        response = api_client.get("/films/search/", params={"query": "nonexistentmovie"})

        assert response.status_code == HTTPStatus.OK
        data = response.json()
        assert data == []


class TestFilmValidation:
    """Тесты валидации параметров"""

    def test_invalid_page_number(self, api_client):
        """Тест невалидного номера страницы"""
        response = api_client.get("/films/", params={"page": 0})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_invalid_page_size(self, api_client):
        """Тест невалидного размера страницы"""
        response = api_client.get("/films/", params={"size": 0})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY

    def test_page_size_exceeds_maximum(self, api_client):
        """Тест превышения максимального размера страницы"""
        response = api_client.get("/films/", params={"size": 101})
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY