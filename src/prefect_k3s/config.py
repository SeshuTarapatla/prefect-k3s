from json import dumps
from subprocess import DEVNULL, check_call
from sys import platform

from my_modules.logger import get_logger
from my_modules.postgres import PostgresSecret
from my_modules.wsl import get_wsl_ip
from pydantic import BaseModel

from prefect_k3s.vars import PREFECT_DATABASE, PREFECT_PORT, PREFECT_SVC

log = get_logger(__name__)


class PrefectConfig(BaseModel):
    PREFECT_API_DATABASE_CONNECTION_URL: str = PostgresSecret.get_connection_string(
        PREFECT_DATABASE, local=False, engine="asyncpg"
    )
    PREFECT_API_URL: str = f"http://{PREFECT_SVC}:{PREFECT_PORT}/api"
    PREFECT_CLOUD_API_URL: None = None
    PREFECT_CLOUD_ENABLE_ORCHESTRATION_TELEMETRY: bool = False
    PREFECT_CLOUD_UI_URL: None = None
    PREFECT_DEFAULT_WORK_POOL_NAME: str = "default-workpool"
    PREFECT_LOGGING_TO_API_WHEN_MISSING_FLOW: str = "ignore"
    PREFECT_SERVER_ANALYTICS_ENABLED: bool = False
    PREFECT_SERVER_UI_SHOW_PROMOTIONAL_CONTENT: bool = False
    PREFECT_TASKS_DEFAULT_NO_CACHE: bool = True
    PREFECT_TELEMETRY_ENABLE_RESOURCE_METRICS: bool = False

    @classmethod
    def docker_env(cls) -> list[str]:
        return [
            f"ENV {key}={dumps(value)}"
            for key, value in cls().model_dump(mode="json").items()
        ]

    @staticmethod
    def PREFECT_API_URL_LOCAL() -> str:
        return f"http://{get_wsl_ip() if platform == 'win32' else PREFECT_SVC}:{PREFECT_PORT}/api"

    @classmethod
    def windows_init(cls) -> bool:
        if platform == "win32":
            log.info("Updating prefect configuration.")
            config = cls().model_dump()
            config["PREFECT_API_URL"] = cls.PREFECT_API_URL_LOCAL()
            del config["PREFECT_API_DATABASE_CONNECTION_URL"]
            for key, value in config.items():
                config_value = f"{key}={value}"
                log.info(config_value)
                check_call(["prefect", "config", "set", config_value], stdout=DEVNULL)
            log.info("Prefect config updated.")
            return True
        else:
            return False
