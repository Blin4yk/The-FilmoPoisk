from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(str):
    """Типы пользовательских событий."""

    CLICK = 'click'
    PAGE_VIEW = 'page_view'
    VIDEO_QUALITY_CHANGE = 'video_quality_change'
    VIDEO_COMPLETED = 'video_completed'
    SEARCH_FILTER_USED = 'search_filter_used'
    CUSTOM = 'custom'


class UserEvent(BaseModel):
    """Базовая схема пользовательского события.

    Модель намеренно универсальная (KISS/DRY), чтобы покрывать разные типы событий.
    """

    event_type: str = Field(..., description='Тип события')
    timestamp: datetime = Field(
        default_factory=datetime.now(), description='Время возникновения события'
    )

    user_id: UUID | None = Field(
        default=None, description='Идентификатор пользователя (если известен)'
    )
    session_id: str = Field(
        ..., description='Идентификатор сессии пользователя на клиенте'
    )

    page: str | None = Field(
        default=None,
        description='URL или логический идентификатор страницы, на которой произошло событие',
    )
    referrer: str | None = Field(
        default=None, description='Адрес страницы-источника (если есть)'
    )

    element_id: str | None = Field(
        default=None,
        description='Идентификатор элемента интерфейса (для кликов и т.п.)',
    )
    element_type: str | None = Field(
        default=None, description='Тип элемента интерфейса (кнопка, карточка и т.п.)'
    )

    video_id: UUID | None = Field(
        default=None, description='Идентификатор видео (если событие связано с видео)'
    )
    quality_from: str | None = Field(
        default=None, description='Исходное качество видео (для смены качества)'
    )
    quality_to: str | None = Field(
        default=None, description='Новое качество видео (для смены качества)'
    )

    watched_full: bool | None = Field(
        default=None,
        description='Просмотрено ли видео до конца (для события завершения просмотра)',
    )

    filter_type: str | None = Field(
        default=None,
        description='Тип применённого фильтра (жанр, рейтинг, актёр и т.п.)',
    )
    filter_value: str | None = Field(
        default=None, description='Значение применённого фильтра'
    )

    duration_ms: int | None = Field(
        default=None,
        description='Количество миллисекунд, проведённых на странице или в состоянии',
        ge=0,
    )

    user_agent: str | None = Field(
        default=None, description='User-Agent клиента (может быть проставлен на бэке)'
    )
    ip_address: str | None = Field(
        default=None, description='IP-адрес клиента (может быть проставлен на бэке)'
    )

    metadata: dict[str, Any] | None = Field(
        default=None,
        description='Дополнительные данные в произвольном формате (JSON-объект)',
    )


class EventsBatch(BaseModel):
    """Пакет пользовательских событий."""

    events: list[UserEvent] = Field(
        ..., description='Список пользовательских событий'
    )



