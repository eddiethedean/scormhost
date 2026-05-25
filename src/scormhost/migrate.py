from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from alembic import command

_PACKAGE_DIR = Path(__file__).resolve().parent
_ALEMBIC_DIR = _PACKAGE_DIR / "alembic"
_REPO_ROOT = _PACKAGE_DIR.parent.parent


def _alembic_config(database_url: str | None = None) -> Config:
    """Load Alembic config from the repo (dev) or the installed package."""
    ini_candidates = (
        _REPO_ROOT / "alembic.ini",
        _PACKAGE_DIR / "alembic.ini",
    )
    cfg: Config | None = None
    for ini_path in ini_candidates:
        if ini_path.is_file():
            cfg = Config(str(ini_path))
            break
    if cfg is None:
        cfg = Config()
        cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
        cfg.set_main_option("version_path_separator", "os")
    else:
        script_location = cfg.get_main_option("script_location")
        if script_location and not Path(script_location).is_absolute():
            base = Path(cfg.config_file_name).resolve().parent if cfg.config_file_name else _REPO_ROOT
            cfg.set_main_option("script_location", str((base / script_location).resolve()))
    if database_url:
        cfg.set_main_option("sqlalchemy.url", database_url)
    return cfg


def run_migrations(database_url: str | None = None) -> None:
    command.upgrade(_alembic_config(database_url), "head")
