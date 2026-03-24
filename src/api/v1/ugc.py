from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.v1.dependencies.auth import get_current_user
from api.v1.scheme.ugc_scheme import (
    BookmarkIn,
    BookmarkOut,
    DeleteResponse,
    FilmFeedbackOut,
    LikeIn,
    LikeOut,
    RatingIn,
    RatingOut,
    ReviewIn,
    ReviewOut,
    ReviewUpdate,
)
from db.mongo import get_mongo_db
from models.user import User
from services.ugc import UGCService

router = APIRouter(prefix='/api/v1/ugc', tags=['ugc'])


def get_ugc_service(db: AsyncIOMotorDatabase = Depends(get_mongo_db)) -> UGCService:
    return UGCService(db)


@router.put('/bookmarks', response_model=BookmarkOut)
async def upsert_bookmark(
    payload: BookmarkIn,
    current_user: User = Depends(get_current_user),
    service: UGCService = Depends(get_ugc_service),
) -> BookmarkOut:
    return BookmarkOut(**await service.upsert_bookmark(str(current_user.id), payload.model_dump()))


@router.get('/bookmarks', response_model=list[BookmarkOut])
async def list_bookmarks(
    current_user: User = Depends(get_current_user),
    service: UGCService = Depends(get_ugc_service),
) -> list[BookmarkOut]:
    return [BookmarkOut(**item) for item in await service.list_bookmarks(str(current_user.id))]


@router.delete('/bookmarks/{film_id}', response_model=DeleteResponse, status_code=status.HTTP_200_OK)
async def delete_bookmark(
    film_id: str,
    current_user: User = Depends(get_current_user),
    service: UGCService = Depends(get_ugc_service),
) -> DeleteResponse:
    await service.delete_bookmark(str(current_user.id), film_id)
    return DeleteResponse()


@router.put('/likes', response_model=LikeOut)
async def upsert_like(
    payload: LikeIn,
    current_user: User = Depends(get_current_user),
    service: UGCService = Depends(get_ugc_service),
) -> LikeOut:
    return LikeOut(**await service.upsert_like(str(current_user.id), payload.model_dump()))


@router.delete('/likes/{film_id}', response_model=DeleteResponse)
async def delete_like(
    film_id: str,
    current_user: User = Depends(get_current_user),
    service: UGCService = Depends(get_ugc_service),
) -> DeleteResponse:
    await service.delete_like(str(current_user.id), film_id)
    return DeleteResponse()


@router.put('/ratings', response_model=RatingOut)
async def upsert_rating(
    payload: RatingIn,
    current_user: User = Depends(get_current_user),
    service: UGCService = Depends(get_ugc_service),
) -> RatingOut:
    return RatingOut(**await service.upsert_rating(str(current_user.id), payload.model_dump()))


@router.get('/ratings', response_model=list[RatingOut])
async def list_ratings(
    current_user: User = Depends(get_current_user),
    service: UGCService = Depends(get_ugc_service),
) -> list[RatingOut]:
    return [RatingOut(**item) for item in await service.list_ratings(str(current_user.id))]


@router.delete('/ratings/{film_id}', response_model=DeleteResponse)
async def delete_rating(
    film_id: str,
    current_user: User = Depends(get_current_user),
    service: UGCService = Depends(get_ugc_service),
) -> DeleteResponse:
    await service.delete_rating(str(current_user.id), film_id)
    return DeleteResponse()


@router.post('/reviews', response_model=ReviewOut, status_code=status.HTTP_201_CREATED)
async def create_review(
    payload: ReviewIn,
    current_user: User = Depends(get_current_user),
    service: UGCService = Depends(get_ugc_service),
) -> ReviewOut:
    return ReviewOut(**await service.create_review(str(current_user.id), payload.model_dump()))


@router.patch('/reviews/{review_id}', response_model=ReviewOut)
async def update_review(
    review_id: str,
    payload: ReviewUpdate,
    current_user: User = Depends(get_current_user),
    service: UGCService = Depends(get_ugc_service),
) -> ReviewOut:
    return ReviewOut(**await service.update_review(str(current_user.id), review_id, payload.model_dump(exclude_none=True)))


@router.delete('/reviews/{review_id}', response_model=DeleteResponse)
async def delete_review(
    review_id: str,
    current_user: User = Depends(get_current_user),
    service: UGCService = Depends(get_ugc_service),
) -> DeleteResponse:
    await service.delete_review(str(current_user.id), review_id)
    return DeleteResponse()


@router.get('/reviews/{film_id}', response_model=list[ReviewOut])
async def list_reviews(
    film_id: str,
    service: UGCService = Depends(get_ugc_service),
) -> list[ReviewOut]:
    return [ReviewOut(**item) for item in await service.list_reviews(film_id)]


@router.get('/films/{film_id}/feedback', response_model=FilmFeedbackOut)
async def get_film_feedback(
    film_id: str,
    service: UGCService = Depends(get_ugc_service),
) -> FilmFeedbackOut:
    return FilmFeedbackOut(**await service.get_film_feedback(film_id))