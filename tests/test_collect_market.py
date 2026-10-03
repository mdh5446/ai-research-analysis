"""Synthetic contract fixtures; live API approval is a separate verification gate."""

import argparse
from collections.abc import Iterator
from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import Engine, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from scripts.collect_market import main, validate_date
from stock_research.collectors.krx import ENDPOINTS, CollectionError, KrxCollector
from stock_research.collectors.schemas import CollectionResult
from stock_research.db.models import (
    CollectionSnapshot,
    MarketDaily,
    StockDaily,
    StockMaster,
)
from stock_research.db.repository import SnapshotConflict, persist_collection
from stock_research.db.session import (
    build_engine,
    create_session_factory,
    init_db,
    session_scope,
)

DAY = date(2026, 9, 30)
type Database = tuple[Engine, sessionmaker[Session]]


def payloads(day: date = DAY) -> dict[str, dict]:
    result = {}
    for market, symbol in (("KOSPI", "005930"), ("KOSDAQ", "000250")):
        master, daily, index = ENDPOINTS[market]
        result[master] = {
            "OutBlock_1": [
                {
                    "ISU_CD": "KR7005930003",
                    "ISU_SRT_CD": symbol,
                    "ISU_NM": f"{market} stock",
                }
            ]
        }
        result[daily] = {
            "OutBlock_1": [
                {
                    "BAS_DD": day.strftime("%Y%m%d"),
                    "ISU_CD": symbol,
                    "TDD_OPNPRC": "70,000",
                    "TDD_HGPRC": "71,000",
                    "TDD_LWPRC": "69,000",
                    "TDD_CLSPRC": "70,500",
                    "ACC_TRDVOL": "123,456",
                    "ACC_TRDVAL": "8,703,648,000",
                }
            ]
        }
        result[index] = {
            "OutBlock_1": [
                {
                    "BAS_DD": day.strftime("%Y%m%d"),
                    "IDX_NM": "\ucf54\uc2a4\ud53c"
                    if market == "KOSPI"
                    else "\ucf54\uc2a4\ub2e5",
                    "OPNPRC_IDX": "2,500.12",
                    "HGPRC_IDX": "2,520.45",
                    "LWPRC_IDX": "2,490.11",
                    "CLSPRC_IDX": "2,510.23",
                    "ACC_TRDVOL": "456,789",
                    "ACC_TRDVAL": "12,000,000,000",
                },
                {"IDX_NM": f"{market} 200"},
            ]
        }
    return result


def collect(data: dict | None = None, day: date = DAY) -> CollectionResult:
    data = payloads(day) if data is None else data

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.scheme == "https"
        assert request.headers["AUTH_KEY"] == "test-secret"
        assert request.url.params["basDd"] == day.strftime("%Y%m%d")
        return httpx.Response(
            200, json=data[request.url.path.removeprefix("/svc/apis/")]
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        return KrxCollector(client, SecretStr("test-secret")).collect(day)


@pytest.fixture
def database(tmp_path: Path) -> Iterator[Database]:
    engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    init_db(engine)
    try:
        yield engine, create_session_factory(engine)
    finally:
        engine.dispose()


def test_six_endpoint_normalization_and_index_selection() -> None:
    result = collect()
    assert len(result.raw) == 6
    assert [r.symbol for r in result.stocks] == ["005930", "000250"]
    assert result.daily[0].close == Decimal(70500)
    assert result.daily[0].volume == 123456
    assert result.indices[0].close == Decimal("2510.23")
    assert [r.index_code for r in result.indices] == ["KOSPI", "KOSDAQ"]
    assert "test-secret" not in result.model_dump_json()


@pytest.mark.parametrize(
    "field,value",
    [
        ("BAS_DD", "20260929"),
        ("TDD_CLSPRC", "-"),
        ("TDD_CLSPRC", "NaN"),
        ("TDD_CLSPRC", "72000"),
        ("ACC_TRDVOL", "-1"),
        ("ACC_TRDVOL", "1.5"),
        ("ISU_CD", "999999"),
    ],
)
def test_invalid_daily_rejected(field: str, value: str) -> None:
    data = payloads()
    data["sto/stk_bydd_trd"]["OutBlock_1"][0][field] = value
    with pytest.raises(CollectionError):
        collect(data)


def test_zero_suspended_prices_and_missing_optional_value() -> None:
    data = payloads()
    row = data["sto/stk_bydd_trd"]["OutBlock_1"][0]
    row.update(
        TDD_OPNPRC="0", TDD_HGPRC="0", TDD_LWPRC="0", ACC_TRDVOL="0", ACC_TRDVAL="-"
    )
    record = collect(data).daily[0]
    assert record.open == 0 and record.close == 70500
    assert record.trading_value is None


@pytest.mark.parametrize(
    "payload", [{}, {"OutBlock_1": []}, {"OutBlock_1": [{}]}, {"OutBlock_1": [1]}]
)
def test_empty_or_malformed_response_rejected(payload: dict) -> None:
    data = payloads()
    data["sto/stk_isu_base_info"] = payload
    with pytest.raises(CollectionError):
        collect(data)


@pytest.mark.parametrize("failure", ["403", "429", "500", "html", "timeout"])
def test_errors_are_safe(failure: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if failure == "timeout":
            raise httpx.ReadTimeout("test-secret", request=request)
        if failure == "html":
            return httpx.Response(200, text="test-secret")
        return httpx.Response(int(failure), text="test-secret")

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(CollectionError) as exc:
            KrxCollector(client, SecretStr("test-secret")).collect(DAY)
        assert "test-secret" not in str(exc.value)


def test_missing_key_sends_no_request() -> None:
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda _: pytest.fail("network called"))
        ) as client,
        pytest.raises(CollectionError, match="KRX_API_KEY"),
    ):
        KrxCollector(client, SecretStr(""))


def test_duplicate_and_missing_universe_rejected() -> None:
    data = payloads()
    data["sto/stk_bydd_trd"]["OutBlock_1"] *= 2
    with pytest.raises(CollectionError, match="duplicate"):
        collect(data)
    data = payloads()
    extra = deepcopy(data["sto/stk_isu_base_info"]["OutBlock_1"][0])
    extra["ISU_SRT_CD"] = "000660"
    data["sto/stk_isu_base_info"]["OutBlock_1"].append(extra)
    with pytest.raises(CollectionError, match="incomplete"):
        collect(data)


def test_round_trip_rerun_and_conflict(database: Database) -> None:
    _, factory = database
    result = collect()
    with session_scope(factory) as session:
        assert persist_collection(session, result)
    with session_scope(factory) as session:
        assert not persist_collection(session, collect())
        assert session.scalar(select(func.count()).select_from(StockMaster)) == 2
        assert session.scalar(select(func.count()).select_from(StockDaily)) == 2
        assert session.scalar(select(func.count()).select_from(MarketDaily)) == 2
        snapshot = session.scalar(select(CollectionSnapshot))
        assert snapshot is not None and len(snapshot.raw) == 6
    changed = payloads()
    changed["sto/stk_bydd_trd"]["OutBlock_1"][0]["TDD_CLSPRC"] = "70600"
    with pytest.raises(SnapshotConflict), session_scope(factory) as session:
        persist_collection(session, collect(changed))
    with session_scope(factory) as session:
        assert (
            session.scalar(
                select(StockDaily.close).where(StockDaily.symbol == "005930")
            )
            == 70500
        )


def test_preexisting_daily_conflict_rolls_back_everything(database: Database) -> None:
    _, factory = database
    with session_scope(factory) as session:
        values = collect().daily[0].model_dump()
        values["close"] = Decimal(1)
        session.add(StockDaily(**values))
    with pytest.raises(SnapshotConflict), session_scope(factory) as session:
        persist_collection(session, collect())
    with session_scope(factory) as session:
        assert session.scalar(select(func.count()).select_from(StockMaster)) == 0
        assert session.scalar(select(func.count()).select_from(MarketDaily)) == 0
        assert session.scalar(select(func.count()).select_from(CollectionSnapshot)) == 0


def test_older_collection_keeps_latest_master(database: Database) -> None:
    _, factory = database
    newer = payloads()
    newer["sto/stk_isu_base_info"]["OutBlock_1"][0]["ISU_NM"] = "New name"
    with session_scope(factory) as session:
        persist_collection(session, collect(newer))
    old_day = date(2026, 9, 29)
    with session_scope(factory) as session:
        persist_collection(session, collect(day=old_day))
    with session_scope(factory) as session:
        assert (
            session.scalar(
                select(StockMaster.name).where(StockMaster.symbol == "005930")
            )
            == "New name"
        )
        old = session.scalar(
            select(CollectionSnapshot).where(CollectionSnapshot.trade_date == old_day)
        )
        assert old is not None
        assert any(r["name"] == "KOSPI stock" for r in old.normalized["stocks"])


@pytest.mark.parametrize("value", ["20260930", "2009-12-31", "2099-01-01", "bad"])
def test_invalid_cli_dates(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        validate_date(value)


def test_same_day_disabled() -> None:
    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    with pytest.raises(argparse.ArgumentTypeError):
        validate_date(today.isoformat())


def test_cli_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cli.db'}")
    monkeypatch.setenv("KRX_API_KEY", "test-secret")
    monkeypatch.setattr("sys.argv", ["collect_market.py", "--date", DAY.isoformat()])
    original_client = httpx.Client
    data = payloads()
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, json=data[r.url.path.removeprefix("/svc/apis/")])
    )
    monkeypatch.setattr(httpx, "Client", lambda: original_client(transport=transport))
    main()
    main()
    output = capsys.readouterr().out
    assert "Stored:" in output and "Already stored (unchanged)" in output
    assert "test-secret" not in output
    engine = build_engine(f"sqlite:///{tmp_path / 'cli.db'}")
    try:
        with Session(engine) as session:
            assert (
                session.scalar(select(func.count()).select_from(CollectionSnapshot))
                == 1
            )
    finally:
        engine.dispose()


def test_last_endpoint_failure_leaves_no_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'cli.db'}")
    monkeypatch.setenv("KRX_API_KEY", "test-secret")
    monkeypatch.setattr("sys.argv", ["collect_market.py", "--date", DAY.isoformat()])
    data = payloads()
    data["idx/kosdaq_dd_trd"] = {"OutBlock_1": []}
    original_client = httpx.Client
    transport = httpx.MockTransport(
        lambda r: httpx.Response(200, json=data[r.url.path.removeprefix("/svc/apis/")])
    )
    monkeypatch.setattr(httpx, "Client", lambda: original_client(transport=transport))
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert not (tmp_path / "cli.db").exists()


def test_equivalent_numeric_formatting_skips_snapshot(database: Database) -> None:
    _, factory = database
    with session_scope(factory) as session:
        persist_collection(session, collect())
    data = payloads()
    data["sto/stk_bydd_trd"]["OutBlock_1"][0]["TDD_CLSPRC"] = "70500.0000"
    with session_scope(factory) as session:
        assert not persist_collection(session, collect(data))


def test_index_unique_date_code(database: Database) -> None:
    _, factory = database
    values = collect().indices[0].model_dump()
    with session_scope(factory) as session:
        session.add(MarketDaily(**values))
    with pytest.raises(IntegrityError), session_scope(factory) as session:
        session.add(MarketDaily(**values))
        session.flush()


def test_additive_initialization_preserves_step1_database(tmp_path: Path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'old.db'}")
    try:
        StockMaster.__table__.create(engine)
        StockDaily.__table__.create(engine)
        before = [
            (c["name"], str(c["type"]), c["nullable"], c["default"], c["primary_key"])
            for c in inspect(engine).get_columns("stock_daily")
        ]
        with Session(engine) as session, session.begin():
            session.add(StockMaster(symbol="005930", name="Existing", market="KOSPI"))
            session.add(StockDaily(**collect().daily[0].model_dump()))
        init_db(engine)
        init_db(engine)
        assert [
            (c["name"], str(c["type"]), c["nullable"], c["default"], c["primary_key"])
            for c in inspect(engine).get_columns("stock_daily")
        ] == before
        with Session(engine) as session:
            assert session.scalar(select(StockMaster.name)) == "Existing"
            assert session.scalar(select(StockDaily.close)) == 70500
            assert (
                session.scalar(select(func.count()).select_from(CollectionSnapshot))
                == 0
            )
    finally:
        engine.dispose()
