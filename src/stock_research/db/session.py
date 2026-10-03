from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from stock_research.db import models  # noqa: F401 -- register tables with metadata
from stock_research.db.base import Base


def build_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    if (
        url.get_backend_name() == "sqlite"
        and url.database
        and url.database != ":memory:"
    ):
        Path(url.database).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(url)


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as session, session.begin():
        yield session
