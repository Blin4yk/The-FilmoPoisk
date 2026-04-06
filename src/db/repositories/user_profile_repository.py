from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.profile import UserProfile


class UserProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(
        self, profile_id: UUID, include_deleted: bool = False
    ) -> UserProfile | None:
        stmt: Select[tuple[UserProfile]] = select(UserProfile).where(
            UserProfile.id == profile_id
        )
        if not include_deleted:
            stmt = stmt.where(UserProfile.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_user_id(
        self, user_id: UUID, include_deleted: bool = False
    ) -> UserProfile | None:
        stmt: Select[tuple[UserProfile]] = select(UserProfile).where(
            UserProfile.user_id == user_id
        )
        if not include_deleted:
            stmt = stmt.where(UserProfile.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> UserProfile | None:
        stmt: Select[tuple[UserProfile]] = select(UserProfile).where(
            UserProfile.phone == phone
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_profiles(
        self,
        page: int,
        size: int,
        phone: str | None = None,
        full_name: str | None = None,
    ) -> tuple[Sequence[UserProfile], int]:
        stmt: Select[tuple[UserProfile]] = select(UserProfile).where(
            UserProfile.deleted_at.is_(None)
        )

        if phone:
            stmt = stmt.where(UserProfile.phone.ilike(f'%{phone}%'))
        if full_name:
            stmt = stmt.where(UserProfile.full_name.ilike(f'%{full_name}%'))

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await self.session.execute(total_stmt)
        total = int(total_result.scalar_one() or 0)

        stmt = stmt.order_by(UserProfile.created_at.desc()).offset(
            (page - 1) * size
        ).limit(size)
        result = await self.session.execute(stmt)
        items = result.scalars().all()
        return items, total

    async def create(
        self,
        user_id: UUID,
        full_name: str,
        phone: str,
    ) -> UserProfile:
        profile = UserProfile(user_id=user_id, full_name=full_name, phone=phone)
        self.session.add(profile)
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def update(
        self,
        profile: UserProfile,
        full_name: str | None = None,
        phone: str | None = None,
    ) -> UserProfile:
        if full_name is not None:
            profile.full_name = full_name
        if phone is not None:
            profile.phone = phone

        await self.session.commit()
        await self.session.refresh(profile)
        return profile

    async def soft_delete(self, profile: UserProfile) -> None:
        profile.deleted_at = func.now()
        await self.session.commit()

    async def restore(self, profile: UserProfile) -> UserProfile:
        profile.deleted_at = None
        await self.session.commit()
        await self.session.refresh(profile)
        return profile

