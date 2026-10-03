"""Validated normalized external data; no persistence or feature calculations."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Market = Literal["KOSPI", "KOSDAQ"]
Price = Annotated[Decimal, Field(ge=0, max_digits=20, decimal_places=4)]
Value = Annotated[Decimal, Field(ge=0, max_digits=24, decimal_places=4)]
Volume = Annotated[int, Field(ge=0, le=9223372036854775807)]


class StockRecord(BaseModel):
    model_config = ConfigDict(frozen=True)
    trade_date: date
    symbol: str = Field(pattern=r"^[0-9A-Z]{6}$")
    name: str = Field(min_length=1, max_length=200)
    market: Market


class DailyPrices(BaseModel):
    model_config = ConfigDict(frozen=True)
    trade_date: date
    open: Price
    high: Price
    low: Price
    close: Price
    volume: Volume
    trading_value: Value | None = None

    @field_validator("open", "high", "low", "close", "trading_value")
    @classmethod
    def fixed_scale(cls, value: Decimal | None) -> Decimal | None:
        return None if value is None else value.quantize(Decimal("0.0001"))

    @model_validator(mode="after")
    def coherent_prices(self) -> DailyPrices:
        # Suspended stocks can report zero O/H/L and a nonzero previous close.
        if self.open == self.high == self.low == 0 and self.volume == 0:
            return self
        if (
            not self.low
            <= min(self.open, self.close)
            <= max(self.open, self.close)
            <= self.high
        ):
            raise ValueError("Inconsistent OHLC range")
        return self


class StockDailyRecord(DailyPrices):
    symbol: str = Field(pattern=r"^[0-9A-Z]{6}$")


class MarketDailyRecord(DailyPrices):
    index_code: Market


class CollectionResult(BaseModel):
    trade_date: date
    retrieved_at: datetime
    stocks: list[StockRecord]
    daily: list[StockDailyRecord]
    indices: list[MarketDailyRecord]
    raw: dict[str, list[dict[str, str]]]
