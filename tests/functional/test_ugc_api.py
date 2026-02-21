import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

fake_motor = types.ModuleType('motor')
fake_motor_asyncio = types.ModuleType('motor.motor_asyncio')
fake_motor_asyncio.AsyncIOMotorDatabase = object
fake_motor_asyncio.AsyncIOMotorClient = object
sys.modules['motor'] = fake_motor
sys.modules['motor.motor_asyncio'] = fake_motor_asyncio

from api.v1.dependencies.auth import get_current_user
from api.v1.ugc import get_ugc_service, router


class FakeService:
    def __init__(self):
        self.upsert_bookmark = AsyncMock(return_value={
            'id': 'b1',
            'user_id': 'u1',
            'film_id': 'f1',
            'note': 'watch later',
            'created_at': '2026-01-01T00:00:00Z',
            'updated_at': '2026-01-01T00:00:00Z',
        })
        self.list_bookmarks = AsyncMock(return_value=[])
        self.delete_bookmark = AsyncMock(return_value=None)
        self.upsert_like = AsyncMock(return_value={
            'id': 'l1',
            'user_id': 'u1',
            'film_id': 'f1',
            'value': 1,
            'created_at': '2026-01-01T00:00:00Z',
            'updated_at': '2026-01-01T00:00:00Z',
        })
        self.delete_like = AsyncMock(return_value=None)
        self.create_review = AsyncMock(return_value={
            'id': 'r1',
            'user_id': 'u1',
            'film_id': 'f1',
            'title': 'Great',
            'text': 'Excellent film!',
            'rating': 9,
            'created_at': '2026-01-01T00:00:00Z',
            'updated_at': '2026-01-01T00:00:00Z',
        })
        self.update_review = AsyncMock(return_value={
            'id': 'r1',
            'user_id': 'u1',
            'film_id': 'f1',
            'title': 'Great',
            'text': 'Updated excellent film!',
            'rating': 10,
            'created_at': '2026-01-01T00:00:00Z',
            'updated_at': '2026-01-02T00:00:00Z',
        })
        self.delete_review = AsyncMock(return_value=None)
        self.list_reviews = AsyncMock(return_value=[])


def build_client(service: FakeService) -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id='u1')
    app.dependency_overrides[get_ugc_service] = lambda: service
    return TestClient(app)


def test_upsert_bookmark_endpoint():
    service = FakeService()
    client = build_client(service)

    response = client.put('/api/v1/ugc/bookmarks', json={'film_id': 'f1', 'note': 'watch later'})

    assert response.status_code == 200
    body = response.json()
    assert body['film_id'] == 'f1'
    assert body['user_id'] == 'u1'


def test_create_review_endpoint():
    service = FakeService()
    client = build_client(service)

    response = client.post(
        '/api/v1/ugc/reviews',
        json={'film_id': 'f1', 'title': 'Great', 'text': 'Excellent film!', 'rating': 9},
    )

    assert response.status_code == 201
    assert response.json()['id'] == 'r1'


def test_delete_like_endpoint():
    service = FakeService()
    client = build_client(service)

    response = client.delete('/api/v1/ugc/likes/f1')

    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
