import json

from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk

# Подключение к Elasticsearch
es = Elasticsearch(
    ['http://localhost:9200'],
)


def load_data_to_elasticsearch():
    try:
        # Чтение JSON-файла
        with open(r'schemes/dump.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        print(f"Найдено документов: {len(data['hits']['hits'])}")

        # Подготовка действий для Bulk API
        actions = []
        for hit in data['hits']['hits']:
            action = {'_index': 'movies', '_id': hit['_id'], '_source': hit['_source']}
            actions.append(action)

        # Выполнение массовой загрузки
        print('Начало загрузки данных в Elasticsearch...')
        success_count, errors = bulk(
            es,
            actions,
            stats_only=True,  # Возвращает только количество успешных и ошибок
            raise_on_error=False,
            max_retries=5,
            initial_backoff=2,
            max_backoff=600,
        )

        print('Загрузка завершена!')
        print(f'Успешно загружено: {success_count} документов')
        print(f'Ошибок: {errors}')

        # Проверка общего количества документов в индексе
        if es.indices.exists(index='movies'):
            count = es.count(index='movies')['count']
            print(f"Всего документов в индексе 'movies': {count}")

        return success_count, errors

    except FileNotFoundError:
        print('Ошибка: Файл не найден. Проверьте путь к файлу.')
        return 0, 0
    except json.JSONDecodeError as e:
        print(f'Ошибка при чтении JSON: {e}')
        return 0, 0
    except Exception as e:
        print(f'Неожиданная ошибка: {e}')
        return 0, 0


def create_index_with_mapping():
    """Создание индекса с правильной схемой данных (опционально)"""
    mapping = {
        'settings': {
            'refresh_interval': '1s',
            'analysis': {
                'filter': {
                    'english_stop': {'type': 'stop', 'stopwords': '_english_'},
                    'english_stemmer': {'type': 'stemmer', 'language': 'english'},
                    'english_possessive_stemmer': {
                        'type': 'stemmer',
                        'language': 'possessive_english',
                    },
                    'russian_stop': {'type': 'stop', 'stopwords': '_russian_'},
                    'russian_stemmer': {'type': 'stemmer', 'language': 'russian'},
                },
                'analyzer': {
                    'ru_en': {
                        'tokenizer': 'standard',
                        'filter': [
                            'lowercase',
                            'english_stop',
                            'english_stemmer',
                            'english_possessive_stemmer',
                            'russian_stop',
                            'russian_stemmer',
                        ],
                    }
                },
            },
        },
        'mappings': {
            'dynamic': 'strict',
            'properties': {
                'id': {'type': 'keyword'},
                'imdb_rating': {'type': 'float'},
                'genres': {'type': 'keyword'},
                'title': {
                    'type': 'text',
                    'analyzer': 'ru_en',
                    'fields': {'raw': {'type': 'keyword'}},
                },
                'description': {'type': 'text', 'analyzer': 'ru_en'},
                'directors_names': {'type': 'text', 'analyzer': 'ru_en'},
                'actors_names': {'type': 'text', 'analyzer': 'ru_en'},
                'writers_names': {'type': 'text', 'analyzer': 'ru_en'},
                'directors': {
                    'type': 'nested',
                    'dynamic': 'strict',
                    'properties': {
                        'id': {'type': 'keyword'},
                        'name': {'type': 'text', 'analyzer': 'ru_en'},
                    },
                },
                'actors': {
                    'type': 'nested',
                    'dynamic': 'strict',
                    'properties': {
                        'id': {'type': 'keyword'},
                        'name': {'type': 'text', 'analyzer': 'ru_en'},
                    },
                },
                'writers': {
                    'type': 'nested',
                    'dynamic': 'strict',
                    'properties': {
                        'id': {'type': 'keyword'},
                        'name': {'type': 'text', 'analyzer': 'ru_en'},
                    },
                },
            },
        },
    }

    if not es.indices.exists(index='movies'):
        es.indices.create(index='movies', body=mapping)
        print("Индекс 'movies' создан с настройками схемы")
    else:
        print("Индекс 'movies' уже существует")


if __name__ == '__main__':
    create_index_with_mapping()

    # Загрузка данных
    success, errors = load_data_to_elasticsearch()

    # Дополнительная проверка
    if success > 0:
        print('\nПроверка загрузки - пример первого документа:')
        try:
            result = es.search(
                index='movies', body={'query': {'match_all': {}}, 'size': 1}
            )
            if result['hits']['hits']:
                first_doc = result['hits']['hits'][0]
                print(f"ID: {first_doc['_id']}")
                print(f"Title: {first_doc['_source'].get('title', 'N/A')}")
        except Exception as e:
            print(f'Ошибка при проверке: {e}')
