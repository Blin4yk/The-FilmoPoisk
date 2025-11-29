import logging
import os
from elasticsearch import Elasticsearch




def load_test_data():
    """Загрузка тестовых данных в Elasticsearch"""

    # Используем переменную окружения или правильное имя сервиса
    es_host = os.getenv('ELASTICSEARCH_URL', 'http://elasticsearch-with-dump:9200')
    es = Elasticsearch([es_host])

    # Обновленные тестовые данные согласно вашим схемам
    test_films = [
        {
            "id": "1d825f60-9fff-4dfe-b294-1a45fa1e111d",
            "imdb_rating": 8.6,
            "genres": ["Adventure", "Action", "Sci-Fi", "Fantasy"],
            "title": "Star Wars: Episode IV - A New Hope",
            "description": "The Imperial Forces, under orders from cruel Darth Vader...",
            "directors_names": ["George Lucas"],
            "actors_names": ["Mark Hamill", "Harrison Ford", "Carrie Fisher", "Peter Cushing"],
            "writers_names": ["George Lucas"],
            "directors": [
                {"id": "a5a8f573-3cee-4ccc-8a2b-91cb9f55250a", "name": "George Lucas"}
            ],
            "actors": [
                {"id": "26e83050-29ef-4163-a99d-b546cac208f8", "name": "Mark Hamill"},
                {"id": "5b4bf1bc-3397-4e83-9b17-8b10c6544ed1", "name": "Harrison Ford"},
                {"id": "b5d2b63a-ed1f-4e46-8320-cf52a32be358", "name": "Carrie Fisher"},
                {"id": "e039eedf-4daf-452a-bf92-a0085c68e156", "name": "Peter Cushing"}
            ],
            "writers": [
                {"id": "a5a8f573-3cee-4ccc-8a2b-91cb9f55250a", "name": "George Lucas"}
            ]
        },
        {
            "id": "2d825f60-9fff-4dfe-b294-1a45fa1e112d",
            "imdb_rating": 8.7,
            "genres": ["Adventure", "Action", "Sci-Fi", "Fantasy"],
            "title": "Star Doors: Episode IV - A New Hope",
            "description": "The Imperial Forces, under orders from cruel Darth Vader...",
            "directors_names": ["George Lucas"],
            "actors_names": ["Mark Hamill", "Harrison Ford", "Carrie Fisher", "Peter Cushing"],
            "writers_names": ["George Lucas"],
            "directors": [
                {"id": "a5a8f573-3cee-4ccc-8a2b-91cb9f55250a", "name": "George Lucas"}
            ],
            "actors": [
                {"id": "26e83050-29ef-4163-a99d-b546cac208f8", "name": "Mark Hamill"},
                {"id": "5b4bf1bc-3397-4e83-9b17-8b10c6544ed1", "name": "Harrison Ford"},
                {"id": "b5d2b63a-ed1f-4e46-8320-cf52a32be358", "name": "Carrie Fisher"},
                {"id": "e039eedf-4daf-452a-bf92-a0085c68e156", "name": "Peter Cushing"}
            ],
            "writers": [
                {"id": "a5a8f573-3cee-4ccc-8a2b-91cb9f55250a", "name": "George Lucas"}
            ]
        },
        {
            "id": "3d825f60-9fff-4dfe-b294-1a45fa1e113d",
            "imdb_rating": 8.8,
            "genres": ["Adventure", "Action", "Sci-Fi", "Fantasy"],
            "title": "Star Hit: Episode IV - A New Hope",
            "description": "The Imperial Forces, under orders from cruel Darth Vader...",
            "directors_names": ["George Lucas"],
            "actors_names": ["Mark Hamill", "Harrison Ford", "Carrie Fisher", "Peter Cushing"],
            "writers_names": ["George Lucas"],
            "directors": [
                {"id": "a5a8f573-3cee-4ccc-8a2b-91cb9f55250a", "name": "George Lucas"}
            ],
            "actors": [
                {"id": "26e83050-29ef-4163-a99d-b546cac208f8", "name": "Mark Hamill"},
                {"id": "5b4bf1bc-3397-4e83-9b17-8b10c6544ed1", "name": "Harrison Ford"},
                {"id": "b5d2b63a-ed1f-4e46-8320-cf52a32be358", "name": "Carrie Fisher"},
                {"id": "e039eedf-4daf-452a-bf92-a0085c68e156", "name": "Peter Cushing"}
            ],
            "writers": [
                {"id": "a5a8f573-3cee-4ccc-8a2b-91cb9f55250a", "name": "George Lucas"}
            ]
        }
    ]

    # Создаем индекс и загружаем данные
    index_name = "movies"

    # Удаляем индекс если существует (для чистоты тестов)
    try:
        if es.indices.exists(index=index_name):
            es.indices.delete(index=index_name)
            logging.warning(f"Индекс {index_name} удален")
    except Exception as e:
        logging.error(f"Ошибка при удалении индекса: {e}")

    # Создаем индекс с mapping соответствующий вашим схемам
    mapping = {
        "settings": {
            "refresh_interval": "1s",
            "analysis": {
                "filter": {
                    "english_stop": {
                        "type": "stop",
                        "stopwords": "_english_"
                    },
                    "english_stemmer": {
                        "type": "stemmer",
                        "language": "english"
                    },
                    "english_possessive_stemmer": {
                        "type": "stemmer",
                        "language": "possessive_english"
                    },
                    "russian_stop": {
                        "type": "stop",
                        "stopwords": "_russian_"
                    },
                    "russian_stemmer": {
                        "type": "stemmer",
                        "language": "russian"
                    }
                },
                "analyzer": {
                    "ru_en": {
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "english_stop",
                            "english_stemmer",
                            "english_possessive_stemmer",
                            "russian_stop",
                            "russian_stemmer"
                        ]
                    }
                }
            }
        },
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "id": {
                    "type": "keyword"
                },
                "imdb_rating": {
                    "type": "float"
                },
                "genres": {
                    "type": "keyword"
                },
                "title": {
                    "type": "text",
                    "analyzer": "ru_en",
                    "fields": {
                        "raw": {
                            "type": "keyword"
                        }
                    }
                },
                "description": {
                    "type": "text",
                    "analyzer": "ru_en"
                },
                "directors_names": {
                    "type": "text",
                    "analyzer": "ru_en"
                },
                "actors_names": {
                    "type": "text",
                    "analyzer": "ru_en"
                },
                "writers_names": {
                    "type": "text",
                    "analyzer": "ru_en"
                },
                "directors": {
                    "type": "nested",
                    "dynamic": "strict",
                    "properties": {
                        "id": {
                            "type": "keyword"
                        },
                        "name": {
                            "type": "text",
                            "analyzer": "ru_en"
                        }
                    }
                },
                "actors": {
                    "type": "nested",
                    "dynamic": "strict",
                    "properties": {
                        "id": {
                            "type": "keyword"
                        },
                        "name": {
                            "type": "text",
                            "analyzer": "ru_en"
                        }
                    }
                },
                "writers": {
                    "type": "nested",
                    "dynamic": "strict",
                    "properties": {
                        "id": {
                            "type": "keyword"
                        },
                        "name": {
                            "type": "text",
                            "analyzer": "ru_en"
                        }
                    }
                }
            }
        }
    }

    try:
        es.indices.create(index=index_name, body=mapping)
        logging.info(f"Индекс {index_name} создан")
    except Exception as e:
        logging.error(f"Ошибка при создании индекса: {e}")

    # Индексируем фильмы
    for film in test_films:
        try:
            es.index(index=index_name, id=film["id"], body=film)
            logging.info(f"Фильм {film['title']} загружен")
        except Exception as e:
            logging.error(f"Ошибка при загрузке фильма {film['title']}: {e}")

    # Ждем обновления индекса
    es.indices.refresh(index=index_name)

    logging.info(f"Загружено {len(test_films)} тестовых фильмов в Elasticsearch")


if __name__ == "__main__":
    load_test_data()