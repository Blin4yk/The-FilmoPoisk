"""Сервис управления ролями."""
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from api.v1.scheme.role_scheme import RoleCreate, RoleUpdate
from db.interface.interfaces import AbstractCache
from db.repositories.role_repository import RoleRepository
from db.repositories.user_repository import UserRepository
from models.role import Role


class RoleService:
    """Сервис для операций управления ролями."""

    def __init__(self, session: AsyncSession, cache: AbstractCache):
        """
        Инициализация сервиса ролей.

        Args:
            session: Сессия базы данных
            cache: Хранилище кэша
        """
        self.session = session
        self.cache = cache
        self.role_repo = RoleRepository(session)
        self.user_repo = UserRepository(session)

    async def create_role(self, role_data: RoleCreate) -> Role:
        """
        Создать новую роль.

        Args:
            role_data: Данные для создания роли

        Returns:
            Созданный объект Role

        Raises:
            ValueError: Если роль с таким именем уже существует
        """
        existing = await self.role_repo.get_by_name(role_data.name)
        if existing:
            raise ValueError('Роль с таким именем уже существует')

        return await self.role_repo.create(role_data.name, role_data.description)

    async def get_role_by_id(self, role_id: UUID) -> Role | None:
        """
        Получить роль по ID.

        Args:
            role_id: UUID роли

        Returns:
            Объект Role или None если не найдена
        """
        return await self.role_repo.get_by_id(role_id)

    async def get_all_roles(self, page: int = 1, size: int = 50) -> tuple[list[Role], int]:
        """
        Получить все роли с пагинацией.

        Args:
            page: Номер страницы
            size: Размер страницы

        Returns:
            Кортеж из (список ролей, общее количество)
        """
        return await self.role_repo.get_all(page, size)

    async def update_role(self, role_id: UUID, role_data: RoleUpdate) -> Role | None:
        """
        Обновить роль.

        Args:
            role_id: UUID роли
            role_data: Данные для обновления роли

        Returns:
            Обновленный объект Role или None если не найдена

        Raises:
            ValueError: Если новое имя уже существует
        """
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            return None

        if role_data.name and role_data.name != role.name:
            existing = await self.role_repo.get_by_name(role_data.name)
            if existing:
                raise ValueError('Роль с таким именем уже существует')

        return await self.role_repo.update(role_id, role_data.name, role_data.description)

    async def delete_role(self, role_id: UUID) -> bool:
        """
        Удалить роль.

        Args:
            role_id: UUID роли

        Returns:
            True если удалена, False если не найдена

        Raises:
            ValueError: Если роль назначена пользователям
        """
        # Проверяем, назначена ли роль каким-либо пользователям
        has_users = await self.role_repo.check_role_has_users(role_id)
        if has_users:
            raise ValueError('Невозможно удалить роль: она назначена одному или нескольким пользователям')

        return await self.role_repo.delete(role_id)

    async def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> bool:
        """
        Назначить роль пользователю.

        Args:
            user_id: UUID пользователя
            role_id: UUID роли

        Returns:
            True если назначена, False если уже назначена

        Raises:
            ValueError: Если пользователь или роль не найдены
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError('Пользователь не найден')

        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise ValueError('Роль не найдена')

        result = await self.role_repo.assign_role_to_user(user_id, role_id)
        if result is None:  # Уже назначена
            return False

        # Инвалидируем кэш пользователя
        await self.cache.delete(f'user:{user_id}')
        await self.cache.delete(f'user:roles:{user_id}')

        return True

    async def revoke_role_from_user(self, user_id: UUID, role_id: UUID) -> bool:
        """
        Отозвать роль у пользователя.

        Args:
            user_id: UUID пользователя
            role_id: UUID роли

        Returns:
            True если отозвана, False если не найдена

        Raises:
            ValueError: Если пользователь или роль не найдены
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError('Пользователь не найден')

        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise ValueError('Роль не найдена')

        result = await self.role_repo.revoke_role_from_user(user_id, role_id)
        if not result:
            return False

        # Инвалидируем кэш пользователя
        await self.cache.delete(f'user:{user_id}')
        await self.cache.delete(f'user:roles:{user_id}')

        return True

    async def get_user_roles(self, user_id: UUID) -> list[Role]:
        """
        Получить все роли, назначенные пользователю.

        Args:
            user_id: UUID пользователя

        Returns:
            Список объектов Role
        """
        return await self.role_repo.get_user_roles(user_id)

    async def check_user_has_role(self, user_id: UUID, role_name: str) -> bool:
        """
        Проверить, имеет ли пользователь конкретную роль.

        Args:
            user_id: UUID пользователя
            role_name: Название роли

        Returns:
            True если пользователь имеет роль, False в противном случае
        """
        roles = await self.role_repo.get_user_roles(user_id)
        return any(role.name == role_name for role in roles)

