from abc import ABC, abstractmethod
from typing import Protocol
from elasticsearch import AsyncElasticsearch


class AbstractSearchClient(Protocol):
    """Абстракция для поискового клиента"""

    async def search(self, *args, **kwargs):
        ...

    async def get(self, *args, **kwargs):
        ...

    async def index(self, *args, **kwargs):
        ...

class ElasticsearchClient:
    """Конкретная реализация для Elasticsearch"""

    def __init__(self, client: AsyncElasticsearch):
        self._client = client

    async def search(self, *args, **kwargs):
        return await self._client.search(*args, **kwargs)

    async def get(self, *args, **kwargs):
        return await self._client.get(*args, **kwargs)

    async def index(self, *args, **kwargs):
        return await self._client.index(*args, **kwargs)


class SearchService:
    """Сервис для работы с поиском"""

    def __init__(self, search_client: AbstractSearchClient):
        self.client = search_client

    async def search_documents(self, index: str, query: dict):
        return await self.client.search(index=index, body=query)


async def create_elastic_client(hosts: list[str]) -> AbstractSearchClient:
    es = AsyncElasticsearch(hosts=hosts)
    return ElasticsearchClient(es)

es: AsyncElasticsearch | None = None


async def get_elastic() -> AsyncElasticsearch:
    return es