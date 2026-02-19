from datetime import UTC, datetime

from bson import ObjectId
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument


class UGCService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    @staticmethod
    def _serialize(doc: dict) -> dict:
        doc['id'] = str(doc.pop('_id'))
        return doc

    async def upsert_bookmark(self, user_id: str, payload: dict) -> dict:
        now = datetime.now(UTC)
        result = await self.db.bookmarks.find_one_and_update(
            {'user_id': user_id, 'film_id': payload['film_id']},
            {
                '$set': {'note': payload.get('note'), 'updated_at': now},
                '$setOnInsert': {'created_at': now, 'user_id': user_id, 'film_id': payload['film_id']},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if result is None:
            result = await self.db.bookmarks.find_one({'user_id': user_id, 'film_id': payload['film_id']})
        return self._serialize(result)

    async def list_bookmarks(self, user_id: str) -> list[dict]:
        cursor = self.db.bookmarks.find({'user_id': user_id}).sort('created_at', -1)
        return [self._serialize(doc) async for doc in cursor]

    async def delete_bookmark(self, user_id: str, film_id: str) -> None:
        result = await self.db.bookmarks.delete_one({'user_id': user_id, 'film_id': film_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Bookmark not found')

    async def upsert_like(self, user_id: str, payload: dict) -> dict:
        now = datetime.now(UTC)
        await self.db.likes.update_one(
            {'user_id': user_id, 'film_id': payload['film_id']},
            {
                '$set': {'value': payload['value'], 'updated_at': now},
                '$setOnInsert': {'created_at': now, 'user_id': user_id, 'film_id': payload['film_id']},
            },
            upsert=True,
        )
        doc = await self.db.likes.find_one({'user_id': user_id, 'film_id': payload['film_id']})
        return self._serialize(doc)

    async def delete_like(self, user_id: str, film_id: str) -> None:
        result = await self.db.likes.delete_one({'user_id': user_id, 'film_id': film_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Like not found')

    async def create_review(self, user_id: str, payload: dict) -> dict:
        now = datetime.now(UTC)
        data = {**payload, 'user_id': user_id, 'created_at': now, 'updated_at': now}
        exists = await self.db.reviews.find_one({'user_id': user_id, 'film_id': payload['film_id']})
        if exists:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Review already exists for film')
        result = await self.db.reviews.insert_one(data)
        doc = await self.db.reviews.find_one({'_id': result.inserted_id})
        return self._serialize(doc)

    async def update_review(self, user_id: str, review_id: str, payload: dict) -> dict:
        if not ObjectId.is_valid(review_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid review id')
        payload['updated_at'] = datetime.now(UTC)
        doc = await self.db.reviews.find_one_and_update(
            {'_id': ObjectId(review_id), 'user_id': user_id},
            {'$set': payload},
            return_document=ReturnDocument.AFTER,
        )
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Review not found')
        return self._serialize(doc)

    async def delete_review(self, user_id: str, review_id: str) -> None:
        if not ObjectId.is_valid(review_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid review id')
        result = await self.db.reviews.delete_one({'_id': ObjectId(review_id), 'user_id': user_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Review not found')

    async def list_reviews(self, film_id: str) -> list[dict]:
        cursor = self.db.reviews.find({'film_id': film_id}).sort('created_at', -1)
        return [self._serialize(doc) async for doc in cursor]