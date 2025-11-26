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

    @property
    def base_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


settings = Settings()
