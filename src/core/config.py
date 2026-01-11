import os
from logging import config as logging_config

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.logger import LOGGING

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
    postgres_db: str = Field('auth_db', alias='POSTGRES_DB')
    postgres_user: str = Field('auth_user', alias='POSTGRES_USER')
    postgres_password: str = Field('auth_password', alias='POSTGRES_PASSWORD')

    @property
    def postgres_url(self) -> str:
        """Вернуть URL базы данных PostgreSQL."""
        return f'postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}'

    jwt_secret_key: str = Field('your-secret-key-change-in-production', alias='JWT_SECRET_KEY')
    jwt_algorithm: str = Field('HS256', alias='JWT_ALGORITHM')
    access_token_expire_minutes: int = Field(15, alias='ACCESS_TOKEN_EXPIRE_MINUTES')
    refresh_token_expire_days: int = Field(7, alias='REFRESH_TOKEN_EXPIRE_DAYS')

    @property
    def base_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


settings = Settings()
