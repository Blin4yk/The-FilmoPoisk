"""Репозиторий для операций с историей входов в базе данных."""
from uuid import UUID

from models.role import LoginHistory
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class LoginHistoryRepository:
    """Репозиторий для операций с историей входов в базе данных."""

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория с сессией базы данных.

        Args:
            session: Сессия базы данных
        """
        self.session = session

    async def create(
        self,
        user_id: UUID,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LoginHistory:
        """
        Создать запись истории входа.

        Args:
            user_id: UUID пользователя
            ip_address: IP адрес
            user_agent: User agent строка

        Returns:
            Созданный объект LoginHistory
        """
        login_history = LoginHistory(
            user_id=user_id, ip_address=ip_address, user_agent=user_agent
        )
        self.session.add(login_history)
        await self.session.commit()
        await self.session.refresh(login_history)
        return login_history

    async def get_by_user_id(
        self, user_id: UUID, page: int = 1, size: int = 10
    ) -> tuple[list[LoginHistory], int]:
        """
        Получить историю входов пользователя с пагинацией.

        Args:
            user_id: UUID пользователя
            page: Номер страницы (начиная с 1)
            size: Размер страницы

        Returns:
            Кортеж из (список записей LoginHistory, общее количество)
        """
        # Получаем общее количество
        count_result = await self.session.execute(
            select(func.count())
            .select_from(LoginHistory)
            .where(LoginHistory.user_id == user_id)
        )
        total = count_result.scalar() or 0

        # Получаем результаты с пагинацией
        offset = (page - 1) * size
        result = await self.session.execute(
            select(LoginHistory)
            .where(LoginHistory.user_id == user_id)
            .order_by(LoginHistory.login_at.desc())
            .offset(offset)
            .limit(size)
        )
        items = list(result.scalars().all())

        return items, total
