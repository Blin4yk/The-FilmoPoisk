from functools import lru_cache

from elasticsearch import AsyncElasticsearch, NotFoundError
from fastapi import Depends
from redis.asyncio import Redis

from api.v1.scheme.film_scheme import FilmDetail, FilmShort, Person, Genre
from core.logger import LOGGING
from db.elastic import get_elastic
from db.redis import get_redis

FILM_CACHE_EXPIRE_IN_SECONDS = 60 * 5  # 5 минут


class FilmService:
    def __init__(self, redis: Redis, elastic: AsyncElasticsearch):
        self.redis = redis
        self.elastic = elastic

    # get_by_id возвращает объект фильма. Он опционален, так как фильм может отсутствовать в базе
    async def get_by_id(self, film_id: str) -> FilmDetail | None:
        film = await self._film_from_cache(film_id)
        if not film:
            film = await self._get_film_from_elastic(film_id)
            if not film:
                return None
            await self._put_film_to_cache(film)
        return film

    async def get_films(
            self,
            sort: str = "-imdb_rating",
            genre: str | None = None,
            page: int = 1,
            size: int = 50
    ) -> list[FilmShort]:
        """
        Получение списка фильмов с сортировкой по рейтингу и фильтром жанров
        Args:
            sort:
            genre:
            page:
            size:

        Returns: list[FilmShort]

        """
        # Строим базовый запрос
        search_body = {
            "query": {"match_all": {}},
            "from": (page - 1) * size,
            "size": size,
            "_source": ["id", "title", "imdb_rating"]
        }

        # Фильтрация по жанру
        if genre:
            search_body["query"] = {
                "nested": {
                    "path": "genres",
                    "query": {
                        "bool": {
                            "must": [
                                {
                                    "terms": {
                                        "genres": genre
                                    }
                                }
                            ]
                        }
                    }
                }
            }

        # Сортировка
        sort_field = sort.lstrip('-')
        sort_order = "desc" if sort.startswith('-') else "asc"

        if sort_field == "imdb_rating":
            search_body["sort"] = [{"imdb_rating": {"order": sort_order, "missing": "_last"}}]
        elif sort_field == "title":
            search_body["sort"] = [{"title.raw": {"order": sort_order}}]
        else:
            # По умолчанию сортируем по рейтингу по убыванию
            search_body["sort"] = [{"imdb_rating": {"order": "desc", "missing": "_last"}}]

        try:
            # Выполняем запрос к Elasticsearch
            response = await self.elastic.search(index="movies", body=search_body)

            films = []
            for doc in response["hits"]["hits"]:
                film_data = doc["_source"]
                films.append(FilmShort(
                    id=film_data["id"],
                    title=film_data["title"],
                    imdb_rating=film_data.get("imdb_rating")
                ))

            return films

        except Exception as e:
            LOGGING.error(f"Error searching films in Elasticsearch: {e}")
            return []

    async def search_films(
            self,
            query: str,
            sort: str = "-imdb_rating",
            page: int = 1,
            size: int = 50
    ) -> list[FilmShort]:
        """
        Поиск фильмов по любому слову в названии, описании и других полях
        Args:
            query:
            page:
            size:

        Returns:

        """
        search_body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": [
                        "title^3",  # Название имеет больший вес
                        "description",
                        "genres",  # Поиск по жанрам
                        "directors_names",
                        "actors_names",
                        "writers_names"
                    ],
                    "fuzziness": "auto",  # Автоматический подбор расстояния Левенштейна
                    "operator": "or"  # Хотя бы одно слово должно совпадать
                }
            },
            "from": (page - 1) * size,
            "size": size,
            "_source": ["id", "title", "imdb_rating"],
            "highlight": {  # Подсветка найденных фрагментов (опционально)
                "fields": {
                    "title": {},
                    "description": {}
                }
            }
        }

        # Сортировка
        sort_field = sort.lstrip('-')
        sort_order = "desc" if sort.startswith('-') else "asc"

        if sort_field == "imdb_rating":
            search_body["sort"] = [{"imdb_rating": {"order": sort_order, "missing": "_last"}}]
        elif sort_field == "title":
            search_body["sort"] = [{"title.raw": {"order": sort_order}}]
        else:
            # По умолчанию сортируем по рейтингу по убыванию
            search_body["sort"] = [{"imdb_rating": {"order": "desc", "missing": "_last"}}]

        try:
            response = await self.elastic.search(index="movies", body=search_body)

            films = []
            for doc in response["hits"]["hits"]:
                film_data = doc["_source"]
                films.append(FilmShort(
                    id=film_data["id"],
                    title=film_data["title"],
                    imdb_rating=film_data.get("imdb_rating")
                ))

            return films

        except Exception as e:
            LOGGING.error(f"Error searching films in Elasticsearch: {e}")
            return []

    async def _get_film_from_elastic(self, film_id: str) -> FilmDetail | None:
        try:
            doc = await self.elastic.get(index='movies', id=film_id)
        except NotFoundError:
            return None
        data = doc['_source']
        return FilmDetail(
            id=data['id'],
            title=data['title'],
            imdb_rating=data.get('imdb_rating'),
            description=data.get('description'),
            genres=[Genre(name=genre) for genre in data.get('genres', [])],
            actors=[Person(id=person['id'], full_name=person['name']) for person in data.get('actors', [])],
            writers=[Person(id=person['id'], full_name=person['name']) for person in data.get('writers', [])],
            directors=[Person(id=person['id'], full_name=person['name']) for person in data.get('directors', [])]
        )

    async def _film_from_cache(self, film_id: str) -> FilmDetail | None:
        data = await self.redis.get(film_id)
        if not data:
            return None
        film = FilmDetail.parse_raw(data)
        return film

    # async def _put_film_to_cache(self, film: FilmDetail):
    #     await self.redis.set(film.id, film.json(), FILM_CACHE_EXPIRE_IN_SECONDS)
    #
    #     # pydantic предоставляет удобное API для создания объекта моделей из json
    #     film = Film.parse_raw(data)
    #     return film

    async def _films_list_from_cache(self, cache_key: str) -> list[FilmDetail] | None:
        data = await self.redis.get(cache_key)
        if not data:
            return None

        # Десериализуем список фильмов
        import json
        films_data = json.loads(data)
        return [FilmDetail(**film_data) for film_data in films_data]

    async def _put_film_to_cache(self, film: FilmDetail):
        # Сохраняем данные о фильме, используя команду set
        # Выставляем время жизни кеша — 5 минут
        # https://redis.io/commands/set/
        # pydantic позволяет сериализовать модель в json
        await self.redis.set(film.id, film.json(), FILM_CACHE_EXPIRE_IN_SECONDS)

    async def _put_films_list_to_cache(self, cache_key: str, films: list[FilmDetail]):
        try:
            import json
            films_data = [film.dict() for film in films]
            await self.redis.set(
                cache_key,
                json.dumps(films_data),
                FILM_CACHE_EXPIRE_IN_SECONDS
            )
        except Exception as e:
            pass



@lru_cache()
def get_film_service(
        redis: Redis = Depends(get_redis),
        elastic: AsyncElasticsearch = Depends(get_elastic),
) -> FilmService:
    return FilmService(redis, elastic)
