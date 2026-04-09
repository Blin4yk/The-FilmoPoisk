import os
from logging import config as logging_config

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.logger import LOGGING

# Применяем настройки логирования
logging_config.dictConfig(LOGGING)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', extra='ignore'
    )

    project_name: str = Field('movies', alias='PROJECT_NAME')

    redis_host: str = Field('redis', alias='REDIS_HOST')
    redis_port: int = Field(6379, alias='REDIS_PORT')

    elastic_host: str = Field('elasticsearch-with-dump', alias='ELASTIC_HOST')
    elastic_port: int = Field(9200, alias='ELASTIC_PORT')

    # Kafka (для сбора пользовательских действий)
    kafka_bootstrap_servers: str = Field(
        'kafka:9092', alias='KAFKA_BOOTSTRAP_SERVERS'
    )
    kafka_user_events_topic: str = Field(
        'user_events', alias='KAFKA_USER_EVENTS_TOPIC'
    )

    # ClickHouse (для аналитического хранения пользовательских действий)
    clickhouse_host: str = Field('clickhouse', alias='CLICKHOUSE_HOST')
    clickhouse_port: int = Field(8123, alias='CLICKHOUSE_PORT')
    clickhouse_database: str = Field('analytics', alias='CLICKHOUSE_DATABASE')
    clickhouse_user: str = Field('user', alias='CLICKHOUSE_USER')
    # Пустая строка трактуется как отсутствие пароля (для стандартного пользователя default)
    clickhouse_password: str | None = Field(
        None,
        alias='CLICKHOUSE_PASSWORD',
    )

    postgres_host: str = Field('postgres', alias='POSTGRES_HOST')
    postgres_port: int = Field(5432, alias='POSTGRES_PORT')
    postgres_db: str = Field('db', alias='POSTGRES_DB')
    postgres_user: str = Field('user', alias='POSTGRES_USER')
    postgres_password: str = Field('password', alias='POSTGRES_PASSWORD')
    postgres_echo: bool = Field(False, alias='POSTGRES_ECHO')
    @property
    def postgres_url(self) -> str:
        """Вернуть URL базы данных PostgreSQL."""
        return f'postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}'

    jwt_secret_key: str = Field(
        'jwt_secret_key', alias='JWT_SECRET_KEY'
    )
    jwt_algorithm: str = Field('HS256', alias='JWT_ALGORITHM')
    access_token_expire_minutes: int = Field(15, alias='ACCESS_TOKEN_EXPIRE_MINUTES')
    refresh_token_expire_days: int = Field(7, alias='REFRESH_TOKEN_EXPIRE_DAYS')

    # Jaeger
    jaeger_agent_host: str = Field('jaeger', alias='JAEGER_AGENT_HOST')
    jaeger_agent_port: int = Field(6831, alias='JAEGER_AGENT_PORT')
    jaeger_service_name: str = Field('filmp Poisk', alias='JAEGER_SERVICE_NAME')

    # Rate
    rate_limit_per_minute: int = Field(60, alias='RATE_LIMIT_PER_MINUTE')
    rate_limit_per_hour: int = Field(1000, alias='RATE_LIMIT_PER_HOUR')

    enable_rate_limit: bool = Field(True, alias='ENABLE_RATE_LIMIT')
    enable_tracing: bool = Field(True, alias='ENABLE_TRACING')
    enable_request_id: bool = Field(True, alias='ENABLE_REQUEST_ID')

    @property
    def base_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class OAuthSettings(BaseSettings):
    """Настройки для авторизации"""
    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', extra='ignore'
    )

    oauth_yandex_client_id: str = Field('secret_client_id', alias='OAUTH_YANDEX_CLIENT_ID')
    oauth_yandex_client_secret: str = Field('client_secret_key', alias='OAUTH_YANDEX_CLIENT_SECRET')
    oauth_redirect_uri: str = Field(
        'https://oauth.yandex.ru/verification_code', alias='OAUTH_REDIRECT_URI'
    )

    AUTHORIZATION_BASE_URL: str = Field('https://oauth.yandex.ru/authorize', alias="AUTHORIZATION_BASE_URL")
    TOKEN_URL: str = Field('https://oauth.yandex.ru/token', alias="TOKEN_URL")

    oauth_credentials: dict = {
        'yandex': {
            'id': Field('secret_client_id', alias='OAUTH_YANDEX_CLIENT_ID'),
            'secret': Field('client_secret_key', alias='OAUTH_YANDEX_CLIENT_SECRET'),
            'redirect_uri': Field('https://oauth.yandex.ru/verification_code', alias='OAUTH_REDIRECT_URI')
        }
    }

    @property
    def base_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class MongoSentrySettings(BaseSettings):
    """Настройки для MongoDB и Sentry"""

    model_config = SettingsConfigDict(
        env_file='.env', env_file_encoding='utf-8', extra='ignore'
    )
    mongo_host: str = Field('mongo', alias='MONGO_HOST')
    mongo_port: int = Field(27017, alias='MONGO_PORT')
    mongo_db: str = Field('ugc', alias='MONGO_DB')
    mongo_user: str | None = Field(None, alias='MONGO_USER')
    mongo_password: str | None = Field(None, alias='MONGO_PASSWORD')

    @property
    def mongo_url(self) -> str:
        if self.mongo_user and self.mongo_password:
            return f'mongodb://{self.mongo_user}:{self.mongo_password}@{self.mongo_host}:{self.mongo_port}/{self.mongo_db}?authSource=admin'
        return f'mongodb://{self.mongo_host}:{self.mongo_port}/{self.mongo_db}'

    sentry_dsn: str | None = Field(None, alias='SENTRY_DSN')
    sentry_environment: str = Field('development', alias='SENTRY_ENVIRONMENT')
    sentry_traces_sample_rate: float = Field(0.1, alias='SENTRY_TRACES_SAMPLE_RATE')

    @property
    def base_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

mongo_sentry_settings: MongoSentrySettings = MongoSentrySettings()
oauth_settings = OAuthSettings()
settings = Settings()
