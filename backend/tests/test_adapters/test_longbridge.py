import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from app.adapters.longbridge import LongbridgeAdapter

MOCK_CREDS = {
    "app_key": "test_key",
    "app_secret": "test_secret",
    "access_token": "test_token",
}

@pytest.fixture
def adapter():
    return LongbridgeAdapter(credentials=MOCK_CREDS)

@pytest.mark.asyncio
async def test_get_accounts_returns_list(adapter):
    mock_account = MagicMock()
    mock_account.account_id = "ACC001"
    mock_account.account_type = MagicMock()
    mock_account.account_type.name = "CASH"
    mock_account.currency = "HKD"

    with patch.object(adapter, "_get_trade_context") as mock_ctx:
        mock_ctx.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
            account_balance=AsyncMock(return_value=MagicMock(list=[mock_account]))
        ))
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
        accounts = await adapter.get_accounts()

    assert len(accounts) == 1
    assert accounts[0].broker_account_id == "ACC001"
    assert accounts[0].currency == "HKD"

@pytest.mark.asyncio
async def test_get_positions_normalises_to_adapter_position(adapter):
    mock_pos = MagicMock()
    mock_pos.symbol = "700.HK"
    mock_pos.symbol_name = "Tencent"
    mock_pos.quantity = 100
    mock_pos.cost_price = Decimal("300.00")
    mock_pos.current_price = Decimal("350.00")
    mock_pos.market_value = Decimal("35000.00")
    mock_pos.currency = "HKD"
    mock_pos.sector = None
    mock_pos.market = MagicMock()
    mock_pos.market.name = "HK"

    with patch.object(adapter, "_get_trade_context") as mock_ctx:
        mock_ctx.return_value.__aenter__ = AsyncMock(return_value=MagicMock(
            stock_positions=AsyncMock(return_value=MagicMock(
                channels=[MagicMock(positions=[mock_pos])]
            ))
        ))
        mock_ctx.return_value.__aexit__ = AsyncMock(return_value=False)
        positions = await adapter.get_positions("ACC001")

    assert len(positions) == 1
    assert positions[0].ticker == "700.HK"
    assert positions[0].current_value == Decimal("35000.00")
    assert positions[0].country == "HK"
