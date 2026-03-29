from json import dumps
from sys import platform

from my_modules.postgres import PostgresSecret
from my_modules.wsl import get_wsl_ip
from pydantic import BaseModel

from prefect_k3s.vars import PREFECT_DATABASE, PREFECT_PORT, PREFECT_SVC


class PrefectConfig(BaseModel):
    PREFECT_API_URL: str = f"http://{PREFECT_SVC}:{PREFECT_PORT}/api"
    PREFECT_API_DATABASE_CONNECTION_URL: str = PostgresSecret.get_connection_string(
        PREFECT_DATABASE, local=False, engine="asyncpg"
    )
    PREFECT_SERVER_ANALYTICS_ENABLED: bool = False
    PREFECT_TELEMETRY_ENABLE_RESOURCE_METRICS: bool = False
    PREFECT_CLOUD_ENABLE_ORCHESTRATION_TELEMETRY: bool = False
    PREFECT_CLOUD_API_URL: None = None
    PREFECT_CLOUD_UI_URL: None = None
    PREFECT_SERVER_UI_SHOW_PROMOTIONAL_CONTENT: bool = False

    @classmethod
    def docker_env(cls) -> list[str]:
        return [
            f"ENV {key}={dumps(value)}"
            for key, value in cls().model_dump(mode="json").items()
        ]

    @staticmethod
    def PREFECT_API_URL_LOCAL() -> str:
        return f"http://{get_wsl_ip() if platform == 'win32' else PREFECT_SVC}:{PREFECT_PORT}/api"
