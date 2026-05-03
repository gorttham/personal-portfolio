from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class AccountSummary(BaseModel):
    id: str
    broker: str
    currency: str
    total_value: float
    account_name: str


class PortfolioSummaryResponse(BaseModel):
    accounts: list[AccountSummary]
    last_synced_at: Optional[datetime]


class SnapshotPoint(BaseModel):
    timestamp: datetime
    value: float


class SnapshotSeries(BaseModel):
    name: str
    data: list[SnapshotPoint]


class PortfolioSnapshotsResponse(BaseModel):
    series: list[SnapshotSeries]
    currency_groups: list[str]


class TransactionMarker(BaseModel):
    ticker: str
    type: str          # "buy" | "sell"
    quantity: float
    price: float
    executed_at: datetime


class PositionItem(BaseModel):
    ticker: str
    name: str
    current_value: float
    currency: str
    asset_class: str
    sector: Optional[str]
    country: Optional[str]
    broker: str
    label_names: list[str]
