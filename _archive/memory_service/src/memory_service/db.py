"""Initialisation de la base SQLite et sessions SQLAlchemy."""

from __future__ import annotations

from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import Settings
from .models import Base

_ENGINE: Optional[Engine] = None
_SESSION_FACTORY: Optional[sessionmaker] = None


def create_session_factory(settings: Settings) -> sessionmaker:
    """Retourne un sessionmaker initialisé (singleton)."""

    global _ENGINE, _SESSION_FACTORY
    if _SESSION_FACTORY is not None:
        return _SESSION_FACTORY

    db_url = settings.database_url
    if db_url.startswith("sqlite:///"):
        data_dir = Path(settings.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)

    connect_args = {}
    extra_kwargs = {}
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        if db_url == "sqlite:///:memory:":
            extra_kwargs["poolclass"] = StaticPool

    _ENGINE = create_engine(db_url, echo=False, future=True, connect_args=connect_args, **extra_kwargs)
    Base.metadata.create_all(_ENGINE)
    _SESSION_FACTORY = sessionmaker(
        bind=_ENGINE,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    return _SESSION_FACTORY


def get_session(session_factory: sessionmaker) -> Generator[Session, None, None]:
    """Contexte simple pour obtenir une session."""

    session = session_factory()
    try:
        yield session
    finally:
        session.close()



