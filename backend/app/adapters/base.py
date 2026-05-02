from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class TransactionType(str, Enum):
    buy = "buy"
    sell = "sell"


@dataclass
class AdapterAccount:
    broker_account_id: str
    account_type: str
    currency: str
    name: str = ""


@dataclass
class AdapterBalance:
    account_id: str
    total_value: Decimal
    currency: str


@dataclass
class AdapterPosition:
    ticker: str
    name: str
    quantity: Decimal
    avg_cost: Optional[Decimal]
    current_price: Optional[Decimal]
    current_value: Decimal
    currency: str
    asset_class: Optional[str] = None
    sector: Optional[str] = None
    country: Optional[str] = None


@dataclass
class AdapterTransaction:
    broker_transaction_id: str
    ticker: str
    type: TransactionType
    quantity: Decimal
    price: Decimal
    total_value: Decimal
    currency: str
    executed_at: datetime


class BrokerageAdapter(ABC):
    @abstractmethod
    async def get_accounts(self) -> list[AdapterAccount]: ...

    @abstractmethod
    async def get_positions(self, account_id: str) -> list[AdapterPosition]: ...

    @abstractmethod
    async def get_transactions(self, account_id: str, since: datetime) -> list[AdapterTransaction]: ...

    @abstractmethod
    async def get_balance(self, account_id: str) -> AdapterBalance: ...
