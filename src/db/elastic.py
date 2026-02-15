from typing import Any, Protocol

from db.interface.interfaces import AbstractDataStorage, FilmStorage, SearchStorage
from elasticsearch import AsyncElasticsearch, NotFoundError


class ElasticDataStorage(AbstractDataStorage):
    """Реализация AbstractDataStorage для Elasticsearch (принцип D из SOLID)"""

    def __init__(
        self, elastic_client: AsyncElasticsearch, default_index: str = 'movies'
    ):
        """
        Args:
            elastic_client: Клиент Elasticsearch
            default_index: Индекс по умолчанию для операций
        """
        self._client = elastic_client
        self.default_index = default_index

    async def get_by_id(
        self, index: str = None, id: str = None, **kwargs
    ) -> dict[str, any] | None:
        """
        Получить документ по ID из индекса

        Args:
            index: Имя индекса (если не указан, используется default_index)
            id: ID документа
            **kwargs: Дополнительные параметры для Elasticsearch get API

        Returns:
            Словарь с данными документа (_source) или None, если не найден
        """
        index = index or self.default_index
        if id is None:
            raise ValueError('требуется параметр id')

        try:
            result = await self._client.get(index=index, id=id, **kwargs)
            return result.get('_source')
        except NotFoundError:
            return None

    async def get_list(
        self,
        index: str = None,
        query: dict[str, any] = None,
        sort: list | str = None,
        page: int = 1,
        size: int = 50,
        **kwargs,
    ) -> list[dict[str, any]]:
        """
        Получить список документов из индекса

        Args:
            index: Имя индекса (если не указан, используется default_index)
            query: Elasticsearch query (по умолчанию match_all)
            sort: Параметры сортировки
            page: Номер страницы (начиная с 1)
            size: Размер страницы
            **kwargs: Дополнительные параметры для Elasticsearch search API

        Returns:
            Список словарей с данными документов
        """
        index = index or self.default_index

        search_body = {
            'query': query or {'match_all': {}},
            'from': (page - 1) * size,
            'size': size,
            **kwargs,
        }

        if sort:
            search_body['sort'] = sort

        try:
            response = await self._client.search(index=index, body=search_body)
            return [hit['_source'] for hit in response['hits']['hits']]
        except Exception:
            return []


class AbstractSearchClient(Protocol):
    """Абстракция для поискового клиента"""

    async def search(self, *args, **kwargs) -> dict[str, any]:
        ...

    async def get(self, *args, **kwargs) -> dict[str, any] | None:
        ...

    async def index(self, *args, **kwargs) -> dict[str, any]:
        ...


class ElasticsearchStorage(SearchStorage):
    """Реализация SearchStorage для Elasticsearch"""

    def __init__(self, elastic_client: AsyncElasticsearch):
        self._client = elastic_client

    async def connect(self) -> None:
        await self._client.ping()

    async def disconnect(self) -> None:
        await self._client.close()

    async def health_check(self) -> bool:
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def search(self, index: str, query: dict[str, any]) -> dict[str, any]:
        return await self._client.search(index=index, body=query)

    async def get(self, index: str, id: str) -> dict[str, any] | None:
        try:
            return await self._client.get(index=index, id=id)
        except NotFoundError:
            return None

    async def index(
        self, index: str, document: dict[str, any], id: str = None
    ) -> dict[str, any]:
        if id:
            return await self._client.index(index=index, document=document, id=id)
        return await self._client.index(index=index, document=document)


class ElasticsearchFilmStorage(FilmStorage):
    """Реализация FilmStorage для Elasticsearch"""

    def __init__(self, search_storage: SearchStorage, index: str = 'movies'):
        self.storage = search_storage
        self.index = index

    async def get_film_by_id(self, film_id: str) -> dict[str, any] | None:
        result = await self.storage.get(self.index, film_id)
        if result:
            return result.get('_source')
        return None

    async def get_films(
        self,
        sort: str = '-imdb_rating',
        genre: str | None = None,
        page: int = 1,
        size: int = 50,
    ) -> list[dict[str, any]]:
        search_body = {
            'query': {'match_all': {}},
            'from': (page - 1) * size,
            'size': size,
            '_source': ['id', 'title', 'imdb_rating'],
        }

        if genre:
            search_body['query'] = {
                'nested': {
                    'path': 'genres',
                    'query': {'bool': {'must': [{'terms': {'genres': [genre]}}]}},
                }
            }

        sort_field = sort.lstrip('-')
        sort_order = 'desc' if sort.startswith('-') else 'asc'

        if sort_field == 'imdb_rating':
            search_body['sort'] = [
                {'imdb_rating': {'order': sort_order, 'missing': '_last'}}
            ]
        elif sort_field == 'title':
            search_body['sort'] = [{'title.raw': {'order': sort_order}}]
        else:
            search_body['sort'] = [
                {'imdb_rating': {'order': 'desc', 'missing': '_last'}}
            ]

        try:
            response = await self.storage.search(self.index, search_body)
            return [hit['_source'] for hit in response['hits']['hits']]
        except Exception:
            return []

    async def search_films(
        self, query: str, sort: str = '-imdb_rating', page: int = 1, size: int = 50
    ) -> list[dict[str, any]]:
        search_body = {
            'query': {
                'multi_match': {
                    'query': query,
                    'fields': [
                        'title^3',
                        'description',
                        'genres',
                        'directors_names',
                        'actors_names',
                        'writers_names',
                    ],
                    'fuzziness': 'auto',
                    'operator': 'or',
                }
            },
            'from': (page - 1) * size,
            'size': size,
            '_source': ['id', 'title', 'imdb_rating'],
        }

        sort_field = sort.lstrip('-')
        sort_order = 'desc' if sort.startswith('-') else 'asc'

        if sort_field == 'imdb_rating':
            search_body['sort'] = [
                {'imdb_rating': {'order': sort_order, 'missing': '_last'}}
            ]
        elif sort_field == 'title':
            search_body['sort'] = [{'title.raw': {'order': sort_order}}]
        else:
            search_body['sort'] = [
                {'imdb_rating': {'order': 'desc', 'missing': '_last'}}
            ]

        try:
            response = await self.storage.search(self.index, search_body)
            return [hit['_source'] for hit in response['hits']['hits']]
        except Exception:
            return []

    async def health_check(self) -> bool:
        return await self.storage.health_check()


# Фабрики и вспомогательные функции
async def create_elasticsearch_storage(hosts: list[str]) -> SearchStorage:
    """Создать Elasticsearch хранилище"""
    es = AsyncElasticsearch(hosts=hosts)
    return ElasticsearchStorage(es)


# Для обратной совместимости
es: AsyncElasticsearch | None = None


async def get_elastic() -> AsyncElasticsearch:
    return es


async def get_search_storage() -> SearchStorage:
    if es is None:
        raise RuntimeError('Elasticsearch не инициализированная')
    return ElasticsearchStorage(es)


async def get_film_storage() -> FilmStorage:
    search_storage = await get_search_storage()
    return ElasticsearchFilmStorage(search_storage)


async def get_storage() -> AbstractDataStorage:
    """Фабрика для получения универсальной абстракции хранилища данных"""
    if es is None:
        raise RuntimeError('Elasticsearch не инициализированная')
    return ElasticDataStorage(es, default_index='movies')
