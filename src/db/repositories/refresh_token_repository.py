"""Репозиторий для операций с refresh токенами в базе данных."""
from datetime import datetime
from uuid import UUID

from models.role import RefreshToken
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


class RefreshTokenRepository:
    """Репозиторий для операций с refresh токенами в базе данных."""

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория с сессией базы данных.

        Args:
            session: Сессия базы данных
        """
        self.session = session

    async def create(
        self, user_id: UUID, token_jti: str, expires_at: datetime
    ) -> RefreshToken:
        """
        Создать запись refresh токена.

        Args:
            user_id: UUID пользователя
            token_jti: JWT ID (jti claim)
            expires_at: Дата истечения токена

        Returns:
            Созданный объект RefreshToken
        """
        refresh_token = RefreshToken(
            user_id=user_id, token_jti=token_jti, expires_at=expires_at
        )
        self.session.add(refresh_token)
        await self.session.commit()
        await self.session.refresh(refresh_token)
        return refresh_token

    async def get_by_jti(self, token_jti: str) -> RefreshToken | None:
        """
        Получить refresh токен по JWT ID.

        Args:
            token_jti: JWT ID

        Returns:
            Объект RefreshToken или None если не найден
        """
        result = await self.session.execute(
            select(RefreshToken).where(RefreshToken.token_jti == token_jti)
        )
        return result.scalar_one_or_none()

    async def delete_by_jti(self, token_jti: str) -> bool:
        """
        Удалить refresh токен по JWT ID.

        Args:
            token_jti: JWT ID

        Returns:
            True если удален, False если не найден
        """
        result = await self.session.execute(
            delete(RefreshToken).where(RefreshToken.token_jti == token_jti)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def delete_all_by_user_id(self, user_id: UUID) -> int:
        """
        Удалить все refresh токены пользователя.

        Args:
            user_id: UUID пользователя

        Returns:
            Количество удаленных токенов
        """
        result = await self.session.execute(
            delete(RefreshToken).where(RefreshToken.user_id == user_id)
        )
        await self.session.commit()
        return result.rowcount

    async def cleanup_expired(self) -> int:
        """
        Удалить все истекшие refresh токены.

        Returns:
            Количество удаленных токенов
        """
        result = await self.session.execute(
            delete(RefreshToken).where(RefreshToken.expires_at < datetime.utcnow())
        )
        await self.session.commit()
        return result.rowcount
