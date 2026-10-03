"""Single-date KRX OPEN API collection. No database writes."""

from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
from pydantic import SecretStr, ValidationError

from stock_research.collectors.schemas import (
    CollectionResult,
    MarketDailyRecord,
    StockDailyRecord,
    StockRecord,
)

BASE_URL = "https://data-dbg.krx.co.kr/svc/apis"
ENDPOINTS = {
    "KOSPI": ("sto/stk_isu_base_info", "sto/stk_bydd_trd", "idx/kospi_dd_trd"),
    "KOSDAQ": ("sto/ksq_isu_base_info", "sto/ksq_bydd_trd", "idx/kosdaq_dd_trd"),
}
INDEX_NAMES = {
    "KOSPI": {"\ucf54\uc2a4\ud53c", "KOSPI"},
    "KOSDAQ": {"\ucf54\uc2a4\ub2e5", "KOSDAQ"},
}


class CollectionError(ValueError):
    """Safe operational error; never includes authentication or response bodies."""


def number(row: dict[str, str], key: str) -> Decimal:
    return Decimal(row[key].replace(",", "").strip())


def prices(row: dict[str, str], index: bool = False) -> dict:
    keys = (
        ("OPNPRC_IDX", "HGPRC_IDX", "LWPRC_IDX", "CLSPRC_IDX")
        if index
        else ("TDD_OPNPRC", "TDD_HGPRC", "TDD_LWPRC", "TDD_CLSPRC")
    )
    value = row.get("ACC_TRDVAL", "").strip()
    volume = number(row, "ACC_TRDVOL")
    if volume != volume.to_integral_value():
        raise CollectionError("Noninteger trading volume")
    return dict(
        zip(
            ("open", "high", "low", "close"),
            (number(row, k) for k in keys),
            strict=True,
        )
    ) | {
        "volume": int(volume),
        "trading_value": None if value in {"", "-"} else number(row, "ACC_TRDVAL"),
    }


class KrxCollector:
    def __init__(self, client: httpx.Client, api_key: SecretStr) -> None:
        if not api_key.get_secret_value().strip():
            raise CollectionError("Set KRX_API_KEY after KRX approval")
        self.client = client
        self.api_key = api_key

    def _rows(self, endpoint: str, trade_date: date) -> list[dict[str, str]]:
        try:
            response = self.client.get(
                f"{BASE_URL}/{endpoint}",
                params={"basDd": trade_date.strftime("%Y%m%d")},
                headers={"AUTH_KEY": self.api_key.get_secret_value()},
                timeout=30,
            )
        except httpx.HTTPError:
            raise CollectionError(f"KRX network failure: {endpoint}") from None
        if response.status_code != 200:
            raise CollectionError(f"KRX HTTP {response.status_code}: {endpoint}")
        try:
            payload = response.json()
        except ValueError:
            raise CollectionError(f"KRX invalid JSON: {endpoint}") from None
        rows = payload.get("OutBlock_1") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or not rows:
            raise CollectionError(
                f"KRX missing/empty data: {endpoint}; check date, publication, approval"
            )
        if any(
            not isinstance(row, dict)
            or any(not isinstance(v, str) for v in row.values())
            for row in rows
        ):
            raise CollectionError(f"KRX unexpected row schema: {endpoint}")
        return rows

    def collect(self, trade_date: date) -> CollectionResult:
        raw: dict[str, list[dict[str, str]]] = {}
        stocks: list[StockRecord] = []
        daily: list[StockDailyRecord] = []
        indices: list[MarketDailyRecord] = []
        try:
            for market, (master_ep, daily_ep, index_ep) in ENDPOINTS.items():
                for endpoint in (master_ep, daily_ep, index_ep):
                    raw[endpoint] = self._rows(endpoint, trade_date)
                for row in raw[master_ep]:
                    if "BAS_DD" in row:
                        self._check_date(row, trade_date)
                    stocks.append(
                        StockRecord(
                            trade_date=trade_date,
                            symbol=row["ISU_SRT_CD"],
                            name=row["ISU_NM"].strip(),
                            market=market,
                        )
                    )
                market_symbols = {s.symbol for s in stocks if s.market == market}
                for row in raw[daily_ep]:
                    self._check_date(row, trade_date)
                    if row["ISU_CD"] not in market_symbols:
                        raise CollectionError(
                            "KRX daily symbol missing from matching master"
                        )
                    daily.append(
                        StockDailyRecord(
                            trade_date=trade_date,
                            symbol=row["ISU_CD"],
                            **prices(row),
                        )
                    )
                if {r["ISU_CD"] for r in raw[daily_ep]} != market_symbols:
                    raise CollectionError(
                        "KRX incomplete daily universe relative to master"
                    )
                selected = [
                    r
                    for r in raw[index_ep]
                    if r["IDX_NM"].strip() in INDEX_NAMES[market]
                ]
                if len(selected) != 1:
                    raise CollectionError(
                        f"KRX expected exactly one headline index: {market}"
                    )
                row = selected[0]
                self._check_date(row, trade_date)
                indices.append(
                    MarketDailyRecord(
                        trade_date=trade_date,
                        index_code=market,
                        **prices(row, index=True),
                    )
                )
        except KeyError, ArithmeticError, ValidationError, TypeError:
            raise CollectionError("KRX invalid fields; no data persisted") from None
        if len({s.symbol for s in stocks}) != len(stocks) or len(
            {s.symbol for s in daily}
        ) != len(daily):
            raise CollectionError("KRX duplicate symbols")
        return CollectionResult(
            trade_date=trade_date,
            retrieved_at=datetime.now(UTC).replace(tzinfo=None),
            stocks=stocks,
            daily=daily,
            indices=indices,
            raw=raw,
        )

    @staticmethod
    def _check_date(row: dict[str, str], trade_date: date) -> None:
        if row["BAS_DD"] != trade_date.strftime("%Y%m%d"):
            raise CollectionError("KRX response date differs from requested date")
