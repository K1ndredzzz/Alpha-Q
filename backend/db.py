import os
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

_DEFAULT_DB = "/data/alpha_q_master.db"


def _build_engine() -> Engine:
    url = os.environ.get("DATABASE_URL", _DEFAULT_DB)
    if url.startswith("postgresql"):
        return create_engine(url, pool_pre_ping=True)
    sqlite_url = url if url.startswith("sqlite:///") else f"sqlite:///{url}"
    return create_engine(sqlite_url, connect_args={"check_same_thread": False})


_engine: Engine = _build_engine()


def get_db() -> Connection:
    """FastAPI dependency: yields a SQLAlchemy Connection per request."""
    with _engine.connect() as conn:
        yield conn


def probe() -> None:
    with _engine.connect() as conn:
        conn.execute(text("SELECT 1"))
