from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class UserProfileBase(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=255)
    phone: str = Field(..., min_length=5, max_length=32)


class UserProfileCreate(UserProfileBase):
    pass


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(None, min_length=3, max_length=255)
    phone: str | None = Field(None, min_length=5, max_length=32)


class UserProfileOut(UserProfileBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserProfileWithUGC(UserProfileOut):
    bookmarks: list[dict] = Field(default_factory=list)
    liked_films: list[dict] = Field(default_factory=list)
    ratings: list[dict] = Field(default_factory=list)
    reviews: list[dict] = Field(default_factory=list)

