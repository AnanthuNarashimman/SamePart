from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from samepart.config import settings
from samepart.db.models import Base

_engine = None
_Factory = None


def engine():
    global _engine
    if _engine is None:
        _engine = create_engine(settings.db_url, future=True)
    return _engine


def init_db(drop: bool = False) -> None:
    if drop:
        Base.metadata.drop_all(engine())
    Base.metadata.create_all(engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    global _Factory
    if _Factory is None:
        _Factory = sessionmaker(bind=engine(), future=True, expire_on_commit=False)
    s = _Factory()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
