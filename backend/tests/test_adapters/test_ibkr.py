import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from app.adapters.ibkr import IBKRAdapter

MOCK_CREDS = {
    "base_url": "https://localhost:5000/v1/api",
    "account_id": "U1234567",
}

@pytest.fixture
def adapter():
    return IBKRAdapter(credentials=MOCK_CREDS)

def test_adapter_instantiates(adapter):
    assert adapter._creds["account_id"] == "U1234567"

@pytest.mark.asyncio
async def test_get_positions_normalises_response(adapter):
    mock_response = [
        {
            "ticker": "AAPL",
            "companyName": "APPLE INC",
            "position": 10.0,
            "avgCost": 150.0,
            "mktPrice": 175.0,
            "mktValue": 1750.0,
            "currency": "USD",
            "assetClass": "STK",
            "sector": "Technology",
            "listingExchange": "NASDAQ",
        }
    ]

    with patch("app.adapters.ibkr.httpx.AsyncClient") as MockClient:
        mock_client_instance = MagicMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response
        mock_resp.raise_for_status = MagicMock()
        mock_client_instance.get.return_value = mock_resp
        positions = await adapter.get_positions("U1234567")

    assert len(positions) == 1
    assert positions[0].ticker == "AAPL"
    assert positions[0].current_value == Decimal("1750.0")
    assert positions[0].asset_class == "stock"

@pytest.mark.asyncio
async def test_get_accounts_uses_cred_account_id(adapter):
    accounts = await adapter.get_accounts()
    assert len(accounts) == 1
    assert accounts[0].broker_account_id == "U1234567"
