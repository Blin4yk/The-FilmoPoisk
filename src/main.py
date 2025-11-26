import contextlib
from collections.abc import AsyncIterator

import uvicorn
from elasticsearch import AsyncElasticsearch
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from redis.asyncio import Redis

from core.config import settings
from api.v1 import films
from db import elastic, redis


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    redis.redis = Redis(host=settings.redis_host, port=settings.redis_port)
    elastic.es = AsyncElasticsearch(
        hosts=[f'http://{settings.elastic_host}:{settings.elastic_port}'],
        headers={'Accept': 'application/vnd.elasticsearch+json; compatible-with=8'}
    )

    yield

    await redis.redis.close()
    await elastic.es.close()


app = FastAPI(
    title=settings.project_name,
    docs_url='/api/openapi',
    openapi_url='/api/openapi.json',
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.include_router(films.router, prefix='/api/v1/films', tags=['films'])

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)