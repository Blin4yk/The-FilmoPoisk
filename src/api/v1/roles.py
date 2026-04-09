"""API эндпоинты для управления ролями."""
import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.dependencies.auth import check_role_permission, get_current_user
from api.v1.dependencies.dependency import PageParams
from api.v1.scheme.role_scheme import (
    AssignRoleResponse,
    CheckPermissionRequest,
    CheckPermissionResponse,
    RoleCreate,
    RoleListResponse,
    RoleResponse,
    RoleUpdate,
)
from db.interface.interfaces import AbstractCache
from db.postgres import get_db
from db.redis import get_cache
from db.repositories.role_repository import RoleRepository
from db.repositories.user_repository import UserRepository
from models.user import User
from services.role import RoleService

router = APIRouter(prefix='/api/v1/roles', tags=['roles'])


class RoleListParams(PageParams):
    """Параметры пагинации для списка ролей."""


def get_role_service(
        db: AsyncSession = Depends(get_db),
        cache: AbstractCache = Depends(get_cache),
) -> RoleService:
    """
    Получить экземпляр сервиса ролей.

    Args:
        db: Сессия базы данных
        cache: Хранилище кэша

    Returns:
        Экземпляр RoleService
    """
    return RoleService(db, cache)


@router.post('/', response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
        role_data: RoleCreate,
        current_user: User = Depends(check_role_permission('admin')),
        role_service: RoleService = Depends(get_role_service),
) -> RoleResponse:
    """
    Создать новую роль (только для admin).

    Args:
        role_data: Данные для создания роли
        current_user: Текущий аутентифицированный пользователь (admin)
        role_service: Сервис ролей

    Returns:
        Созданная роль

    Raises:
        HTTPException: Если роль уже существует или валидация не прошла
    """
    try:
        role = await role_service.create_role(role_data)
        return RoleResponse.model_validate(role)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.get('/', response_model=RoleListResponse)
async def get_roles(
        pagination: RoleListParams = Depends(),
        current_user: User = Depends(check_role_permission('admin')),
        role_service: RoleService = Depends(get_role_service),
) -> RoleListResponse:
    """
    Получить все роли с пагинацией (только для admin).

    Args:
        pagination: Параметры пагинации
        current_user: Текущий аутентифицированный пользователь (admin)
        role_service: Сервис ролей

    Returns:
        Список ролей с пагинацией
    """
    items, total = await role_service.get_all_roles(
        page=pagination.page, size=pagination.size
    )

    pages = math.ceil(total / pagination.size) if total > 0 else 0

    return RoleListResponse(
        items=[RoleResponse.model_validate(role) for role in items],
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=pages,
    )


@router.get('/{role_id}', response_model=RoleResponse)
async def get_role(
        role_id: UUID,
        current_user: User = Depends(check_role_permission('admin')),
        role_service: RoleService = Depends(get_role_service),
) -> RoleResponse:
    """
    Получить роль по ID (только для admin).

    Args:
        role_id: UUID роли
        current_user: Текущий аутентифицированный пользователь (admin)
        role_service: Сервис ролей

    Returns:
        Объект роли

    Raises:
        HTTPException: Если роль не найдена
    """
    role = await role_service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Роль не найдена',
        )
    return RoleResponse.model_validate(role)


@router.patch('/{role_id}', response_model=RoleResponse)
async def update_role(
        role_id: UUID,
        role_data: RoleUpdate,
        current_user: User = Depends(check_role_permission('admin')),
        role_service: RoleService = Depends(get_role_service),
) -> RoleResponse:
    """
    Обновить роль (только для admin).

    Args:
        role_id: UUID роли
        role_data: Данные для обновления роли
        current_user: Текущий аутентифицированный пользователь (admin)
        role_service: Сервис ролей

    Returns:
        Обновленная роль

    Raises:
        HTTPException: Если роль не найдена или валидация не прошла
    """
    if not role_data.name and role_data.description is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Необходимо указать хотя бы одно поле (name или description)',
        )

    try:
        role = await role_service.update_role(role_id, role_data)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Роль не найдена',
            )
        return RoleResponse.model_validate(role)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.delete('/{role_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
        role_id: UUID,
        current_user: User = Depends(check_role_permission('admin')),
        role_service: RoleService = Depends(get_role_service),
) -> None:
    """
    Удалить роль (только для admin).

    Args:
        role_id: UUID роли
        current_user: Текущий аутентифицированный пользователь (admin)
        role_service: Сервис ролей

    Raises:
        HTTPException: Если роль не найдена или назначена пользователям
    """
    try:
        deleted = await role_service.delete_role(role_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Роль не найдена',
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post('/{role_id}/assign/{user_id}', response_model=AssignRoleResponse)
async def assign_role(
        role_id: UUID,
        user_id: UUID,
        current_user: User = Depends(check_role_permission('admin')),
        role_service: RoleService = Depends(get_role_service),
) -> AssignRoleResponse:
    """
    Назначить роль пользователю (только для admin).

    Args:
        role_id: UUID роли
        user_id: UUID пользователя
        current_user: Текущий аутентифицированный пользователь (admin)
        role_service: Сервис ролей

    Returns:
        Подтверждение назначения

    Raises:
        HTTPException: Если пользователь/роль не найдены или роль уже назначена
    """
    try:
        assigned = await role_service.assign_role_to_user(user_id, role_id)
        if not assigned:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail='Роль уже назначена этому пользователю',
            )
        return AssignRoleResponse(
            message='Роль успешно назначена',
            user_id=user_id,
            role_id=role_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.delete('/{role_id}/revoke/{user_id}', response_model=dict)
async def revoke_role(
        role_id: UUID,
        user_id: UUID,
        current_user: User = Depends(check_role_permission('admin')),
        role_service: RoleService = Depends(get_role_service),
) -> dict:
    """
    Отозвать роль у пользователя (только для admin).

    Args:
        role_id: UUID роли
        user_id: UUID пользователя
        current_user: Текущий аутентифицированный пользователь (admin)
        role_service: Сервис ролей

    Returns:
        Подтверждение отзыва

    Raises:
        HTTPException: Если пользователь/роль не найдены или роль не назначена
    """
    try:
        revoked = await role_service.revoke_role_from_user(user_id, role_id)
        if not revoked:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='Роль не назначена этому пользователю',
            )
        return {'message': 'Роль успешно отозвана'}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.post('/check-permission', response_model=CheckPermissionResponse)
async def check_permission(
        request: CheckPermissionRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        cache: AbstractCache = Depends(get_cache),
) -> CheckPermissionResponse:
    """
    Проверить, имеет ли пользователь требуемое разрешение.

    Args:
        request: Запрос на проверку разрешения
        current_user: Текущий аутентифицированный пользователь
        db: Сессия базы данных
        cache: Хранилище кэша

    Returns:
        Результат проверки разрешения

    Raises:
        HTTPException: Если запрос невалиден или пользователь не найден
    """

    # Определяем, какого пользователя проверять
    user_id = request.user_id if request.user_id else current_user.id

    # Если проверяем другого пользователя, требуется admin
    if (
            request.user_id
            and request.user_id != current_user.id
            and not current_user.is_superuser
    ):
        # Проверяем, является ли текущий пользователь admin
        role_repo = RoleRepository(db)
        user_roles = await role_repo.get_user_roles(current_user.id)
        if not any(role.name == 'admin' for role in user_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Только admin может проверять разрешения других пользователей',
            )

    # Получаем целевого пользователя
    user_repo = UserRepository(db)
    target_user = await user_repo.get_by_id(user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Пользователь не найден',
        )

    # Суперпользователь всегда имеет разрешение
    if target_user.is_superuser:
        return CheckPermissionResponse(
            has_permission=True,
            user_id=user_id,
            roles=[],
        )

    # Получаем роли пользователя
    role_repo = RoleRepository(db)
    user_roles = await role_repo.get_user_roles(user_id)
    role_names = [role.name for role in user_roles]

    # Проверяем разрешение
    has_permission = False
    if request.required_role:
        has_permission = request.required_role in role_names
    elif request.required_permission:
        # Для будущего расширения - система разрешений
        # Пока проверяем только роли
        has_permission = False
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Необходимо указать required_role или required_permission',
        )

    return CheckPermissionResponse(
        has_permission=has_permission,
        user_id=user_id,
        roles=role_names,
    )
