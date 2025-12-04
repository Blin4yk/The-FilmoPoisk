from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query

from api.v1.dependencies.dependency import FilmListParams, FilmSearchParams
from api.v1.scheme.film_scheme import FilmDetail, FilmShort
from services.film import FilmService, get_film_service

router = APIRouter()

# Внедряем FilmService с помощью Depends(get_film_service)
@router.get('/{film_id}', response_model=FilmDetail)
async def film_details(
        film_id: str,
        film_service: FilmService = Depends(get_film_service)
) -> FilmDetail:
    """
    Get фильма по id
    """
    film = await film_service.get_by_id(film_id)
    if not film:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='film not found')
    return film


@router.get("/", response_model=list[FilmShort])
async def films_list(
        params: FilmListParams = Depends(),  # Используем класс-зависимость
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
        sort=params.sort,
        genre=params.genre,
        page=params.page,
        size=params.size
    )

    if not films:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='films not found')

    return films


@router.get("/search/", response_model=list[FilmShort])
async def films_search(
        params: FilmSearchParams = Depends(),  # Используем класс-зависимость
        film_service: FilmService = Depends(get_film_service)
) -> list[FilmShort]:
    """
    Поиск фильмов

    Examples:
    - /api/v1/films/search/?query=star wars&sort=-imdb_rating
    - /api/v1/films/search/?query=action
    """
    if not params.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    films = await film_service.search_films(
        query=params.query,
        sort=params.sort,
        page=params.page,
        size=params.size
    )

    if not films:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='films not found')

    return films