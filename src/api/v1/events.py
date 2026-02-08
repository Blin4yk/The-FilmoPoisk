from http import HTTPStatus

from fastapi import APIRouter, Depends, Request

from api.v1.scheme.event_scheme import EventsBatch, UserEvent
from services.analytics import AnalyticsService, get_analytics_service

router = APIRouter(prefix='/api/v1/events', tags=['events'])


@router.post('/', status_code=HTTPStatus.ACCEPTED, response_model=None)
async def collect_events(
    payload: EventsBatch,
    request: Request,
    analytics_service: AnalyticsService = Depends(get_analytics_service),
) -> dict[str, any]:
    """Собрать пользовательские события и отправить их в Kafka.

    Эндпоинт принимает пакет событий от фронтенда и обогащает их базовой
    информацией (IP, User-Agent), после чего отправляет в шину.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get('User-Agent')

    enriched_events: list[UserEvent] = []
    for event in payload.events:
        event.ip_address = event.ip_address or client_ip
        event.user_agent = event.user_agent or user_agent
        enriched_events.append(event)

    await analytics_service.send_events(enriched_events)

    return {'status': 'accepted', 'count': len(enriched_events)}



