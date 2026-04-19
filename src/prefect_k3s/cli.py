__all__ = ["prefect_k3s"]

from importlib.metadata import version
from pathlib import Path
from subprocess import run
from sys import version_info
from time import sleep

import httpx
from my_modules.datetime_utils import now
from my_modules.git import Git
from my_modules.logger import get_logger
from my_modules.postgres import Postgres, PostgresSecret
from sqlalchemy import text
from typer import Option, Typer

from prefect_k3s.config import PrefectConfig
from prefect_k3s.vars import PREFECT_DATABASE, PREFECT_IMAGE

prefect_k3s = Typer(
    name="prefect_k3s",
    help="Prefect K3S Command-line utility.",
    no_args_is_help=True,
    add_completion=False,
)

log = get_logger(__name__)


@prefect_k3s.command(
    name="init", help="Initialize required setup before start including db creation."
)
def init(
    drop: bool = Option(
        False, "-d", "--drop", help="Drop any existing Prefect database and metadata."
    ),
):
    db = Postgres(PREFECT_DATABASE)
    if drop and db.exists:
        log.info(
            f"{PREFECT_DATABASE.capitalize()} database exists: [bold red]Dropping[/]..."
        )
        db.drop_db()
    if db.exists:
        log.info(
            f"[bold blue]{PREFECT_DATABASE}[/] PostgreSQL database already exists."
        )
    else:
        log.info(
            f"Creating a PostgreSQL database [bold blue]{PREFECT_DATABASE}[/] for prefect."
        )
        with db.engine_dev.connect() as conn:
            sql = text(f"CREATE DATABASE {PREFECT_DATABASE};")
            conn.execute(sql)
        log.info("Database created successfully.")
    PrefectConfig.windows_init()


@prefect_k3s.command(
    name="build",
    help="Docker build the custom prefect-k3s image with dependencies injected.",
)
def build(prefix: str = PREFECT_IMAGE):
    started_at = now()
    python_version = f"{version_info.major}.{version_info.minor}"
    prefect_version = version("prefect")
    tag = f"{prefect_version}-python{python_version}"
    base_image = f"prefecthq/prefect:{tag}"
    custom_image = f"{prefix}:{tag}"
    sqlalchemy_conn_url = PostgresSecret.get_connection_string(local=False)

    git = Git()

    log.info(f"Current python version: {python_version}")
    log.info(f"Prefect version installed: {prefect_version}")
    log.info(f"Base Image: '{base_image}'")
    log.info(f"Building custom image with dependencies injected: '{custom_image}'")

    dockerfile = Path("Dockerfile")
    dockefile_contents = "\n".join(
        (
            f"FROM {base_image}",
            "",
            " ENV TZ=Asia/Kolkata",
            f"ENV SQLALCHEMY_CONN_URL={sqlalchemy_conn_url}",
            *PrefectConfig.docker_env(),
            f"RUN uv pip install git+{git.remote_url}@{git.current_branch}",
        )
    )
    dockerfile.write_text(dockefile_contents)
    run(["docker", "build", "--no-cache", "-t", custom_image, "."])
    log.info(f"Build complete. Time taken: {now() - started_at}")


@prefect_k3s.command(
    name="wait", help="Wait for Prefect server readiness and liveness."
)
def wait(
    timeout: int = Option(
        300, "-t", "--timeout", help="Timeout for wait (in seconds)."
    ),
):
    started_at = now()
    while (now() - started_at).total_seconds() <= timeout:
        health_endpoint = PrefectConfig.PREFECT_API_URL_LOCAL() + "/health"
        try:
            if httpx.get(health_endpoint).status_code == 200:
                log.info("Prefect server initialized and running.")
                return
            else:
                log.info("Prefect server initializing...")
                sleep(3)
        except Exception:
            log.info("Prefect server initializing...")
            sleep(3)
    raise TimeoutError("Timeout reached for server wait.")
