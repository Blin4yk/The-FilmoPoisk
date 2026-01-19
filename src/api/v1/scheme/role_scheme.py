"""Pydantic схемы для API ролей."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class RoleCreate(BaseModel):
    """Схема для создания роли."""

    name: str = Field(..., min_length=3, max_length=50, description='Название роли')
    description: str | None = Field(None, max_length=500, description='Описание роли')


class RoleUpdate(BaseModel):
    """Схема для обновления роли."""

    name: str | None = Field(
        None, min_length=3, max_length=50, description='Название роли'
    )
    description: str | None = Field(None, max_length=500, description='Описание роли')


class RoleResponse(BaseModel):
    """Схема ответа с данными роли."""

    id: UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoleListResponse(BaseModel):
    """Схема для списка ролей с пагинацией."""

    items: list[RoleResponse]
    total: int
    page: int
    size: int
    pages: int


class AssignRoleResponse(BaseModel):
    """Схема ответа на назначение роли."""

    message: str
    user_id: UUID
    role_id: UUID


class CheckPermissionRequest(BaseModel):
    """Схема запроса на проверку разрешения."""

    user_id: UUID | None = Field(
        None,
        description='ID пользователя (если не указан, используется текущий пользователь)',
    )
    required_role: str | None = Field(None, description='Требуемое название роли')
    required_permission: str | None = Field(
        None, description='Требуемое название разрешения'
    )


class CheckPermissionResponse(BaseModel):
    """Схема ответа на проверку разрешения."""

    has_permission: bool
    user_id: UUID
    roles: list[str]
