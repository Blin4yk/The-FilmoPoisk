from uuid import UUID

from db.repositories.user_profile_repository import UserProfileRepository
from models.profile import UserProfile
from services.ugc import UGCService
from sqlalchemy.ext.asyncio import AsyncSession


class ProfileService:
    def __init__(self, session: AsyncSession, ugc_service: UGCService) -> None:
        self.session = session
        self.profile_repo = UserProfileRepository(session)
        self.ugc_service = ugc_service

    async def get_or_create_self_profile(
        self, user_id: UUID, full_name: str | None, phone: str | None
    ) -> UserProfile:
        profile = await self.profile_repo.get_by_user_id(user_id)
        if profile:
            return profile
        if full_name is None or phone is None:
            raise ValueError('full_name and phone are required to create profile')
        return await self.profile_repo.create(user_id=user_id, full_name=full_name, phone=phone)

    async def get_profile_by_user(self, user_id: UUID) -> UserProfile | None:
        return await self.profile_repo.get_by_user_id(user_id)

    async def update_self_profile(
        self, user_id: UUID, full_name: str | None, phone: str | None
    ) -> UserProfile:
        profile = await self.profile_repo.get_by_user_id(user_id)
        if not profile:
            raise LookupError('profile_not_found')
        return await self.profile_repo.update(profile, full_name=full_name, phone=phone)

    async def delete_self_profile(self, user_id: UUID) -> None:
        profile = await self.profile_repo.get_by_user_id(user_id)
        if not profile:
            raise LookupError('profile_not_found')
        await self.profile_repo.delete(profile)

    async def list_profiles(
        self, page: int, size: int, phone: str | None = None, full_name: str | None = None
    ) -> tuple[list[UserProfile], int]:
        items, total = await self.profile_repo.list_profiles(
            page=page, size=size, phone=phone, full_name=full_name
        )
        return list(items), total

    async def get_user_ugc(self, user_id: UUID) -> dict:
        user_id_str = str(user_id)
        bookmarks = await self.ugc_service.list_bookmarks(user_id_str)
        liked_films = await self.ugc_service.list_likes(user_id_str)
        ratings = await self.ugc_service.list_ratings(user_id_str)
        # для профиля полезно видеть собственные отзывы; лайки опциональны
        reviews_cursor = self.ugc_service.db.reviews.find({'user_id': user_id_str}).sort(
            'created_at', -1
        )
        reviews = [self.ugc_service._serialize(doc) async for doc in reviews_cursor]
        return {
            'bookmarks': bookmarks,
            'liked_films': liked_films,
            'ratings': ratings,
            'reviews': reviews,
        }

