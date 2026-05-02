import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime, timezone
from app.adapters.moomoo import MoomooAdapter

MOCK_CREDS = {
    "host": "127.0.0.1",
    "port": 11111,
    "trade_env": "REAL",
    "acc_id": 123456789,
}

@pytest.fixture
def adapter():
    return MoomooAdapter(credentials=MOCK_CREDS)

def test_adapter_instantiates(adapter):
    assert adapter._creds["acc_id"] == 123456789

@pytest.mark.asyncio
async def test_get_positions_normalises_data(adapter):
    import pandas as pd
    mock_df = pd.DataFrame([{
        "code": "US.AAPL",
        "stock_name": "Apple Inc",
        "qty": 10,
        "cost_price": 150.0,
        "current_price": 175.0,
        "market_val": 1750.0,
        "currency": "USD",
        "sec_market": "US",
        "stock_type": "STOCK",
    }])

    with patch("app.adapters.moomoo.OpenSecTradeContext") as MockCtx:
        instance = MockCtx.return_value.__enter__.return_value
        instance.position_list_query.return_value = ("0", mock_df)
        positions = await adapter.get_positions("123456789")

    assert len(positions) == 1
    assert positions[0].ticker == "US.AAPL"
    assert positions[0].current_value == Decimal("1750.0")
    assert positions[0].country == "US"

@pytest.mark.asyncio
async def test_get_positions_returns_empty_on_api_error(adapter):
    with patch("app.adapters.moomoo.OpenSecTradeContext") as MockCtx:
        instance = MockCtx.return_value.__enter__.return_value
        instance.position_list_query.return_value = ("ERROR", None)
        positions = await adapter.get_positions("123456789")

    assert positions == []
