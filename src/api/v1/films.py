from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional

from api.v1.dependencies.auth import get_current_user_optional
from api.v1.dependencies.dependency import PaginationParams
from api.v1.scheme.film_scheme import FilmDetail, FilmShort
from db.interface.interfaces import AbstractCache
from db.postgres import get_db
from db.redis import get_cache
from models.user import User
from services.film import FilmService, get_film_service
from services.permission import PermissionService
from sqlalchemy.ext.asyncio import AsyncSession

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


def get_permission_service(
    db: AsyncSession = Depends(get_db),
    cache: AbstractCache = Depends(get_cache),
) -> PermissionService:
    """Получить экземпляр сервиса проверки разрешений."""
    return PermissionService(db, cache)


@router.get('/{film_id}', response_model=FilmDetail)
async def film_details(
    film_id: str,
    film_service: FilmService = Depends(get_film_service),
    current_user: User | None = Depends(get_current_user_optional),
    permission_service: PermissionService = Depends(get_permission_service),
) -> FilmDetail:
    """
    Get фильма по id с проверкой доступа.

    Фильмы новее 3 лет требуют роль 'subscriber'.

    Args:
        film_id: ID фильма
        film_service: Сервис фильмов
        current_user: Текущий аутентифицированный пользователь (опционально)
        permission_service: Сервис проверки разрешений

    Returns:
        Детали фильма

    Raises:
        HTTPException: 404 если фильм не найден или 403 если доступ запрещен
    """
    film = await film_service.get_by_id(film_id, user=current_user, permission_service=permission_service)
    if not film:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Фильм не найден или доступ запрещен. Новые фильмы требуют роль subscriber.',
        )

    return film


@router.get("/", response_model=list[FilmShort])
async def films_list(
    pagination: FilmListParams = Depends(),
    film_service: FilmService = Depends(get_film_service),
    current_user: User | None = Depends(get_current_user_optional),
    permission_service: PermissionService | None = Depends(get_permission_service),
) -> list[FilmShort]:
    """
    Get списка фильмов с сортировкой и фильтрацией по жанрам.

    Фильмы новее 3 лет требуют роль 'subscriber' и будут скрыты для неавторизованных пользователей.

    Examples:
    - /api/v1/films?sort=-imdb_rating
    - /api/v1/films?sort=-imdb_rating&genre=<genre-uuid>
    - /api/v1/films?page=2&size=20
    """
    films = await film_service.get_films(
        sort=pagination.sort,
        genre=pagination.genre,
        page=pagination.page,
        size=pagination.size,
        user=current_user,
        permission_service=permission_service,
    )

    if not films:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='Фильмы не найдены')

    return films


@router.get("/search/", response_model=list[FilmShort])
async def films_search(
    search_params: FilmSearchParams = Depends(),
    film_service: FilmService = Depends(get_film_service),
    current_user: User | None = Depends(get_current_user_optional),
    permission_service: PermissionService = Depends(get_permission_service),
) -> list[FilmShort]:
    """
    Поиск фильмов.

    Фильмы новее 3 лет требуют роль 'subscriber' и будут скрыты в результатах для неавторизованных пользователей.

    Examples:
    - /api/v1/films/search/?query=star wars&sort=-imdb_rating
    - /api/v1/films/search/?query=action
    """
    if not search_params.query.strip():
        raise HTTPException(status_code=400, detail="Запрос не может быть пустым")

    return await film_service.search_films(
        query=search_params.query,
        sort=search_params.sort,
        page=search_params.page,
        size=search_params.size,
        user=current_user,
        permission_service=permission_service,
    )