"""Репозиторий для операций с ролями в базе данных."""
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.role import Role, UserRole


class RoleRepository:
    """Репозиторий для операций с ролями в базе данных."""

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория с сессией базы данных.

        Args:
            session: Сессия базы данных
        """
        self.session = session

    async def get_by_id(self, role_id: UUID) -> Role | None:
        """
        Получить роль по ID.

        Args:
            role_id: UUID роли

        Returns:
            Объект Role или None если не найдена
        """
        result = await self.session.execute(select(Role).where(Role.id == role_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Role | None:
        """
        Получить роль по имени.

        Args:
            name: Название роли

        Returns:
            Объект Role или None если не найдена
        """
        result = await self.session.execute(select(Role).where(Role.name == name))
        return result.scalar_one_or_none()

    async def get_all(self, page: int = 1, size: int = 50) -> tuple[list[Role], int]:
        """
        Получить все роли с пагинацией.

        Args:
            page: Номер страницы (начиная с 1)
            size: Размер страницы

        Returns:
            Кортеж из (список объектов Role, общее количество)
        """
        # Получаем общее количество
        count_result = await self.session.execute(select(func.count()).select_from(Role))
        total = count_result.scalar() or 0

        # Получаем результаты с пагинацией
        offset = (page - 1) * size
        result = await self.session.execute(select(Role).order_by(Role.name).offset(offset).limit(size))
        items = list(result.scalars().all())

        return items, total

    async def create(self, name: str, description: str | None = None) -> Role:
        """
        Создать новую роль.

        Args:
            name: Название роли
            description: Описание роли

        Returns:
            Созданный объект Role
        """
        role = Role(name=name, description=description)
        self.session.add(role)
        await self.session.commit()
        await self.session.refresh(role)
        return role

    async def update(self, role_id: UUID, name: str | None = None, description: str | None = None) -> Role | None:
        """
        Обновить роль.

        Args:
            role_id: UUID роли
            name: Новое название роли (опционально)
            description: Новое описание роли (опционально)

        Returns:
            Обновленный объект Role или None если не найдена
        """
        update_values = {}
        if name is not None:
            update_values['name'] = name
        if description is not None:
            update_values['description'] = description

        if not update_values:
            return await self.get_by_id(role_id)

        from sqlalchemy import update

        await self.session.execute(update(Role).where(Role.id == role_id).values(**update_values))
        await self.session.commit()
        return await self.get_by_id(role_id)

    async def delete(self, role_id: UUID) -> bool:
        """
        Удалить роль.

        Args:
            role_id: UUID роли

        Returns:
            True если удалена, False если не найдена
        """
        role = await self.get_by_id(role_id)
        if not role:
            return False

        await self.session.execute(delete(Role).where(Role.id == role_id))
        await self.session.commit()
        return True

    async def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> UserRole | None:
        """
        Назначить роль пользователю.

        Args:
            user_id: UUID пользователя
            role_id: UUID роли

        Returns:
            Созданный объект UserRole или None если уже существует
        """
        # Проверяем, не назначена ли уже
        existing = await self.session.execute(
            select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        )
        if existing.scalar_one_or_none():
            return None

        user_role = UserRole(user_id=user_id, role_id=role_id)
        self.session.add(user_role)
        await self.session.commit()
        await self.session.refresh(user_role)
        return user_role

    async def revoke_role_from_user(self, user_id: UUID, role_id: UUID) -> bool:
        """
        Отозвать роль у пользователя.

        Args:
            user_id: UUID пользователя
            role_id: UUID роли

        Returns:
            True если отозвана, False если не найдена
        """
        result = await self.session.execute(
            delete(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def get_user_roles(self, user_id: UUID) -> list[Role]:
        """
        Получить все роли, назначенные пользователю.

        Args:
            user_id: UUID пользователя

        Returns:
            Список объектов Role
        """
        result = await self.session.execute(
            select(Role)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
            .options(selectinload(Role.user_roles))
        )
        return list(result.scalars().all())

    async def check_role_has_users(self, role_id: UUID) -> bool:
        """
        Проверить, назначена ли роль каким-либо пользователям.

        Args:
            role_id: UUID роли

        Returns:
            True если роль назначена пользователям, False в противном случае
        """
        result = await self.session.execute(
            select(func.count()).select_from(UserRole).where(UserRole.role_id == role_id)
        )
        count = result.scalar() or 0
        return count > 0

