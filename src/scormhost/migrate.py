from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


def run_migrations(database_url: str | None = None) -> None:
    root = Path(__file__).resolve().parents[2]
    cfg = Config(str(root / "alembic.ini"))
    if database_url:
        cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")
