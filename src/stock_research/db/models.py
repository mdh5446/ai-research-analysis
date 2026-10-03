from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Date,
    DateTime,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from stock_research.db.base import Base


def utc_now() -> datetime:
    # SQLite stores naive datetimes; all persistence timestamps are UTC.
    return datetime.now(UTC).replace(tzinfo=None)


class StockMaster(Base):
    __tablename__ = "stock_master"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    market: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )


class StockDaily(Base):
    __tablename__ = "stock_daily"
    __table_args__ = (
        UniqueConstraint("trade_date", "symbol", name="uq_stock_daily_date_symbol"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date)
    symbol: Mapped[str] = mapped_column(String(20))
    open: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    high: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    low: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    close: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    volume: Mapped[int] = mapped_column(BigInteger)
    trading_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class MarketDaily(Base):
    __tablename__ = "market_daily"
    __table_args__ = (
        UniqueConstraint("trade_date", "index_code", name="uq_market_daily_date_index"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date)
    index_code: Mapped[str] = mapped_column(String(20))
    open: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    high: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    low: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    close: Mapped[Decimal] = mapped_column(Numeric(20, 4))
    volume: Mapped[int] = mapped_column(BigInteger)
    trading_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class CollectionSnapshot(Base):
    """Original response rows and dated master information, without credentials."""

    __tablename__ = "collection_snapshot"
    __table_args__ = (
        UniqueConstraint("trade_date", "source", name="uq_collection_date_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(30))
    retrieved_at: Mapped[datetime] = mapped_column(DateTime)
    raw: Mapped[dict] = mapped_column(JSON)
    normalized: Mapped[dict] = mapped_column(JSON)
