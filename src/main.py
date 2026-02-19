import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator

import uvicorn
from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.v1 import auth, events, films, roles, ugc
from core.config import settings
from core.sentry import setup_sentry
from core.tracing import setup_tracing
from db import elastic, postgres, redis
from db.kafka import close_kafka_producer, init_kafka_producer
from db.mongo import init_mongo, close_mongo
from middleware.rate_limit import RateLimitMiddleware
from middleware.request_id import RequestIDMiddleware

logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    redis.redis = Redis(host=settings.redis_host, port=settings.redis_port)
    elastic.es = AsyncElasticsearch(
        hosts=[f'https://{settings.elastic_host}:{settings.elastic_port}'],
        headers={'Accept': 'application/vnd.elasticsearch+json; compatible-with=8'},
    )

    # Инициализируем Kafka продьюсер для отправки пользовательских событий
    await init_kafka_producer()

    await init_mongo()

    max_retries = 5
    retry_delay = 2
    for attempt in range(max_retries):
        try:
            async with postgres.AsyncSessionLocal() as session:
                await session.execute(text('SELECT 1'))
                await session.commit()
            logger.info('Подключение к PostgreSQL успешно установлено')
            break
        except SQLAlchemyError as e:
            if attempt < max_retries - 1:
                logger.warning(
                    f'Попытка {attempt + 1}/{max_retries}: Не удалось подключиться к PostgreSQL: {e}. Повтор через {retry_delay} сек...'
                )
                await asyncio.sleep(retry_delay)
            else:
                logger.error(
                    f'Не удалось подключиться к PostgreSQL после {max_retries} попыток: {e}. Приложение может работать некорректно.'
                )
        except Exception as e:
            logger.error(f'Неожиданная ошибка при подключении к PostgreSQL: {e}')
            break

    yield

    await redis.redis.close()
    await elastic.es.close()
    await postgres.engine.dispose()
    await close_mongo()
    await close_kafka_producer()

setup_sentry()
app = FastAPI(
    title=settings.project_name,
    docs_url='/api/openapi',
    openapi_url='/api/openapi.json',
    default_response_class=ORJSONResponse,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=['*'],
    allow_headers=['*'],
    lifespan=lifespan,
    swagger_ui_parameters={
        'persistAuthorization': True,
        'docExpansion': 'none',
    },
)

if settings.enable_request_id:
    app.add_middleware(RequestIDMiddleware)

if settings.enable_rate_limit:
    app.add_middleware(RateLimitMiddleware)

# Настраиваем трассировку с условием отключения
if settings.enable_tracing:
    setup_tracing(app)

app.include_router(auth.router)
app.include_router(roles.router)
app.include_router(films.router)
app.include_router(events.router)
app.include_router(ugc.router)

# Для локальной разработки надо раскомментировать код ниже
# if __name__ == '__main__':
#     uvicorn.run("main:app", host='0.0.0.0', port=8000)
