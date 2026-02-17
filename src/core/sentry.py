import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from core.config import mongo_sentry_settings


def setup_sentry() -> None:
    if not mongo_sentry_settings.sentry_dsn:
        return

    sentry_sdk.init(
        dsn=mongo_sentry_settings.sentry_dsn,
        environment=mongo_sentry_settings.sentry_environment,
        traces_sample_rate=mongo_sentry_settings.sentry_traces_sample_rate,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
    )
