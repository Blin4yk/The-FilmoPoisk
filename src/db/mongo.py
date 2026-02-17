from collections.abc import AsyncIterator

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from core.config import mongo_sentry_settings

mongo_client: AsyncIOMotorClient | None = None
mongo_db: AsyncIOMotorDatabase | None = None

async def init_mongo() -> AsyncIOMotorDatabase:
    global mongo_client, mongo_db
    mongo_client = AsyncIOMotorClient(mongo_sentry_settings.mongo_url)
    mongo_db = mongo_client[mongo_sentry_settings.mongo_db]

    await mongo_db.bookmarks.create_index([('user_id', 1), ('film_id', 1)], unique=True)
    await mongo_db.likes.create_index([('user_id', 1), ('film_id', 1)], unique=True)
    await mongo_db.reviews.create_index([('film_id', 1), ('created_at', -1)])
    await mongo_db.reviews.create_index([('user_id', 1), ('film_id', 1)], unique=True)
    return mongo_db

async def close_mongo() -> None:
    global mongo_client
    if mongo_client is not None:
        mongo_client.close()


async def get_mongo_db() -> AsyncIterator[AsyncIOMotorDatabase]:
    if mongo_db is None:
        raise RuntimeError
    yield mongo_db
