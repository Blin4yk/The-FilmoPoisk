"""Зависимости для аутентификации в FastAPI."""
import json
from uuid import UUID

from core.jwt import jwt_service
from db.interface.interfaces import AbstractCache
from db.postgres import get_db
from db.redis import get_cache
from fastapi import Depends, HTTPException, Request, status
from models.user import User
from services.auth import AuthService
from sqlalchemy.ext.asyncio import AsyncSession


async def get_current_user_optional(
    request: Request,
    db: AsyncSession = Depends(get_db),
    cache: AbstractCache = Depends(get_cache),
) -> User | None:
    """
    Получить текущего пользователя из токена (опционально - возвращает None если не аутентифицирован).
    Теперь токен ищется сначала в куках, затем в заголовке Authorization.

    Args:
        request: Объект запроса FastAPI
        db: Сессия базы данных
        cache: Хранилище кэша

    Returns:
        Объект User или None если не аутентифицирован
    """
    # Пробуем получить токен из куков
    token = request.cookies.get('access_token')

    # Если нет в куках, пробуем получить из заголовка Authorization
    if not token:
        authorization = request.headers.get('Authorization')
        if authorization and authorization.startswith('Bearer '):
            token = authorization.split(' ')[1]

    if not token:
        return None

    payload = jwt_service.verify_token(token, token_type='access')
    if not payload:
        return None

    user_id_str = payload.get('sub')
    if not user_id_str:
        return None

    user_id = UUID(user_id_str)

    # Проверяем поколение (для logout-all)
    generation = payload.get('generation', 0)
    cache_key = f'user:generation:{user_id}'
    cached_generation = await cache.get(cache_key)
    if cached_generation and int(cached_generation) != generation:
        return None

    # Получаем из базы данных (нам всегда нужны свежие данные для проверки суперпользователя)
    from db.repositories.user_repository import UserRepository

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)
    if not user:
        return None

    # Кэшируем данные пользователя (исключая чувствительную информацию) для будущих запросов
    user_cache_key = f'user:{user_id}'
    user_data = {
        'id': str(user.id),
        'username': user.username,
        'email': user.email,
        'is_superuser': user.is_superuser,
    }
    await cache.set(user_cache_key, json.dumps(user_data), expire=300)

    return user


async def get_current_user(
    current_user: User | None = Depends(get_current_user_optional),
) -> User:
    """
    Получить текущего пользователя из токена (обязательно).

    Args:
        current_user: Текущий пользователь из опциональной зависимости

    Returns:
        Объект User

    Raises:
        HTTPException: Если пользователь не аутентифицирован
    """
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Не аутентифицирован',
            headers={'WWW-Authenticate': 'Bearer'},
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Получить текущего суперпользователя (обязательно).

    Args:
        current_user: Текущий пользователь

    Returns:
        Объект User суперпользователя

    Raises:
        HTTPException: Если пользователь не является суперпользователем
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Недостаточно прав. Требуется доступ суперпользователя.',
        )
    return current_user


def check_role_permission(role_name: str):
    """
    Фабрика зависимостей для проверки прав доступа по роли.

    Args:
        role_name: Требуемое название роли

    Returns:
        Функция зависимости
    """

    async def _check_role(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        cache: AbstractCache = Depends(get_cache),
    ) -> User:
        """
        Проверить, имеет ли пользователь требуемую роль.

        Args:
            current_user: Текущий пользователь
            db: Сессия базы данных
            cache: Хранилище кэша

        Returns:
            Объект User если имеет роль

        Raises:
            HTTPException: Если доступ запрещен
        """
        # Суперпользователь всегда имеет доступ
        if current_user.is_superuser:
            return current_user

        # Проверяем, имеет ли пользователь роль (сначала из кэша)
        roles_cache_key = f'user:roles:{current_user.id}'
        cached_roles = await cache.get(roles_cache_key)
        if cached_roles:
            roles = json.loads(cached_roles)
        else:
            # Получаем из базы данных
            from db.repositories.role_repository import RoleRepository

            role_repo = RoleRepository(db)
            user_roles = await role_repo.get_user_roles(current_user.id)
            roles = [role.name for role in user_roles]
            # Кэшируем роли
            await cache.set(roles_cache_key, json.dumps(roles), expire=600)

        if role_name not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f'Недостаточно прав. Требуется роль: {role_name}',
            )

        return current_user

    return _check_role


# Удобная фабрика зависимостей для роли admin
def require_admin_dependency():
    """Создать зависимость для требования роли admin."""
    return Depends(check_role_permission('admin'))


def get_auth_service(
    db: AsyncSession = Depends(get_db),
    cache: AbstractCache = Depends(get_cache),
) -> AuthService:
    """
    Получить экземпляр сервиса аутентификации.

    Args:
        db: Сессия базы данных
        cache: Хранилище кэша

    Returns:
        Экземпляр AuthService
    """
    return AuthService(db, cache)
