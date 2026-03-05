import json
from typing import Iterable

from fastapi import Depends

from api.v1.scheme.event_scheme import UserEvent
from db.interface.interfaces import AbstractEventPublisher
from db.kafka import get_event_publisher


class AnalyticsService:
    """Сервис для отправки пользовательских событий в шину.
    Зависит от абстракции публикации событий, а не от конкретной реализации Kafka.
    """

    def __init__(self, publisher: AbstractEventPublisher) -> None:
        self._publisher = publisher
        self._topic = 'user_events'

    async def send_events(self, events: Iterable[UserEvent]) -> None:
        """Отправить пакет событий в Kafka."""
        for event in events:
            payload = json.dumps(event.model_dump(mode='json')).encode('utf-8')
            key = event.session_id
            await self._publisher.publish(self._topic, key=key, value=payload)


async def get_analytics_service(
        publisher: AbstractEventPublisher = Depends(get_event_publisher),
) -> AnalyticsService:
    """Фабрика зависимостей для AnalyticsService."""
    return AnalyticsService(publisher)
