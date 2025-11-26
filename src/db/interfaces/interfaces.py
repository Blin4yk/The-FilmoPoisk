from abc import ABC, abstractmethod
from typing import Any


class DataStorage(ABC):
    """Общая абстракция для хранилищ данных"""

    @abstractmethod
    async def connect(self) -> None:
        """Подключение к хранилищу"""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Отключение от хранилища"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Проверка здоровья подключения"""
        pass


class SearchStorage(DataStorage):
    """Абстракция для поисковых хранилищ"""

    @abstractmethod
    async def search(self, index: str, query: dict[str, Any]) -> dict[str, Any]:
        """Поиск документов"""
        pass

    @abstractmethod
    async def get(self, index: str, id: str) -> dict[str, Any] | None:
        """Получение документа по ID"""
        pass

    @abstractmethod
    async def index(self, index: str, document: dict[str, Any], id: str = None) -> dict[str, Any]:
        """Индексация документа"""
        pass


class CacheStorage(DataStorage):
    """Абстракция для кэш-хранилищ"""

    @abstractmethod
    async def get(self, key: str) -> str | None:
        """Получение значения по ключу"""
        pass

    @abstractmethod
    async def set(self, key: str, value: str, expire: int = None) -> None:
        """Установка значения"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Удаление значения"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Проверка существования ключа"""
        pass