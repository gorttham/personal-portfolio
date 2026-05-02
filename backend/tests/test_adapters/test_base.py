from app.adapters.base import (
    AdapterPosition, AdapterTransaction, AdapterAccount,
    AdapterBalance, BrokerageAdapter, TransactionType
)
from datetime import datetime
from decimal import Decimal


def test_adapter_position_fields():
    pos = AdapterPosition(
        ticker="AAPL",
        name="Apple Inc",
        quantity=Decimal("10"),
        avg_cost=Decimal("150.00"),
        current_price=Decimal("175.00"),
        current_value=Decimal("1750.00"),
        currency="USD",
    )
    assert pos.ticker == "AAPL"
    assert pos.asset_class is None
    assert pos.sector is None
    assert pos.country is None


def test_adapter_transaction_type_enum():
    assert TransactionType.buy.value == "buy"
    assert TransactionType.sell.value == "sell"


def test_brokerage_adapter_is_abstract():
    import inspect
    assert inspect.isabstract(BrokerageAdapter)
