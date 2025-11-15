from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.src.api.v1.scheme.film_scheme import FilmDetail, FilmShort
from backend.src.services.film import FilmService, get_film_service

router = APIRouter()

# Внедряем FilmService с помощью Depends(get_film_service)
@router.get('/{film_id}', response_model=FilmDetail)
async def film_details(film_id: str, film_service: FilmService = Depends(get_film_service)) -> FilmDetail:
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
        sort: str = Query("-imdb_rating", description="Sort by field (- for DESC)"),
        genre: str | None = Query(None, description="Filter by genre ID"),
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(50, ge=1, le=100, description="Page size"),
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
        sort=sort,
        genre=genre,
        page=page,
        size=size
    )

    if not films:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='film not found')

    return films


@router.get("/search/", response_model=list[FilmShort])
async def films_search(
        query: str = Query(..., min_length=1, description="Search query"),
        sort: str = Query("-imdb_rating", description="Sort by field (- for DESC)"),
        page: int = Query(1, ge=1, description="Page number"),
        size: int = Query(50, ge=1, le=100, description="Page size"),
        film_service: FilmService = Depends(get_film_service)
) -> list[FilmShort]:
    """
    Поиск фильмов

    Examples:
    - /api/v1/films/search/?query=star wars&sort=-imdb_rating
    - /api/v1/films/search/?query=action
    """
    if not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    return await film_service.search_films(
        query=query,
        sort=sort,
        page=page,
        size=size
    )