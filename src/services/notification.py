import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from api.v1.scheme.notification_scheme import (
    BroadcastNotificationCreate,
    FixedEventNotificationCreate,
    FreeFormNotificationCreate,
    PersonalizedNotificationsCreate,
    UserNotificationView,
)
from core.config import kafka_settings
from db.mongo import get_mongo_db
from db.notification_queue import NotificationPublisher, get_notification_publisher


@dataclass(frozen=True)
class QueuedNotification:
    """Внутренняя модель сообщения, публикуемого в очередь."""

    event_type: str
    user_id: str | None
    template_id: str
    subject: str
    channel: str
    payload: dict[str, Any]
    text: str | None = None


class NotificationService:
    """Центральный сервис нотификаций, отвечающий за постановку сообщений в очередь."""

    def __init__(
            self,
            publisher: NotificationPublisher,
            mongo_db: AsyncIOMotorDatabase,
    ) -> None:
        self._publisher = publisher
        self._mongo_db = mongo_db
        self._topic = kafka_settings.kafka_notifications_topic

    async def enqueue_broadcast(self, payload: BroadcastNotificationCreate) -> int:
        """Поставить в очередь широковещательное уведомление."""
        message = QueuedNotification(
            event_type='broadcast',
            user_id=None,
            template_id=payload.template_id,
            subject=payload.subject,
            channel=payload.channel.value,
            payload=payload.payload or {},
        )
        await self._publish(message, key='broadcast')
        return 1

    async def enqueue_personalized(self, payload: PersonalizedNotificationsCreate) -> int:
        """Поставить в очередь набор персонализированных уведомлений."""
        for item in payload.items:
            message = QueuedNotification(
                event_type='personalized',
                user_id=str(item.user_id),
                template_id=item.template_id,
                subject=item.subject,
                channel=item.channel.value,
                payload=item.payload or {},
            )
            await self._publish(message, key=str(item.user_id))
        return len(payload.items)

    async def enqueue_fixed_event(self, payload: FixedEventNotificationCreate) -> int:
        """Поставить в очередь фиксированное событие предметной области."""
        user_ids = payload.user_ids or [None]
        for user_id in user_ids:
            message = QueuedNotification(
                event_type=payload.event_type.value,
                user_id=str(user_id) if user_id else None,
                template_id=payload.event_type.value,
                subject='Событие кинотеатра',
                channel='push',
                payload=payload.payload or {},
            )
            await self._publish(message, key=str(user_id) if user_id else payload.event_type.value)
        return len(user_ids)

    async def enqueue_free_form(self, payload: FreeFormNotificationCreate) -> int:
        """Поставить в очередь событие в свободном формате."""
        message = QueuedNotification(
            event_type='free_form',
            user_id=str(payload.user_id),
            template_id=payload.template_id,
            subject=payload.subject,
            channel=payload.channel.value,
            payload=payload.payload or {},
            text=payload.text,
        )
        await self._publish(message, key=str(payload.user_id))
        return 1

    async def get_user_notifications(self, user_id: UUID, limit: int = 20) -> list[UserNotificationView]:
        """Вернуть последние уведомления пользователя из MongoDB."""
        cursor = (
            self._mongo_db.notifications.find({'user_id': str(user_id)})
            .sort('created_at', -1)
            .limit(limit)
        )

        result: list[UserNotificationView] = []
        async for item in cursor:
            result.append(
                UserNotificationView(
                    id=str(item['_id']),
                    user_id=UUID(item['user_id']),
                    channel=item['channel'],
                    subject=item['subject'],
                    text=item['text'],
                    status=item['status'],
                    created_at=item['created_at'],
                )
            )
        return result

    async def _publish(self, message: QueuedNotification, key: str | None) -> None:
        """Сериализовать сообщение и отправить его в шину."""
        body = {
            'event_type': message.event_type,
            'user_id': message.user_id,
            'template_id': message.template_id,
            'subject': message.subject,
            'channel': message.channel,
            'payload': message.payload,
            'text': message.text,
            'created_at': datetime.now(timezone.utc).isoformat(),
        }
        await self._publisher.publish(self._topic, key=key, value=json.dumps(body).encode('utf-8'))


async def get_notification_service(
        publisher: NotificationPublisher = Depends(get_notification_publisher),  # noqa: B008
        mongo_db: AsyncIOMotorDatabase = Depends(get_mongo_db),  # noqa: B008
) -> NotificationService:
    """Фабрика зависимости для NotificationService."""
    return NotificationService(publisher=publisher, mongo_db=mongo_db)
