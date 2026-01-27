import os
from logging import config as logging_config

from core.logger import LOGGING
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Применяем настройки логирования
logging_config.dictConfig(LOGGING)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    project_name: str = Field('movies', alias='PROJECT_NAME')

    redis_host: str = Field('redis', alias='REDIS_HOST')
    redis_port: int = Field(6379, alias='REDIS_PORT')

    elastic_host: str = Field('elasticsearch-with-dump', alias='ELASTIC_HOST')
    elastic_port: int = Field(9200, alias='ELASTIC_PORT')

    postgres_host: str = Field('postgres', alias='POSTGRES_HOST')
    postgres_port: int = Field(5432, alias='POSTGRES_PORT')
    postgres_db: str = Field('db', alias='POSTGRES_DB')
    postgres_user: str = Field('user', alias='POSTGRES_USER')
    postgres_password: str = Field('password', alias='POSTGRES_PASSWORD')

    @property
    def postgres_url(self) -> str:
        """Вернуть URL базы данных PostgreSQL."""
        return f'postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}'

    jwt_secret_key: str = Field(
        'zK9kFhzwajNklEzmnoYVWma4EmyXXWtOkTyJGZ6BdgV', alias='JWT_SECRET_KEY'
    )
    jwt_algorithm: str = Field('HS256', alias='JWT_ALGORITHM')
    access_token_expire_minutes: int = Field(15, alias='ACCESS_TOKEN_EXPIRE_MINUTES')
    refresh_token_expire_days: int = Field(7, alias='REFRESH_TOKEN_EXPIRE_DAYS')

    # Auth service integration
    auth_service_url: str = Field('http://localhost:8000', alias='AUTH_SERVICE_URL')

    # Jaeger tracing
    jaeger_agent_host: str = Field('jaeger', alias='JAEGER_AGENT_HOST')
    jaeger_agent_port: int = Field(6831, alias='JAEGER_AGENT_PORT')
    jaeger_service_name: str = Field('filmp Poisk', alias='JAEGER_SERVICE_NAME')

    # Rate limiting
    rate_limit_per_minute: int = Field(60, alias='RATE_LIMIT_PER_MINUTE')
    rate_limit_per_hour: int = Field(1000, alias='RATE_LIMIT_PER_HOUR')

    # OAuth providers
    oauth_yandex_client_id: str = Field('secret_client_id', alias='OAUTH_YANDEX_CLIENT_ID')
    oauth_yandex_client_secret: str = Field('client_secret_key', alias='OAUTH_YANDEX_CLIENT_SECRET')

    oauth_redirect_uri: str = Field(
        'https://oauth.yandex.ru/verification_code', alias='OAUTH_REDIRECT_URI'
    )

    AUTHORIZATION_BASE_URL: str = Field('https://oauth.yandex.ru/authorize', alias="AUTHORIZATION_BASE_URL")
    TOKEN_URL: str = Field('https://oauth.yandex.ru/token', alias="TOKEN_URL")

    @property
    def base_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


settings = Settings()
