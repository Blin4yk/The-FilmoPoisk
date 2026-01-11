from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional

from api.v1.dependencies.dependency import PaginationParams
from api.v1.scheme.film_scheme import FilmDetail, FilmShort
from services.film import FilmService, get_film_service

router = APIRouter(prefix='/api/v1/films', tags=['films'])

class FilmListParams(PaginationParams):
    """Параметры для списка фильмов с фильтром по жанру"""
    def __init__(
        self,
        sort: str = Query("-imdb_rating", description="Sort by field (- for DESC)"),
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(50, ge=1, le=100, description="Page size"),
        genre: Optional[str] = Query(None, description="Filter by genre ID")
    ):
        super().__init__(sort, page, size)
        self.genre = genre


class FilmSearchParams(PaginationParams):
    """Параметры для поиска фильмов"""
    def __init__(
        self,
        query: str = Query(..., min_length=3, description="Search query"),
        sort: str = Query("-imdb_rating", description="Sort by field (- for DESC)"),
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(50, ge=1, le=100, description="Page size")
    ):
        super().__init__(sort, page, size)
        self.query = query


@router.get('/{film_id}', response_model=FilmDetail)
async def film_details(
    film_id: str,
    film_service: FilmService = Depends(get_film_service)
) -> FilmDetail:
    """
    Get фильма по id
    Args:
        film_id:
        film_service:

    Returns:

    """
    film = await film_service.get_by_id(film_id)
    if not film:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='film not found')

    return film


@router.get("/", response_model=list[FilmShort])
async def films_list(
    pagination: FilmListParams = Depends(),
    film_service: FilmService = Depends(get_film_service)
) -> list[FilmShort]:
    """
    Get списка фильмов с сортировкой и фильтрацией по жанрам

    Examples:
    - /api/v1/films?sort=-imdb_rating
    - /api/v1/films?sort=-imdb_rating&genre=<genre-uuid>
    - /api/v1/films?page=2&size=20
    """
    films = await film_service.get_films(
        sort=pagination.sort,
        genre=pagination.genre,
        page=pagination.page,
        size=pagination.size
    )

    if not films:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='film not found')

    return films


@router.get("/search/", response_model=list[FilmShort])
async def films_search(
    search_params: FilmSearchParams = Depends(),
    film_service: FilmService = Depends(get_film_service)
) -> list[FilmShort]:
    """
    Поиск фильмов

    Examples:
    - /api/v1/films/search/?query=star wars&sort=-imdb_rating
    - /api/v1/films/search/?query=action
    """
    if not search_params.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    return await film_service.search_films(
        query=search_params.query,
        sort=search_params.sort,
        page=search_params.page,
        size=search_params.size
    )