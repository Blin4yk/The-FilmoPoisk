from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationChannel(str, Enum):
    """Доступные каналы доставки уведомлений."""

    EMAIL = 'email'
    SMS = 'sms'
    PUSH = 'push'


class FixedEventType(str, Enum):
    """Фиксированные доменные события кинотеатра."""

    USER_REGISTERED = 'user_registered'
    NEW_FILM_AVAILABLE = 'new_film_available'
    SUBSCRIPTION_EXPIRING = 'subscription_expiring'


class BroadcastNotificationCreate(BaseModel):
    """Запрос на отправку одинакового сообщения всем пользователям."""

    template_id: str = Field(..., description='Идентификатор шаблона')
    subject: str = Field(..., description='Тема уведомления')
    channel: NotificationChannel = Field(..., description='Канал доставки')
    payload: dict[str, Any] | None = Field(
        default=None,
        description='Дополнительные параметры шаблона',
    )


class PersonalizedNotificationItem(BaseModel):
    """Элемент персонализированной рассылки для одного пользователя."""

    user_id: UUID = Field(..., description='Идентификатор пользователя')
    template_id: str = Field(..., description='Идентификатор шаблона')
    subject: str = Field(..., description='Тема уведомления')
    channel: NotificationChannel = Field(..., description='Канал доставки')
    payload: dict[str, Any] | None = Field(
        default=None,
        description='Дополнительные параметры шаблона',
    )


class PersonalizedNotificationsCreate(BaseModel):
    """Пакет персонализированных уведомлений."""

    items: list[PersonalizedNotificationItem] = Field(
        ..., min_length=1, description='Список уведомлений для постановки в очередь'
    )


class FixedEventNotificationCreate(BaseModel):
    """Запрос на постановку в очередь фиксированного события."""

    event_type: FixedEventType = Field(..., description='Тип события')
    user_ids: list[UUID] | None = Field(
        default=None,
        description='Список пользователей. Если пусто, событие трактуется как широковещательное',
    )
    payload: dict[str, Any] | None = Field(
        default=None,
        description='Полезная нагрузка события',
    )


class FreeFormNotificationCreate(BaseModel):
    """Свободный формат события для интеграций с внешними сервисами."""

    user_id: UUID
    template_id: str
    subject: str
    text: str | None = None
    channel: NotificationChannel
    payload: dict[str, Any] | None = None


class NotificationEnqueueResponse(BaseModel):
    """Ответ API после постановки уведомлений в очередь."""

    accepted: int = Field(..., description='Количество принятых сообщений')
    queue_topic: str = Field(..., description='Топик/очередь, куда отправлены сообщения')


class UserNotificationView(BaseModel):
    """Уведомление для отображения в личном кабинете пользователя."""

    id: str = Field(..., description='Идентификатор уведомления')
    user_id: UUID = Field(..., description='Идентификатор пользователя')
    channel: NotificationChannel = Field(..., description='Канал доставки')
    subject: str = Field(..., description='Тема уведомления')
    text: str = Field(..., description='Сформированный текст уведомления')
    status: str = Field(..., description='Статус отправки')
    created_at: datetime = Field(..., description='Дата создания')
