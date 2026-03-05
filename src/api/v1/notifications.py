from http import HTTPStatus

from fastapi import APIRouter, Depends, Query

from api.v1.dependencies.auth import get_current_superuser, get_current_user
from api.v1.scheme.notification_scheme import (
    BroadcastNotificationCreate,
    FixedEventNotificationCreate,
    FreeFormNotificationCreate,
    NotificationEnqueueResponse,
    PersonalizedNotificationsCreate,
    UserNotificationView,
)
from models.user import User
from services.notification import NotificationService, get_notification_service

router = APIRouter(prefix='/api/v1/notifications', tags=['notifications'])


@router.post('/broadcast', status_code=HTTPStatus.ACCEPTED, response_model=NotificationEnqueueResponse)
async def create_broadcast_notification(
    payload: BroadcastNotificationCreate,
    _: User = Depends(get_current_superuser),  # noqa: B008
    notification_service: NotificationService = Depends(get_notification_service),  # noqa: B008
) -> NotificationEnqueueResponse:
    """Принять заявку на широковещательное уведомление и передать её в очередь."""
    accepted = await notification_service.enqueue_broadcast(payload)
    return NotificationEnqueueResponse(
        accepted=accepted,
        queue_topic='notifications',
    )


@router.post('/personalized', status_code=HTTPStatus.ACCEPTED, response_model=NotificationEnqueueResponse)
async def create_personalized_notifications(
    payload: PersonalizedNotificationsCreate,
    _: User = Depends(get_current_superuser),  # noqa: B008
    notification_service: NotificationService = Depends(get_notification_service),  # noqa: B008
) -> NotificationEnqueueResponse:
    """Принять пакет персонализированных уведомлений и передать его в очередь."""
    accepted = await notification_service.enqueue_personalized(payload)
    return NotificationEnqueueResponse(accepted=accepted, queue_topic='notifications')


@router.post('/events/fixed', status_code=HTTPStatus.ACCEPTED, response_model=NotificationEnqueueResponse)
async def create_fixed_event_notification(
    payload: FixedEventNotificationCreate,
    _: User = Depends(get_current_superuser),  # noqa: B008
    notification_service: NotificationService = Depends(get_notification_service),  # noqa: B008
) -> NotificationEnqueueResponse:
    """Принять фиксированное событие от внешних сервисов и поставить в очередь."""
    accepted = await notification_service.enqueue_fixed_event(payload)
    return NotificationEnqueueResponse(accepted=accepted, queue_topic='notifications')


@router.post('/events/free-form', status_code=HTTPStatus.ACCEPTED, response_model=NotificationEnqueueResponse)
async def create_free_form_notification(
    payload: FreeFormNotificationCreate,
    _: User = Depends(get_current_superuser),  # noqa: B008
    notification_service: NotificationService = Depends(get_notification_service),  # noqa: B008
) -> NotificationEnqueueResponse:
    """Принять событие в свободном формате и поставить его в очередь."""
    accepted = await notification_service.enqueue_free_form(payload)
    return NotificationEnqueueResponse(accepted=accepted, queue_topic='notifications')


@router.get('/me', status_code=HTTPStatus.OK, response_model=list[UserNotificationView])
async def get_my_notifications(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),  # noqa: B008
    notification_service: NotificationService = Depends(get_notification_service),  # noqa: B008
) -> list[UserNotificationView]:
    """Вернуть последние уведомления текущего пользователя."""
    return await notification_service.get_user_notifications(user_id=current_user.id, limit=limit)
