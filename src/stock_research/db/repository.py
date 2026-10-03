"""Small persistence helpers. Transactions belong to the caller."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from stock_research.collectors.schemas import CollectionResult
from stock_research.db.models import (
    CollectionSnapshot,
    MarketDaily,
    StockDaily,
    StockMaster,
)


def add_stock(session: Session, stock: StockMaster) -> None:
    session.add(stock)
    session.flush()


def get_stock(session: Session, symbol: str) -> StockMaster | None:
    return session.scalar(select(StockMaster).where(StockMaster.symbol == symbol))


def add_stock_daily(session: Session, daily: StockDaily) -> None:
    # Insert only: duplicate snapshots raise IntegrityError, never overwrite.
    session.add(daily)
    session.flush()


def get_stock_daily(
    session: Session, trade_date: date, symbol: str
) -> StockDaily | None:
    return session.scalar(
        select(StockDaily).where(
            StockDaily.trade_date == trade_date, StockDaily.symbol == symbol
        )
    )


class SnapshotConflict(ValueError):
    """Stored historical data differs; never overwrite it."""


def persist_collection(session: Session, result: CollectionResult) -> bool:
    """Persist a validated complete collection in caller's transaction.

    Returns False on an identical normalized rerun. Original response remains intact.
    """
    source = "KRX_OPEN_API"
    normalized = {
        "version": 1,
        "stocks": [
            r.model_dump(mode="json")
            for r in sorted(result.stocks, key=lambda r: r.symbol)
        ],
        "daily": [
            r.model_dump(mode="json")
            for r in sorted(result.daily, key=lambda r: r.symbol)
        ],
        "indices": [
            r.model_dump(mode="json")
            for r in sorted(result.indices, key=lambda r: r.index_code)
        ],
    }
    snapshot = session.scalar(
        select(CollectionSnapshot).where(
            CollectionSnapshot.trade_date == result.trade_date,
            CollectionSnapshot.source == source,
        )
    )
    if snapshot is not None:
        if snapshot.normalized != normalized:
            raise SnapshotConflict(
                f"Collection conflicts with snapshot: {result.trade_date}"
            )
        return False

    latest = session.scalar(
        select(func.max(CollectionSnapshot.trade_date)).where(
            CollectionSnapshot.source == source,
        )
    )
    masters = {s.symbol: s for s in session.scalars(select(StockMaster))}
    for record in result.stocks:
        existing = masters.get(record.symbol)
        if existing is None:
            session.add(
                StockMaster(
                    symbol=record.symbol, name=record.name, market=record.market
                )
            )
        elif latest is None or result.trade_date >= latest:
            existing.name, existing.market = record.name, record.market

    stock_rows = {
        r.symbol: r
        for r in session.scalars(
            select(StockDaily).where(
                StockDaily.trade_date == result.trade_date,
            )
        )
    }
    index_rows = {
        r.index_code: r
        for r in session.scalars(
            select(MarketDaily).where(
                MarketDaily.trade_date == result.trade_date,
            )
        )
    }
    for record in result.daily:
        values = record.model_dump()
        existing = stock_rows.get(record.symbol)
        if existing is None:
            session.add(StockDaily(**values))
        elif any(getattr(existing, key) != value for key, value in values.items()):
            raise SnapshotConflict(
                f"Stock daily conflict: {record.symbol} {result.trade_date}"
            )
    for record in result.indices:
        values = record.model_dump()
        existing = index_rows.get(record.index_code)
        if existing is None:
            session.add(MarketDaily(**values))
        elif any(getattr(existing, key) != value for key, value in values.items()):
            raise SnapshotConflict(
                f"Index daily conflict: {record.index_code} {result.trade_date}"
            )
    session.add(
        CollectionSnapshot(
            trade_date=result.trade_date,
            source=source,
            retrieved_at=result.retrieved_at,
            raw=result.raw,
            normalized=normalized,
        )
    )
    session.flush()
    return True
