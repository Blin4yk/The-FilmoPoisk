"""Воркер обработки очереди нотификаций."""

import asyncio
import json
import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from typing import Any, Protocol

import httpx
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError
from motor.motor_asyncio import AsyncIOMotorDatabase

from core.config import kafka_settings, notification_settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Recipient:
    """Данные получателя уведомления."""

    user_id: str
    username: str
    email: str | None
    first_name: str | None
    last_name: str | None


class NotificationSender(Protocol):
    """Протокол отправителя уведомлений."""

    async def send(self, recipient: Recipient, subject: str, text: str) -> None:
        """Отправить уведомление получателю."""


class LogNotificationSender:
    """Базовый отправитель, который пишет отправку в лог."""

    def __init__(self, channel: str) -> None:
        self._channel = channel

    async def send(self, recipient: Recipient, subject: str, text: str) -> None:
        """Смоделировать отправку уведомления в конкретный канал."""
        logger.info(
            'Уведомление отправлено в канал %s: user_id=%s, email=%s, subject=%s, text=%s',
            self._channel,
            recipient.user_id,
            recipient.email,
            subject,
            text,
        )


class EmailNotificationSender:
    """Отправитель email-уведомлений через smtplib."""

    async def send(self, recipient: Recipient, subject: str, text: str) -> None:
        """Отправить email-уведомление пользователю."""
        if not recipient.email:
            raise ValueError(f'У пользователя {recipient.user_id} отсутствует email')

        message = EmailMessage()
        message['From'] = notification_settings.smtp_from_email
        message['To'] = recipient.email
        message['Subject'] = subject
        message.set_content(text)

        await asyncio.to_thread(self._send_sync, message)

    def _send_sync(self, message: EmailMessage) -> None:
        """Синхронная отправка email через SMTP."""
        with smtplib.SMTP(notification_settings.smtp_host, notification_settings.smtp_port, timeout=10) as smtp:
            if notification_settings.smtp_use_tls:
                smtp.starttls()
            if notification_settings.smtp_username:
                smtp.login(notification_settings.smtp_username, notification_settings.smtp_password or '')
            smtp.send_message(message)


class SenderFactory:
    """Фабрика отправителей по каналу доставки."""

    def __init__(self) -> None:
        email_sender: NotificationSender
        if notification_settings.enable_smtp_notifications:
            email_sender = EmailNotificationSender()
        else:
            email_sender = LogNotificationSender('email')

        self._senders: dict[str, NotificationSender] = {
            'email': email_sender,
            'sms': LogNotificationSender('sms'),
            'push': LogNotificationSender('push'),
        }

    def get(self, channel: str) -> NotificationSender:
        """Вернуть отправитель для канала или бросить ошибку."""
        sender = self._senders.get(channel)
        if sender is None:
            raise ValueError(f'Неизвестный канал доставки: {channel}')
        return sender


class AuthUserClient:
    """Клиент сервиса авторизации для получения получателей уведомлений."""

    def __init__(self, auth_service_url: str) -> None:
        self._auth_service_url = auth_service_url.rstrip('/')

    async def get_user(self, user_id: str) -> Recipient:
        """Запросить одного пользователя по идентификатору."""
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f'{self._auth_service_url}/api/v1/auth/users/{user_id}')
            response.raise_for_status()
            data = response.json()
        return Recipient(
            user_id=str(data['id']),
            username=data.get('username', ''),
            email=data.get('email'),
            first_name=data.get('first_name'),
            last_name=data.get('last_name'),
        )

    async def list_users(self, page_size: int = 100) -> list[Recipient]:
        """Запросить всех пользователей порциями для широковещательных уведомлений."""
        users: list[Recipient] = []
        page = 1
        async with httpx.AsyncClient(timeout=10.0) as client:
            while True:
                response = await client.get(
                    f'{self._auth_service_url}/api/v1/auth/users',
                    params={'page': page, 'size': page_size},
                )
                response.raise_for_status()
                payload = response.json()
                items = payload.get('items', payload)
                if not items:
                    break
                for data in items:
                    users.append(
                        Recipient(
                            user_id=str(data['id']),
                            username=data.get('username', ''),
                            email=data.get('email'),
                            first_name=data.get('first_name'),
                            last_name=data.get('last_name'),
                        )
                    )
                if len(items) < page_size:
                    break
                page += 1
        return users


class NotificationWorker:
    """Воркер, формирующий персонализированные уведомления и сохраняющий результат."""

    def __init__(
            self,
            consumer: AIOKafkaConsumer,
            producer: AIOKafkaProducer,
            mongo_db: AsyncIOMotorDatabase,
            auth_service_url: str,
            sender_factory: SenderFactory | None = None,
            auth_client: AuthUserClient | None = None,
    ) -> None:
        self._consumer = consumer
        self._producer = producer
        self._mongo_db = mongo_db
        self._sender_factory = sender_factory or SenderFactory()
        self._auth_client = auth_client or AuthUserClient(auth_service_url)

    async def run_forever(self) -> None:
        """Запустить постоянную обработку сообщений."""
        await self._consumer.start()
        try:
            async for message in self._consumer:
                try:
                    payload = json.loads(message.value.decode('utf-8'))
                    await self._process_message(payload)
                except Exception as exc:  # noqa: BLE001
                    logger.exception('Ошибка обработки уведомления: %s', exc)
                    await self._send_to_dead_letter(message.value)
        finally:
            await self._consumer.stop()

    async def _process_message(self, payload: dict[str, Any]) -> None:
        """Обработать одно сообщение очереди."""
        recipients = await self._resolve_recipients(payload)
        sender = self._sender_factory.get(payload['channel'])

        for recipient in recipients:
            context = payload.get('payload', {}).copy()
            context.update(
                {
                    'first_name': recipient.first_name or recipient.username,
                    'last_name': recipient.last_name or '',
                    'email': recipient.email or '',
                    'username': recipient.username,
                }
            )
            rendered_text = self._render_message(payload.get('text'), context)
            await sender.send(recipient=recipient, subject=payload['subject'], text=rendered_text)
            await self._save_notification(
                user_id=recipient.user_id,
                subject=payload['subject'],
                text=rendered_text,
                channel=payload['channel'],
            )

    async def _resolve_recipients(self, payload: dict[str, Any]) -> list[Recipient]:
        """Определить список получателей для уведомления."""
        user_id = payload.get('user_id')
        if user_id:
            return [await self._auth_client.get_user(user_id)]

        users = await self._auth_client.list_users()
        if not users:
            logger.warning('Широковещательное уведомление пропущено: нет получателей')
        return users

    async def _save_notification(self, user_id: str, subject: str, text: str, channel: str) -> None:
        """Сохранить отправленное уведомление для отображения в личном кабинете."""
        await self._mongo_db.notifications.insert_one(
            {
                'user_id': user_id,
                'subject': subject,
                'text': text,
                'channel': channel,
                'status': 'delivered',
                'created_at': datetime.now(timezone.utc),
            }
        )

    async def _send_to_dead_letter(self, value: bytes) -> None:
        """Отправить сообщение в dead-letter топик при ошибке обработки."""
        try:
            await self._producer.send_and_wait(kafka_settings.kafka_notifications_dlt_topic, value=value)
        except KafkaError:
            logger.exception('Не удалось отправить сообщение в dead-letter топик')

    def _render_message(self, template_text: str | None, context: dict[str, Any]) -> str:
        """Сформировать текст уведомления из шаблона и пользовательских данных."""
        template = template_text or '{first_name}, для вас новое уведомление.'
        return template.format(**context)
