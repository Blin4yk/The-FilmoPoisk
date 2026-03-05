from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from uuid import uuid4

from api.v1.scheme.notification_scheme import (
    BroadcastNotificationCreate,
    NotificationChannel,
    PersonalizedNotificationItem,
    PersonalizedNotificationsCreate,
)
from services.notification import NotificationService
from workers.notification_worker import (
    EmailNotificationSender,
    NotificationWorker,
    Recipient,
    SenderFactory,
)


class DummyKafkaProducer:
    """Заглушка Kafka-продьюсера для тестирования публикации."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def send_and_wait(self, topic: str, key: bytes | None, value: bytes) -> None:
        self.calls.append({'topic': topic, 'key': key, 'value': value})


class FakePublisher:
    """Фейковый паблишер для проверки постановки сообщений в очередь."""

    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def publish(self, topic: str, key: str | None, value: bytes) -> None:
        self.messages.append({'topic': topic, 'key': key, 'value': value})


class FakeCursor:
    """Фейковый курсор MongoDB для тестов."""

    def __init__(self, data):
        self._data = data

    def sort(self, *_args, **_kwargs):
        return self

    def limit(self, _limit: int):
        return self

    def __aiter__(self):
        self._iter = iter(self._data)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class FakeNotificationsCollection:
    """Фейковая коллекция нотификаций."""

    def __init__(self):
        self.inserted: list[dict] = []

    async def insert_one(self, doc: dict) -> None:
        self.inserted.append(doc)

    def find(self, _query: dict):
        return FakeCursor([])


class FakeSender:
    """Фейковый отправитель уведомлений."""

    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send(self, recipient: Recipient, subject: str, text: str) -> None:
        self.sent.append({'recipient': recipient, 'subject': subject, 'text': text})


class FakeSenderFactory(SenderFactory):
    """Фабрика отправителей, возвращающая один фейковый sender."""

    def __init__(self, sender: FakeSender) -> None:
        self._sender = sender

    def get(self, channel: str) -> FakeSender:
        return self._sender


class FakeAuthClient:
    """Фейковый клиент авторизации."""

    def __init__(self, users: list[Recipient]) -> None:
        self._users = users

    async def get_user(self, user_id: str) -> Recipient:
        for user in self._users:
            if user.user_id == user_id:
                return user
        raise ValueError('Пользователь не найден')

    async def list_users(self, page_size: int = 100) -> list[Recipient]:
        return self._users


def test_enqueue_personalized_notifications() -> None:
    async def _run() -> None:
        publisher = FakePublisher()
        mongo_db = SimpleNamespace(notifications=FakeNotificationsCollection())
        service = NotificationService(publisher=publisher, mongo_db=mongo_db)

        user_id = uuid4()
        payload = PersonalizedNotificationsCreate(
            items=[
                PersonalizedNotificationItem(
                    user_id=user_id,
                    template_id='welcome',
                    subject='Добро пожаловать',
                    channel=NotificationChannel.EMAIL,
                    payload={'coupon': 'NEW10'},
                )
            ]
        )

        accepted = await service.enqueue_personalized(payload)

        assert accepted == 1
        assert len(publisher.messages) == 1
        body = json.loads(publisher.messages[0]['value'])
        assert body['user_id'] == str(user_id)
        assert body['template_id'] == 'welcome'

    asyncio.run(_run())


def test_enqueue_broadcast_notifications() -> None:
    async def _run() -> None:
        publisher = FakePublisher()
        mongo_db = SimpleNamespace(notifications=FakeNotificationsCollection())
        service = NotificationService(publisher=publisher, mongo_db=mongo_db)

        payload = BroadcastNotificationCreate(
            template_id='new_movie',
            subject='Новый фильм уже доступен',
            channel=NotificationChannel.PUSH,
            payload={'film_name': 'Interstellar'},
        )

        accepted = await service.enqueue_broadcast(payload)

        assert accepted == 1
        assert publisher.messages[0]['key'] == 'broadcast'

    asyncio.run(_run())


def test_worker_renders_template() -> None:
    worker = NotificationWorker(
        consumer=SimpleNamespace(),
        producer=SimpleNamespace(),
        mongo_db=SimpleNamespace(notifications=FakeNotificationsCollection()),
        auth_service_url='http://auth',
    )

    message = {'first_name': 'Иван', 'last_name': 'Иванов'}

    assert worker._render_message('Здравствуйте, {first_name} {last_name}!', message) == 'Здравствуйте, Иван Иванов!'


def test_get_notification_publisher_returns_actual_runtime_producer() -> None:
    async def _run() -> None:
        from db import kafka
        from db.notification_queue import get_notification_publisher

        original_producer = kafka.kafka_producer
        test_producer = DummyKafkaProducer()
        kafka.kafka_producer = test_producer
        try:
            publisher = await get_notification_publisher()
            await publisher.publish('notifications', key='user-1', value=b'payload')
            assert test_producer.calls[0]['topic'] == 'notifications'
            assert test_producer.calls[0]['key'] == b'user-1'
        finally:
            kafka.kafka_producer = original_producer

    asyncio.run(_run())


def test_get_notification_publisher_raises_when_not_initialized() -> None:
    async def _run() -> None:
        from db import kafka
        from db.notification_queue import get_notification_publisher

        original_producer = kafka.kafka_producer
        kafka.kafka_producer = None
        try:
            try:
                await get_notification_publisher()
                raise AssertionError('Ожидалась ошибка при неинициализированном продьюсере')
            except RuntimeError as exc:
                assert str(exc) == 'Kafka producer не инициализирован'
        finally:
            kafka.kafka_producer = original_producer

    asyncio.run(_run())


def test_worker_processes_broadcast_and_saves_notifications() -> None:
    async def _run() -> None:
        notifications = FakeNotificationsCollection()
        sender = FakeSender()
        users = [
            Recipient('u1', 'ivan', 'ivan@example.com', 'Иван', 'Иванов'),
            Recipient('u2', 'olga', 'olga@example.com', 'Ольга', 'Петрова'),
        ]
        worker = NotificationWorker(
            consumer=SimpleNamespace(),
            producer=SimpleNamespace(),
            mongo_db=SimpleNamespace(notifications=notifications),
            auth_service_url='http://auth',
            sender_factory=FakeSenderFactory(sender),
            auth_client=FakeAuthClient(users),
        )

        await worker._process_message(
            {
                'user_id': None,
                'subject': 'Новости сервиса',
                'channel': 'email',
                'text': 'Здравствуйте, {first_name}!',
                'payload': {},
            }
        )

        assert len(sender.sent) == 2
        assert len(notifications.inserted) == 2
        assert notifications.inserted[0]['user_id'] == 'u1'
        assert notifications.inserted[1]['user_id'] == 'u2'

    asyncio.run(_run())


def test_email_sender_uses_smtplib_transport() -> None:
    async def _run() -> None:
        sender = EmailNotificationSender()
        recipient = Recipient('u1', 'ivan', 'ivan@example.com', 'Иван', 'Иванов')

        calls: list[str] = []

        def fake_send_sync(_message) -> None:
            calls.append('called')

        sender._send_sync = fake_send_sync  # type: ignore[method-assign]
        await sender.send(recipient=recipient, subject='Тема', text='Текст')

        assert calls == ['called']

    asyncio.run(_run())
