import logging

from elasticsearch import Elasticsearch


def load_test_data():
    """Загрузка тестовых данных в Elasticsearch"""

    # Подключаемся к Elasticsearch
    es = Elasticsearch(["http://elasticsearch:9200"])

    # Тестовые данные
    test_films = [
        {
            "id": "film-1",
            "title": "The Matrix",
            "imdb_rating": 8.7,
            "genre": ["Action", "Sci-Fi"],
            "description": "A computer hacker learns about the true nature of reality",
            "directors": ["Lana Wachowski", "Lilly Wachowski"],
            "actors": ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss"],
            "writers": ["Lana Wachowski", "Lilly Wachowski"]
        },
        {
            "id": "film-2",
            "title": "The Matrix Reloaded",
            "imdb_rating": 7.2,
            "genre": ["Action", "Sci-Fi"],
            "description": "Neo and the rebels continue their fight against the machines",
            "directors": ["Lana Wachowski", "Lilly Wachowski"],
            "actors": ["Keanu Reeves", "Laurence Fishburne", "Carrie-Anne Moss"],
            "writers": ["Lana Wachowski", "Lilly Wachowski"]
        },
        {
            "id": "film-3",
            "title": "Star Wars: A New Hope",
            "imdb_rating": 8.6,
            "genre": ["Action", "Adventure", "Fantasy"],
            "description": "Luke Skywalker joins the rebellion against the Empire",
            "directors": ["George Lucas"],
            "actors": ["Mark Hamill", "Harrison Ford", "Carrie Fisher"],
            "writers": ["George Lucas"]
        },
        {
            "id": "film-4",
            "title": "Inception",
            "imdb_rating": 8.8,
            "genre": ["Action", "Sci-Fi", "Thriller"],
            "description": "A thief who steals corporate secrets through dream-sharing",
            "directors": ["Christopher Nolan"],
            "actors": ["Leonardo DiCaprio", "Joseph Gordon-Levitt", "Ellen Page"],
            "writers": ["Christopher Nolan"]
        }
    ]

    # Создаем индекс и загружаем данные
    index_name = "movies"

    # Удаляем индекс если существует (для чистоты тестов)
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)

    # Создаем индекс с mapping
    mapping = {
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "title": {"type": "text", "analyzer": "standard"},
                "imdb_rating": {"type": "float"},
                "genre": {"type": "keyword"},
                "description": {"type": "text"},
                "directors": {"type": "text"},
                "actors": {"type": "text"},
                "writers": {"type": "text"}
            }
        }
    }

    es.indices.create(index=index_name, body=mapping)

    # Индексируем фильмы
    for film in test_films:
        es.index(index=index_name, id=film["id"], body=film)

    # Ждем обновления индекса
    es.indices.refresh(index=index_name)

    logging.log(1, f"Загружено {len(test_films)} тестовых фильмов в Elasticsearch")


if __name__ == "__main__":
    load_test_data()