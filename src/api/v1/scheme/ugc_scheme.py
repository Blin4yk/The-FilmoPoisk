from datetime import datetime

from pydantic import BaseModel, Field


class BookmarkIn(BaseModel):
    film_id: str = Field(...)
    note: str = Field(...)


class BookmarkOut(BookmarkIn):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class LikeIn(BaseModel):
    film_id: str = Field(...)
    value: int = Field(..., ge=-1, le=1, description="-1 дизлайк, 1 лайк")


class LikeOut(LikeIn):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class ReviewIn(BaseModel):
    film_id: str = Field(...)
    title: str = Field(..., min_length=3, max_length=100)
    text: str = Field(..., min_length=10, max_length=5000)
    rating: int = Field(..., ge=1, le=10)


class ReviewUpdate(BaseModel):
    title: str | None = Field(None, min_length=3, max_length=100)
    text: str | None = Field(None, min_length=3, max_length=5000)
    rating: int | None = Field(None, ge=1, le=10)


class ReviewOut(ReviewIn):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class RatingIn(BaseModel):
    film_id: str = Field(...)
    value: int = Field(..., ge=1, le=10, description='Оценка фильма от 1 до 10')


class RatingOut(RatingIn):
    id: str
    user_id: str
    created_at: datetime
    updated_at: datetime


class FilmFeedbackOut(BaseModel):
    film_id: str
    ratings_count: int
    average_rating: float | None
    reviews_count: int
    reviews: list[ReviewOut]


class DeleteResponse(BaseModel):
    status: str = 'ok'
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
