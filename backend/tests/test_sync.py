import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime, timezone
from app.services.sync import run_sync_for_connection
from app.adapters.base import AdapterAccount, AdapterPosition, AdapterBalance, AdapterTransaction


@pytest.fixture
def mock_connection():
    conn = MagicMock()
    conn.id = uuid.uuid4()
    conn.user_id = uuid.uuid4()
    conn.broker = "longbridge"
    conn.credentials = "encrypted-creds"
    conn.status = "active"
    return conn


@pytest.fixture
def mock_adapter():
    adapter = AsyncMock()
    adapter.get_accounts.return_value = [
        AdapterAccount(broker_account_id="ACC1", account_type="CASH", currency="HKD", name="Test")
    ]
    adapter.get_positions.return_value = [
        AdapterPosition(
            ticker="700.HK", name="Tencent", quantity=Decimal("100"),
            avg_cost=Decimal("300"), current_price=Decimal("350"),
            current_value=Decimal("35000"), currency="HKD",
        )
    ]
    adapter.get_balance.return_value = AdapterBalance(
        account_id="ACC1", total_value=Decimal("35000"), currency="HKD"
    )
    adapter.get_transactions.return_value = []
    return adapter


@pytest.mark.asyncio
async def test_run_sync_logs_success(mock_connection, mock_adapter):
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None)))
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    with patch("app.services.sync.build_adapter", return_value=mock_adapter), \
         patch("app.services.sync.decrypt", return_value='{"app_key":"k"}'):
        result = await run_sync_for_connection(mock_connection, mock_session)

    assert result["status"] == "success"
    assert mock_session.add.called


@pytest.mark.asyncio
async def test_run_sync_logs_error_on_adapter_failure(mock_connection):
    failing_adapter = AsyncMock()
    failing_adapter.get_accounts.side_effect = Exception("Connection refused")

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()

    with patch("app.services.sync.build_adapter", return_value=failing_adapter), \
         patch("app.services.sync.decrypt", return_value='{"app_key":"k"}'):
        result = await run_sync_for_connection(mock_connection, mock_session)

    assert result["status"] == "error"
    assert "Connection refused" in result["error"]
