import json
from datetime import datetime
from typing import TYPE_CHECKING

from db.redis import get_cache
from db.elastic import get_storage
from fastapi import Depends

from api.v1.scheme.film_scheme import FilmDetail, FilmShort, Person, Genre
from db.interface.interfaces import AbstractCache, AbstractDataStorage

if TYPE_CHECKING:
    from models.user import User

FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5  # 5 минут
FILMS_LIST_CACHE_EXPIRE_IN_SECONDS = 60  # 1 минута


class FilmService:
    """Сервис для работы с фильмами. Зависит от абстракций (принцип D из SOLID)"""

    def __init__(self, cache: AbstractCache, storage: AbstractDataStorage):
        """
        Args:
            cache: Абстракция кэша (например, RedisCache)
            storage: Абстракция хранилища данных (например, ElasticDataStorage)
        """
        self.cache = cache
        self.storage = storage
        self.index = "movies"  # Индекс фильмов в Elasticsearch

    async def get_by_id(self, film_id: str, user: 'User | None' = None, permission_service=None) -> FilmDetail | None:
        """
        Получить фильм по ID с кэшированием и проверкой доступа.

        Args:
            film_id: ID фильма
            user: Текущий пользователь (опционально)
            permission_service: Сервис проверки разрешений для проверки доступа

        Returns:
            FilmDetail или None если не найден или доступ запрещен
        """
        cache_key = f"film:{film_id}"
        cached_film = await self.cache.get(cache_key)
        if cached_film:
            film = FilmDetail.parse_raw(cached_film)
        else:
            film_data = await self.storage.get_by_id(index=self.index, id=film_id)
            if not film_data:
                return None

            film = self._convert_to_film_detail(film_data)

            await self.cache.set(
                cache_key,
                film.json(),
                expire=FILM_CACHE_EXPIRE_IN_SECONDS
            )

        # Проверяем доступ, если предоставлен сервис проверки разрешений
        if permission_service:
            # Пытаемся получить creation_date из данных фильма
            film_data = await self.storage.get_by_id(index=self.index, id=film_id)
            creation_date = None
            if film_data:
                # Пробуем разные возможные поля даты
                creation_date_str = film_data.get('creation_date') or film_data.get('release_date') or film_data.get(
                    'premiere')
                if creation_date_str:
                    try:
                        if isinstance(creation_date_str, str):
                            # Пробуем парсить разные форматы дат
                            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%fZ', '%Y']:
                                try:
                                    creation_date = datetime.strptime(creation_date_str.split('T')[0], fmt)
                                    break
                                except ValueError:
                                    continue
                        elif isinstance(creation_date_str, (int, float)):
                            # Unix timestamp
                            creation_date = datetime.fromtimestamp(creation_date_str)
                    except Exception:
                        pass

            can_access = await permission_service.can_access_new_film(user, creation_date)
            if not can_access:
                return None

        return film

    async def get_films(
            self,
            sort: str = "-imdb_rating",
            genre: str | None = None,
            page: int = 1,
            size: int = 50,
            user: 'User | None' = None,
            permission_service=None,
    ) -> list[FilmShort]:
        """Получение списка фильмов с сортировкой по рейтингу и фильтром жанров"""
        cache_key = f"films:list:{sort}:{genre}:{page}:{size}"

        cached_films = await self.cache.get(cache_key)
        if cached_films:
            films_data = json.loads(cached_films)
            return [FilmShort(**film_data) for film_data in films_data]

        query = {"match_all": {}}
        if genre:
            query = {
                "nested": {
                    "path": "genres",
                    "query": {
                        "bool": {
                            "must": [{"terms": {"genres": [genre]}}]
                        }
                    }
                }
            }

        # Формируем параметры сортировки
        sort_field = sort.lstrip('-')
        sort_order = "desc" if sort.startswith('-') else "asc"

        if sort_field == "imdb_rating":
            sort_param = [{"imdb_rating": {"order": sort_order, "missing": "_last"}}]
        elif sort_field == "title":
            sort_param = [{"title.raw": {"order": sort_order}}]
        else:
            sort_param = [{"imdb_rating": {"order": "desc", "missing": "_last"}}]

        # Получаем из хранилища
        films_data = await self.storage.get_list(
            index=self.index,
            query=query,
            sort=sort_param,
            page=page,
            size=size,
            _source=["id", "title", "imdb_rating"]
        )

        # Конвертируем в модели
        films = [self._convert_to_film_short(film_data) for film_data in films_data]

        # Сохраняем в кэш
        if films:
            films_json = json.dumps([film.dict() for film in films])
            await self.cache.set(
                cache_key,
                films_json,
                expire=FILMS_LIST_CACHE_EXPIRE_IN_SECONDS
            )

        return films

    async def search_films(
            self,
            query: str,
            sort: str = "-imdb_rating",
            page: int = 1,
            size: int = 50,
            user: 'User | None' = None,
            permission_service=None,
    ) -> list[FilmShort]:
        """Поиск фильмов по любому слову в названии, описании и других полях"""
        # Генерируем ключ для кэша
        cache_key = f"films:search:{query}:{sort}:{page}:{size}"

        # Пытаемся получить из кэша
        cached_films = await self.cache.get(cache_key)
        if cached_films:
            films_data = json.loads(cached_films)
            return [FilmShort(**film_data) for film_data in films_data]

        # Формируем поисковый query для Elasticsearch
        search_query = {
            "multi_match": {
                "query": query,
                "fields": [
                    "title^3",
                    "description",
                    "genres",
                    "directors_names",
                    "actors_names",
                    "writers_names"
                ],
                "fuzziness": "auto",
                "operator": "or"
            }
        }

        # Формируем параметры сортировки
        sort_field = sort.lstrip('-')
        sort_order = "desc" if sort.startswith('-') else "asc"

        if sort_field == "imdb_rating":
            sort_param = [{"imdb_rating": {"order": sort_order, "missing": "_last"}}]
        elif sort_field == "title":
            sort_param = [{"title.raw": {"order": sort_order}}]
        else:
            sort_param = [{"imdb_rating": {"order": "desc", "missing": "_last"}}]

        # Получаем из хранилища
        films_data = await self.storage.get_list(
            index=self.index,
            query=search_query,
            sort=sort_param,
            page=page,
            size=size,
            _source=["id", "title", "imdb_rating", "creation_date", "release_date", "premiere"]
        )

        # Конвертируем в модели и фильтруем по доступу
        accessible_films = []
        for film_data in films_data:
            # Check access if permission service provided
            if permission_service:
                creation_date = None
                creation_date_str = film_data.get('creation_date') or film_data.get('release_date') or film_data.get(
                    'premiere')
                if creation_date_str:
                    try:
                        if isinstance(creation_date_str, str):
                            for fmt in ['%Y-%m-%d', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%S.%fZ', '%Y']:
                                try:
                                    creation_date = datetime.strptime(creation_date_str.split('T')[0], fmt)
                                    break
                                except ValueError:
                                    continue
                        elif isinstance(creation_date_str, (int, float)):
                            creation_date = datetime.fromtimestamp(creation_date_str)
                    except Exception:
                        pass

                can_access = await permission_service.can_access_new_film(user, creation_date)
                if not can_access:
                    continue

            accessible_films.append(self._convert_to_film_short(film_data))

        # Сохраняем в кэш (note: cache key doesn't include user, so we cache accessible films for current user)
        if accessible_films:
            films_json = json.dumps([film.dict() for film in accessible_films])
            await self.cache.set(
                cache_key,
                films_json,
                expire=FILMS_LIST_CACHE_EXPIRE_IN_SECONDS
            )

        return accessible_films

    @staticmethod
    def _convert_to_film_detail(data: dict) -> FilmDetail:
        """Конвертировать словарь в FilmDetail"""
        return FilmDetail(
            id=data['id'],
            title=data['title'],
            imdb_rating=data.get('imdb_rating'),
            description=data.get('description'),
            genres=[Genre(name=genre) for genre in data.get('genres', [])],
            actors=[Person(id=person['id'], full_name=person['name'])
                    for person in data.get('actors', [])],
            writers=[Person(id=person['id'], full_name=person['name'])
                     for person in data.get('writers', [])],
            directors=[Person(id=person['id'], full_name=person['name'])
                       for person in data.get('directors', [])]
        )

    @staticmethod
    def _convert_to_film_short(data: dict) -> FilmShort:
        """Конвертировать словарь в FilmShort"""
        return FilmShort(
            id=data['id'],
            title=data['title'],
            imdb_rating=data.get('imdb_rating')
        )

    async def health_check(self) -> dict[str, bool]:
        """Проверка здоровья всех компонентов"""
        try:
            await self.cache.get("health_check")
            cache_health = True
        except Exception:
            cache_health = False

        try:
            await self.storage.get_by_id(index=self.index, id="health_check")
            storage_health = True
        except Exception:
            storage_health = False

        return {
            "cache": cache_health,
            "storage": storage_health,
            "overall": cache_health and storage_health
        }


# Зависимости для внедрения
async def get_film_service(
        cache: AbstractCache = Depends(get_cache),
        storage: AbstractDataStorage = Depends(get_storage),
) -> FilmService:
    return FilmService(cache, storage)