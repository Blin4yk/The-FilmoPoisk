"""Сервис для проверки доступа к фильмам."""
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from db.interface.interfaces import AbstractCache
from db.repositories.role_repository import RoleRepository
from models.user import User


class PermissionService:
    """Сервис для проверки прав доступа пользователей."""

    def __init__(self, session: AsyncSession, cache: AbstractCache):
        """
        Инициализация сервиса проверки прав доступа.

        Args:
            session: Сессия базы данных
            cache: Хранилище кэша
        """
        self.session = session
        self.cache = cache
        self.role_repo = RoleRepository(session)

    async def can_access_new_film(self, user: User | None, film_creation_date: datetime | None) -> bool:
        """
        Проверить, может ли пользователь получить доступ к фильму на основе даты его создания.

        Фильмы новее 3 лет требуют роль 'subscriber'.

        Args:
            user: Объект пользователя или None для анонимного
            film_creation_date: Дата создания/релиза фильма

        Returns:
            True если пользователь имеет доступ, False в противном случае
        """
        # Если дата создания отсутствует, разрешаем доступ (старые фильмы)
        if not film_creation_date:
            return True

        # Проверяем, старше ли фильм 3 лет
        three_years_ago = datetime.utcnow() - timedelta(days=3 * 365)
        if film_creation_date < three_years_ago:
            # Старые фильмы доступны всем
            return True

        # Новые фильмы (младше 3 лет) требуют роль subscriber
        # Анонимные пользователи не имеют доступа
        if not user:
            return False

        # Суперпользователь всегда имеет доступ
        if user.is_superuser:
            return True

        # Проверяем наличие роли subscriber у пользователя
        return await self.user_has_role(user.id, 'subscriber')

    async def user_has_role(self, user_id: UUID, role_name: str) -> bool:
        """
        Проверить, имеет ли пользователь конкретную роль.

        Args:
            user_id: UUID пользователя
            role_name: Название роли

        Returns:
            True если пользователь имеет роль
        """
        # Сначала проверяем кэш
        roles_cache_key = f'user:roles:{user_id}'
        cached_roles = await self.cache.get(roles_cache_key)
        if cached_roles:
            import json
            roles = json.loads(cached_roles)
            return role_name in roles

        # Получаем из базы данных
        roles = await self.role_repo.get_user_roles(user_id)
        role_names = [role.name for role in roles]

        # Кэшируем роли
        import json
        await self.cache.set(roles_cache_key, json.dumps(role_names), expire=600)

        return role_name in role_names

