from uuid import UUID

from api.v1.dependencies.auth import check_role_permission, get_current_user
from api.v1.dependencies.dependency import PaginationParams
from api.v1.scheme.profile_scheme import (
    UserProfileCreate,
    UserProfileOut,
    UserProfileUpdate,
    UserProfileWithUGC,
)
from db.mongo import get_mongo_db
from db.postgres import get_db
from fastapi import APIRouter, Depends, HTTPException, Query, status
from models.user import User
from motor.motor_asyncio import AsyncIOMotorDatabase
from services.profile import ProfileService
from services.ugc import UGCService
from sqlalchemy.ext.asyncio import AsyncSession


router = APIRouter(prefix='/api/v1/profile', tags=['profile'])


def get_profile_service(
    db: AsyncSession = Depends(get_db),
    mongo: AsyncIOMotorDatabase = Depends(get_mongo_db),
) -> ProfileService:
    ugc_service = UGCService(mongo)
    return ProfileService(db, ugc_service)


class ProfileListParams(PaginationParams):
    def __init__(
        self,
        page: int = Query(1, ge=1, description='Номер страницы'),
        size: int = Query(50, ge=1, le=100, description='Размер страницы'),
        phone: str | None = Query(None, description='Фильтр по телефону'),
        full_name: str | None = Query(None, description='Фильтр по ФИО'),
    ):
        super().__init__(sort='', page=page, size=size)
        self.phone = phone
        self.full_name = full_name


@router.get('/me', response_model=UserProfileWithUGC)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> UserProfileWithUGC:
    profile = await service.get_profile_by_user(current_user.id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Профиль не найден',
        )
    ugc = await service.get_user_ugc(current_user.id)
    return UserProfileWithUGC(
        **UserProfileOut.model_validate(profile).model_dump(),
        bookmarks=ugc['bookmarks'],
        liked_films=ugc['liked_films'],
        ratings=ugc['ratings'],
        reviews=ugc['reviews'],
    )


@router.post('/me', response_model=UserProfileOut, status_code=status.HTTP_201_CREATED)
async def create_my_profile(
    payload: UserProfileCreate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> UserProfileOut:
    existing = await service.get_profile_by_user(current_user.id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Профиль уже существует',
        )
    try:
        profile = await service.get_or_create_self_profile(
            current_user.id, payload.full_name, payload.phone
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    return UserProfileOut.model_validate(profile)


@router.patch('/me', response_model=UserProfileOut)
async def update_my_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> UserProfileOut:
    if payload.full_name is None and payload.phone is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Необходимо указать хотя бы одно поле для обновления',
        )
    try:
        profile = await service.update_self_profile(
            current_user.id, payload.full_name, payload.phone
        )
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Профиль не найден',
        ) from None
    return UserProfileOut.model_validate(profile)


@router.delete('/me', status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_profile(
    current_user: User = Depends(get_current_user),
    service: ProfileService = Depends(get_profile_service),
) -> None:
    try:
        await service.delete_self_profile(current_user.id)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Профиль не найден',
        ) from None


@router.get(
    '/',
    response_model=list[UserProfileOut],
)
async def list_profiles(
    params: ProfileListParams = Depends(),
    current_user: User = Depends(check_role_permission('admin')),
    service: ProfileService = Depends(get_profile_service),
) -> list[UserProfileOut]:
    items, total = await service.list_profiles(
        page=params.page, size=params.size, phone=params.phone, full_name=params.full_name
    )
    # total и pages можно вернуть в заголовках или через отдельную схему, но для простоты возвращаем только список
    return [UserProfileOut.model_validate(item) for item in items]


@router.get('/{user_id}', response_model=UserProfileWithUGC)
async def get_user_profile_admin(
    user_id: UUID,
    current_user: User = Depends(check_role_permission('admin')),
    service: ProfileService = Depends(get_profile_service),
) -> UserProfileWithUGC:
    profile = await service.get_profile_by_user(user_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Профиль не найден',
        )
    ugc = await service.get_user_ugc(user_id)
    return UserProfileWithUGC(
        **UserProfileOut.model_validate(profile).model_dump(),
        bookmarks=ugc['bookmarks'],
        liked_films=ugc['liked_films'],
        ratings=ugc['ratings'],
        reviews=ugc['reviews'],
    )

