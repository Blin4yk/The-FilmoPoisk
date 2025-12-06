from typing import Any

from redis.asyncio import Redis, ConnectionPool

from db.interface.interfaces import CacheStorage, CacheService, AbstractCache


class RedisCache(AbstractCache):
    """Реализация AbstractCache для Redis (принцип D из SOLID)"""

    def __init__(self, redis_client: Redis):
        """
        Args:
            redis_client: Клиент Redis
        """
        self._client = redis_client

    async def get(self, key: str, **kwargs) -> str | None:
        """
        Получить значение из кэша по ключу

        Args:
            key: Ключ для получения значения
            **kwargs: Дополнительные параметры для Redis get API

        Returns:
            Значение из кэша или None, если ключ не существует
        """
        return await self._client.get(key, **kwargs)

    async def set(self, key: str, value: str, expire: int = None, **kwargs) -> None:
        """
        Установить значение в кэш

        Args:
            key: Ключ для сохранения
            value: Значение для сохранения
            expire: Время жизни ключа в секундах (опционально)
            **kwargs: Дополнительные параметры для Redis set API
        """
        if expire:
            await self._client.setex(key, expire, value, **kwargs)
        else:
            await self._client.set(key, value, **kwargs)


class RedisCacheStorage(CacheStorage):
    """Реализация CacheStorage для Redis"""

    def __init__(self, redis_client: Redis):
        self._client = redis_client

    async def connect(self) -> None:
        """Подключение уже установлено при создании клиента"""
        await self._client.ping()

    async def disconnect(self) -> None:
        await self._client.close()

    async def health_check(self) -> bool:
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def get(self, key: str) -> str | None:
        return await self._client.get(key)

    async def set(self, key: str, value: str, expire: int = None) -> None:
        if expire:
            await self._client.setex(key, expire, value)
        else:
            await self._client.set(key, value)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        return await self._client.exists(key) > 0


class RedisCacheService(CacheService):
    """Реализация CacheService для Redis"""

    def __init__(self, cache_storage: CacheStorage):
        self.cache = cache_storage

    async def get_film(self, film_id: str) -> str | None:
        return await self.cache.get(f"film:{film_id}")

    async def set_film(self, film_id: str, film_data: str, expire: int = 300) -> None:
        await self.cache.set(f"film:{film_id}", film_data, expire)

    async def get_films_list(self, cache_key: str) -> str | None:
        return await self.cache.get(f"films:{cache_key}")

    async def set_films_list(self, cache_key: str, films_data: str, expire: int = 60) -> None:
        await self.cache.set(f"films:{cache_key}", films_data, expire)

    async def health_check(self) -> bool:
        return await self.cache.health_check()


# Фабрика для создания Redis клиента
async def create_redis_cache(host: str = "localhost", port: int = 6379, db: int = 0) -> CacheStorage:
    """Создать Redis кэш"""
    pool = ConnectionPool(host=host, port=port, db=db, decode_responses=True)
    redis_client = Redis(connection_pool=pool)
    return RedisCacheStorage(redis_client)


# Для обратной совместимости
redis: Redis | None = None


async def get_redis() -> Redis:
    return redis


async def get_cache_storage() -> CacheStorage:
    if redis is None:
        raise RuntimeError("Radis не инициализирован")
    return RedisCacheStorage(redis)


async def get_cache_service() -> CacheService:
    cache_storage = await get_cache_storage()
    return RedisCacheService(cache_storage)


async def get_cache() -> AbstractCache:
    """Фабрика для получения универсальной абстракции кэша"""
    if redis is None:
        raise RuntimeError("Radis не инициализирован")
    return RedisCache(redis)
