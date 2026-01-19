"""Pydantic схемы для API аутентификации."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    """Схема для регистрации пользователя."""

    username: str = Field(
        ..., min_length=3, max_length=50, description='Имя пользователя'
    )
    email: EmailStr = Field(..., description='Email пользователя')
    password: str = Field(..., description='Пароль (минимум 8 символов)')

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Валидировать, что username содержит только буквенно-цифровые символы, подчеркивания и дефисы."""
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError(
                'Username может содержать только буквы, цифры, подчеркивания и дефисы'
            )
        return v


class UserLogin(BaseModel):
    """Схема для входа пользователя."""

    username: str = Field(..., description='Имя пользователя')
    password: str = Field(..., description='Пароль')


class TokenResponse(BaseModel):
    """Схема ответа с токенами."""

    access_token: str = Field(..., description='JWT access токен')
    refresh_token: str | None = Field(
        None, description='JWT refresh токен (только при входе)'
    )
    token_type: str = Field(default='bearer', description='Тип токена')


class UserResponse(BaseModel):
    """Схема ответа с данными пользователя."""

    id: UUID
    username: str
    email: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    """Схема для обновления профиля пользователя."""

    username: str | None = Field(
        None, min_length=3, max_length=50, description='Новое имя пользователя'
    )
    password: str | None = Field(None, min_length=8, description='Новый пароль')

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str | None) -> str | None:
        """Валидировать username, если предоставлен."""
        if v and not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError(
                'Username может содержать только буквы, цифры, подчеркивания и дефисы'
            )
        return v


class LoginHistoryResponse(BaseModel):
    """Схема для записи истории входов."""

    id: UUID
    ip_address: str | None
    user_agent: str | None
    login_at: datetime

    class Config:
        from_attributes = True


class LoginHistoryListResponse(BaseModel):
    """Схема для истории входов с пагинацией."""

    items: list[LoginHistoryResponse]
    total: int
    page: int
    size: int
    pages: int


class MessageResponse(BaseModel):
    """Схема для простого сообщения в ответе."""

    message: str
