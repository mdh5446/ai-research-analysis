from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import Engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from stock_research.config.settings import Settings
from stock_research.db.models import StockDaily, StockMaster
from stock_research.db.repository import (
    add_stock,
    add_stock_daily,
    get_stock,
    get_stock_daily,
)
from stock_research.db.session import (
    build_engine,
    create_session_factory,
    init_db,
    session_scope,
)

type Database = tuple[Engine, sessionmaker[Session]]


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    engine = build_engine(f"sqlite:///{tmp_path / 'nested' / 'test.db'}")
    init_db(engine)
    try:
        yield engine, create_session_factory(engine)
    finally:
        engine.dispose()


def daily(trade_date: date = date(2026, 10, 2), symbol: str = "005930") -> StockDaily:
    return StockDaily(
        trade_date=trade_date,
        symbol=symbol,
        open=Decimal(70000),
        high=Decimal(71000),
        low=Decimal(69000),
        close=Decimal(70500),
        volume=123456,
        trading_value=None,
    )


def test_settings_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert Settings(_env_file=None).database_url == "sqlite:///./data/stock_research.db"


def test_settings_dotenv_and_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    env = tmp_path / ".env"
    env.write_text("DATABASE_URL=sqlite:///dotenv.db\n", encoding="utf-8")
    assert Settings(_env_file=env).database_url == "sqlite:///dotenv.db"
    monkeypatch.setenv("DATABASE_URL", "sqlite:///override.db")
    assert Settings(_env_file=env).database_url == "sqlite:///override.db"


def test_tables_and_repeat_initialization(database: Database) -> None:
    engine, _ = database
    init_db(engine)
    assert set(inspect(engine).get_table_names()) == {
        "stock_master",
        "stock_daily",
        "market_daily",
        "collection_snapshot",
    }


def test_stock_master_round_trip(database: Database) -> None:
    _, factory = database
    with session_scope(factory) as session:
        add_stock(
            session,
            StockMaster(symbol="005930", name="Samsung Electronics", market="KOSPI"),
        )
    with session_scope(factory) as session:
        stock = get_stock(session, "005930")
        assert stock is not None
        assert stock.id is not None
        assert (stock.symbol, stock.name, stock.market) == (
            "005930",
            "Samsung Electronics",
            "KOSPI",
        )
        assert stock.created_at is not None
        assert stock.updated_at is not None
        assert get_stock(session, "missing") is None


def test_stock_daily_round_trip(database: Database) -> None:
    _, factory = database
    with session_scope(factory) as session:
        add_stock_daily(session, daily())
    with session_scope(factory) as session:
        stock = get_stock_daily(session, date(2026, 10, 2), "005930")
        assert stock is not None
        assert stock.id is not None
        assert stock.trade_date == date(2026, 10, 2)
        assert stock.symbol == "005930"
        assert (stock.open, stock.high, stock.low, stock.close) == (
            Decimal(70000),
            Decimal(71000),
            Decimal(69000),
            Decimal(70500),
        )
        assert stock.volume == 123456
        assert stock.trading_value is None
        assert stock.created_at is not None


def test_duplicate_daily_rejected_without_overwriting(database: Database) -> None:
    _, factory = database
    with session_scope(factory) as session:
        add_stock_daily(session, daily())
    with pytest.raises(IntegrityError), session_scope(factory) as session:
        duplicate = daily()
        duplicate.close = Decimal(1)
        add_stock_daily(session, duplicate)
    with session_scope(factory) as session:
        original = get_stock_daily(session, date(2026, 10, 2), "005930")
        assert original is not None
        assert original.close == Decimal(70500)
        add_stock_daily(session, daily(date(2026, 10, 5)))
        other = daily(symbol="000660")
        other.trading_value = Decimal("123456789.1234")
        add_stock_daily(session, other)
    with session_scope(factory) as session:
        stored = get_stock_daily(session, date(2026, 10, 2), "000660")
        assert stored is not None
        assert stored.trading_value == Decimal("123456789.1234")


def test_session_rolls_back_on_failure(database: Database) -> None:
    _, factory = database
    with pytest.raises(RuntimeError), session_scope(factory) as session:
        add_stock(session, StockMaster(symbol="005930", name="Samsung", market="KOSPI"))
        raise RuntimeError("abort transaction")
    with session_scope(factory) as session:
        assert get_stock(session, "005930") is None
