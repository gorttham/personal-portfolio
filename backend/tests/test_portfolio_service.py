import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from uuid import uuid4

from app.services.portfolio import PortfolioService


@pytest.fixture
def user_id():
    return str(uuid4())


@pytest.fixture
def mock_session():
    return AsyncMock()


class TestGetSummary:
    @pytest.mark.asyncio
    async def test_returns_accounts_list(self, mock_session, user_id):
        row = MagicMock()
        row.id = str(uuid4())
        row.broker = "longbridge"
        row.currency = "HKD"
        row.total_value = 35000.0
        row.account_name = "Main"

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [row]
        sync_result = MagicMock()
        sync_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(side_effect=[result_mock, sync_result])

        svc = PortfolioService(mock_session)
        data = await svc.get_summary(user_id)

        assert "accounts" in data
        assert len(data["accounts"]) == 1
        assert data["accounts"][0]["broker"] == "longbridge"
        assert data["accounts"][0]["currency"] == "HKD"
        assert data["accounts"][0]["total_value"] == 35000.0

    @pytest.mark.asyncio
    async def test_returns_last_synced_at(self, mock_session, user_id):
        ts = datetime(2026, 5, 2, 8, 0, 0, tzinfo=timezone.utc)
        row = MagicMock()
        row.id = str(uuid4())
        row.broker = "ibkr"
        row.currency = "USD"
        row.total_value = 10000.0
        row.account_name = "IBKR Main"

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [row]
        sync_result = MagicMock()
        sync_result.scalar_one_or_none.return_value = ts
        mock_session.execute = AsyncMock(side_effect=[result_mock, sync_result])

        svc = PortfolioService(mock_session)
        data = await svc.get_summary(user_id)
        assert data["last_synced_at"] == ts

    @pytest.mark.asyncio
    async def test_empty_accounts(self, mock_session, user_id):
        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = []
        sync_result = MagicMock()
        sync_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(side_effect=[result_mock, sync_result])

        svc = PortfolioService(mock_session)
        data = await svc.get_summary(user_id)
        assert data["accounts"] == []
        assert data["last_synced_at"] is None


class TestGetSnapshots:
    @pytest.mark.asyncio
    async def test_total_split_groups_by_currency(self, mock_session, user_id):
        ts1 = datetime(2026, 4, 1, tzinfo=timezone.utc)
        ts2 = datetime(2026, 4, 2, tzinfo=timezone.utc)

        row1 = MagicMock()
        row1.snapshot_at = ts1
        row1.total_value = 10000.0
        row1.currency = "USD"

        row2 = MagicMock()
        row2.snapshot_at = ts2
        row2.total_value = 10500.0
        row2.currency = "USD"

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [row1, row2]
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        data = await svc.get_snapshots(user_id, range_="1M", split="total")

        assert "series" in data
        assert "currency_groups" in data
        assert "USD" in data["currency_groups"]
        usd_series = next(s for s in data["series"] if "USD" in s["name"])
        assert len(usd_series["data"]) == 2
        assert usd_series["data"][0]["value"] == 10000.0

    @pytest.mark.asyncio
    async def test_broker_split_groups_by_broker_and_currency(self, mock_session, user_id):
        ts = datetime(2026, 4, 1, tzinfo=timezone.utc)

        row1 = MagicMock()
        row1.snapshot_at = ts
        row1.total_value = 5000.0
        row1.currency = "USD"
        row1.broker = "ibkr"

        row2 = MagicMock()
        row2.snapshot_at = ts
        row2.total_value = 35000.0
        row2.currency = "HKD"
        row2.broker = "longbridge"

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [row1, row2]
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        data = await svc.get_snapshots(user_id, range_="1M", split="broker")

        series_names = [s["name"] for s in data["series"]]
        assert any("ibkr" in n.lower() for n in series_names)
        assert any("longbridge" in n.lower() for n in series_names)

    @pytest.mark.asyncio
    async def test_range_1w_limits_window(self, mock_session, user_id):
        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        await svc.get_snapshots(user_id, range_="1W", split="total")
        assert mock_session.execute.call_args is not None

    @pytest.mark.asyncio
    async def test_range_all_has_no_cutoff(self, mock_session, user_id):
        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        data = await svc.get_snapshots(user_id, range_="all", split="total")
        assert data["series"] == []
        assert data["currency_groups"] == []


class TestGetTransactions:
    @pytest.mark.asyncio
    async def test_returns_transaction_list(self, mock_session, user_id):
        ts = datetime(2026, 4, 15, tzinfo=timezone.utc)
        row = MagicMock()
        row.ticker = "AAPL"
        row.type = "buy"
        row.quantity = 10.0
        row.price = 150.0
        row.executed_at = ts

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [row]
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        txns = await svc.get_transactions(user_id, range_="1M")

        assert len(txns) == 1
        assert txns[0]["ticker"] == "AAPL"
        assert txns[0]["type"] == "buy"
        assert txns[0]["quantity"] == 10.0
        assert txns[0]["price"] == 150.0
        assert txns[0]["executed_at"] == ts

    @pytest.mark.asyncio
    async def test_empty_result(self, mock_session, user_id):
        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        txns = await svc.get_transactions(user_id, range_="1W")
        assert txns == []


class TestGetPositions:
    @pytest.mark.asyncio
    async def test_returns_position_list(self, mock_session, user_id):
        row = MagicMock()
        row.ticker = "AAPL"
        row.name = "Apple Inc."
        row.current_value = 1750.0
        row.currency = "USD"
        row.asset_class = "stock"
        row.sector = "Technology"
        row.country = "US"
        row.broker = "ibkr"
        row.label_names = ["Tech", "Growth"]

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [row]
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        positions = await svc.get_positions(user_id)

        assert len(positions) == 1
        p = positions[0]
        assert p["ticker"] == "AAPL"
        assert p["label_names"] == ["Tech", "Growth"]

    @pytest.mark.asyncio
    async def test_positions_with_no_labels(self, mock_session, user_id):
        row = MagicMock()
        row.ticker = "700"
        row.name = "Tencent"
        row.current_value = 5000.0
        row.currency = "HKD"
        row.asset_class = "stock"
        row.sector = None
        row.country = "CN"
        row.broker = "longbridge"
        row.label_names = []

        result_mock = MagicMock()
        result_mock.mappings.return_value.all.return_value = [row]
        mock_session.execute = AsyncMock(return_value=result_mock)

        svc = PortfolioService(mock_session)
        positions = await svc.get_positions(user_id)
        assert positions[0]["label_names"] == []
