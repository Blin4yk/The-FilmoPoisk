import abc
from abc import ABC, abstractmethod


class AbstractDataStorage(ABC):
    """Универсальная абстракция для хранилищ данных (принцип D из SOLID)"""

    @abc.abstractmethod
    async def get_by_id(self, *args, **kwargs):
        """Получить запись по ID"""
        ...

    @abc.abstractmethod
    async def get_list(self, *args, **kwargs):
        """Получить список записей"""
        ...


class AbstractCache(ABC):
    """Универсальная абстракция для кэша (принцип D из SOLID)"""

    @abc.abstractmethod
    async def get(self, *args, **kwargs):
        """Получить значение из кэша"""
        ...

    @abc.abstractmethod
    async def set(self, *args, **kwargs):
        """Установить значение в кэш"""
        ...


class DataStorage(ABC):
    """Общая абстракция для хранилищ данных"""

    @abstractmethod
    async def connect(self) -> None:
        """Подключение к хранилищу"""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Отключение от хранилища"""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Проверка здоровья подключения"""
        ...


class SearchStorage(DataStorage):
    """Абстракция для поисковых хранилищ"""

    @abstractmethod
    async def search(self, index: str, query: dict[str, any]) -> dict[str, any]:
        """Поиск документов"""
        ...

    @abstractmethod
    async def get(self, index: str, id: str) -> dict[str, any] | None:
        """Получение документа по ID"""
        ...

    @abstractmethod
    async def index(self, index: str, document: dict[str, any], id: str = None) -> dict[str, any]:
        """Индексация документа"""
        ...


class CacheStorage(DataStorage):
    """Абстракция для кэш-хранилищ"""

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Получение значения по ключу"""
        ...

    @abstractmethod
    async def set(self, key: str, value: str, expire: int = None) -> None:
        """Установка значения"""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Удаление значения"""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Проверка существования ключа"""
        ...


class FilmStorage(ABC):
    """Абстракция для работы с фильмами (репозиторий)"""

    @abstractmethod
    async def get_film_by_id(self, film_id: str) -> dict[str, any] | None:
        """Получить фильм по ID"""
        ...

    @abstractmethod
    async def get_films(
            self,
            sort: str = "-imdb_rating",
            genre: str | None = None,
            page: int = 1,
            size: int = 50
    ) -> list[dict[str, any]]:
        """Получить список фильмов с фильтрацией"""
        ...

    @abstractmethod
    async def search_films(
            self,
            query: str,
            sort: str = "-imdb_rating",
            page: int = 1,
            size: int = 50
    ) -> list[dict[str, any]]:
        """Поиск фильмов"""
        ...


class CacheService(ABC):
    """Абстракция для сервиса кэширования"""

    @abstractmethod
    async def get_film(self, film_id: str) -> str | None:
        """Получить фильм из кэша"""
        ...

    @abstractmethod
    async def set_film(self, film_id: str, film_data: str, expire: int = 300) -> None:
        """Сохранить фильм в кэш"""
        ...

    @abstractmethod
    async def get_films_list(self, cache_key: str) -> str | None:
        """Получить список фильмов из кэша"""
        ...

    @abstractmethod
    async def set_films_list(self, cache_key: str, films_data: str, expire: int = 60) -> None:
        """Сохранить список фильмов в кэш"""
        ...
