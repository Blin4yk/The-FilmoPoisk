"""Репозиторий для операций с пользователями в базе данных."""
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.role import UserRole
from models.user import User


class UserRepository:
    """Репозиторий для операций с пользователями в базе данных."""

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория с сессией базы данных.

        Args:
            session: Сессия базы данных
        """
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        """
        Получить пользователя по ID.

        Args:
            user_id: UUID пользователя

        Returns:
            Объект User или None если не найден
        """
        result = await self.session.execute(
            select(User).where(User.id == user_id).options(selectinload(User.roles))
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """
        Получить пользователя по username.

        Args:
            username: Имя пользователя

        Returns:
            Объект User или None если не найден
        """
        result = await self.session.execute(
            select(User).where(User.username == username).options(selectinload(User.roles))
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """
        Получить пользователя по email.

        Args:
            email: Email пользователя

        Returns:
            Объект User или None если не найден
        """
        result = await self.session.execute(
            select(User).where(User.email == email).options(selectinload(User.roles))
        )
        return result.scalar_one_or_none()

    async def create(self, username: str, email: str, password_hash: str, is_superuser: bool = True) -> User:
        """
        Создать нового пользователя.

        Args:
            username: Имя пользователя
            email: Email пользователя
            password_hash: Хешированный пароль
            is_superuser: Является ли пользователь суперпользователем

        Returns:
            Созданный объект User
        """
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            is_superuser=is_superuser,
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        # Перезагружаем пользователя с ролями
        result = await self.session.execute(
            select(User).where(User.id == user.id).options(selectinload(User.roles))
        )
        return result.scalar_one()

    async def update_username(self, user_id: UUID, new_username: str) -> User | None:
        """
        Обновить username пользователя.

        Args:
            user_id: UUID пользователя
            new_username: Новый username

        Returns:
            Обновленный объект User или None если не найден
        """
        await self.session.execute(update(User).where(User.id == user_id).values(username=new_username))
        await self.session.commit()
        return await self.get_by_id(user_id)

    async def update_password(self, user_id: UUID, new_password_hash: str) -> User | None:
        """
        Обновить пароль пользователя.

        Args:
            user_id: UUID пользователя
            new_password_hash: Новый хеш пароля

        Returns:
            Обновленный объект User или None если не найден
        """
        await self.session.execute(update(User).where(User.id == user_id).values(password_hash=new_password_hash))
        await self.session.commit()
        return await self.get_by_id(user_id)

    async def update_username_and_password(
        self, user_id: UUID, new_username: str | None, new_password_hash: str | None
    ) -> User | None:
        """
        Обновить username и/или пароль пользователя.

        Args:
            user_id: UUID пользователя
            new_username: Новый username (опционально)
            new_password_hash: Новый хеш пароля (опционально)

        Returns:
            Обновленный объект User или None если не найден
        """
        update_values = {}
        if new_username is not None:
            update_values['username'] = new_username
        if new_password_hash is not None:
            update_values['password_hash'] = new_password_hash

        if update_values:
            await self.session.execute(update(User).where(User.id == user_id).values(**update_values))
            await self.session.commit()
        return await self.get_by_id(user_id)

