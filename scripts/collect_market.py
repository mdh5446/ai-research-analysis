"""Manual single-date collection only; daily orchestration is a later step."""

import argparse
from datetime import date, datetime
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy.exc import SQLAlchemyError

from stock_research.collectors.krx import CollectionError, KrxCollector
from stock_research.config.settings import Settings
from stock_research.db.repository import SnapshotConflict, persist_collection
from stock_research.db.session import (
    build_engine,
    create_session_factory,
    init_db,
    session_scope,
)


def validate_date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Use YYYY-MM-DD") from None
    if parsed.isoformat() != value:
        raise argparse.ArgumentTypeError("Use YYYY-MM-DD")
    if parsed < date(2010, 1, 4):
        raise argparse.ArgumentTypeError("KRX coverage starts 2010-01-04")
    if parsed >= datetime.now(ZoneInfo("Asia/Seoul")).date():
        raise argparse.ArgumentTypeError(
            "Use a past date; same-day/future collection is disabled"
        )
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect KRX master, OHLCV, KOSPI, KOSDAQ"
    )
    parser.add_argument("--date", required=True, type=validate_date)
    args = parser.parse_args()
    settings = Settings()
    try:
        with httpx.Client() as client:
            result = KrxCollector(client, settings.krx_api_key).collect(args.date)
    except CollectionError as exc:
        parser.exit(1, f"Collection failed: {exc}\n")
    engine = build_engine(settings.database_url)
    try:
        init_db(engine)
        with session_scope(create_session_factory(engine)) as session:
            inserted = persist_collection(session, result)
    except SnapshotConflict as exc:
        parser.exit(1, f"Collection failed: {exc}\n")
    except SQLAlchemyError:
        parser.exit(1, "Database operation failed; transaction rolled back.\n")
    finally:
        engine.dispose()
    status = "Stored" if inserted else "Already stored (unchanged)"
    print(
        f"{status}: {args.date}; master={len(result.stocks)}, stocks={len(result.daily)}, indices={len(result.indices)}"
    )


if __name__ == "__main__":
    main()
