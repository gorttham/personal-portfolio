import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4
from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import get_current_user_email
from app.database import get_session


TEST_EMAIL = "test@example.com"
TEST_USER_ID = str(uuid4())


def override_auth():
    return TEST_EMAIL


def override_get_session():
    session = AsyncMock()
    user_result = MagicMock()
    user_result.scalar_one.return_value = TEST_USER_ID
    session.execute = AsyncMock(return_value=user_result)
    yield session


@pytest.fixture
def client():
    app.dependency_overrides[get_current_user_email] = override_auth
    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def mock_summary():
    return {
        "accounts": [{"id": str(uuid4()), "broker": "ibkr", "currency": "USD", "total_value": 10000.0, "account_name": "IBKR Main"}],
        "last_synced_at": datetime(2026, 5, 2, 8, 0, 0, tzinfo=timezone.utc),
    }


@pytest.fixture
def mock_snapshots():
    return {
        "series": [{"name": "Total USD", "data": [{"timestamp": datetime(2026, 4, 1, tzinfo=timezone.utc), "value": 9000.0}]}],
        "currency_groups": ["USD"],
    }


@pytest.fixture
def mock_transactions():
    return [{"ticker": "AAPL", "type": "buy", "quantity": 10.0, "price": 150.0, "executed_at": datetime(2026, 4, 15, tzinfo=timezone.utc)}]


@pytest.fixture
def mock_positions():
    return [{"ticker": "AAPL", "name": "Apple Inc.", "quantity": 10.0, "avg_cost": 150.0, "current_price": 175.0, "current_value": 1750.0, "unrealized_gain": 250.0, "unrealized_gain_pct": 16.666666666666668, "currency": "USD", "asset_class": "stock", "sector": "Technology", "country": "US", "broker": "ibkr", "label_names": ["Tech"]}]


class TestPortfolioSummaryEndpoint:
    def test_get_summary_returns_200(self, client, mock_summary):
        with patch("app.routers.portfolio.PortfolioService.get_summary", new_callable=AsyncMock, return_value=mock_summary):
            response = client.get("/portfolio/summary")
        assert response.status_code == 200
        body = response.json()
        assert "accounts" in body
        assert body["accounts"][0]["broker"] == "ibkr"

    def test_get_summary_requires_auth(self):
        with TestClient(app) as c:
            response = c.get("/portfolio/summary")
        assert response.status_code == 401

    def test_get_summary_empty_accounts(self, client):
        with patch("app.routers.portfolio.PortfolioService.get_summary", new_callable=AsyncMock, return_value={"accounts": [], "last_synced_at": None}):
            response = client.get("/portfolio/summary")
        assert response.status_code == 200
        assert response.json()["accounts"] == []


class TestPortfolioSnapshotsEndpoint:
    def test_get_snapshots_defaults(self, client, mock_snapshots):
        with patch("app.routers.portfolio.PortfolioService.get_snapshots", new_callable=AsyncMock, return_value=mock_snapshots):
            response = client.get("/portfolio/snapshots")
        assert response.status_code == 200
        body = response.json()
        assert "series" in body
        assert "currency_groups" in body

    def test_get_snapshots_accepts_range_and_split_params(self, client, mock_snapshots):
        with patch("app.routers.portfolio.PortfolioService.get_snapshots", new_callable=AsyncMock, return_value=mock_snapshots):
            response = client.get("/portfolio/snapshots?range=3M&split=broker")
        assert response.status_code == 200

    def test_get_snapshots_invalid_range_returns_422(self, client):
        response = client.get("/portfolio/snapshots?range=BADRANGE")
        assert response.status_code == 422

    def test_get_snapshots_invalid_split_returns_422(self, client):
        response = client.get("/portfolio/snapshots?split=badsplit")
        assert response.status_code == 422


class TestPortfolioTransactionsEndpoint:
    def test_get_transactions_returns_list(self, client, mock_transactions):
        with patch("app.routers.portfolio.PortfolioService.get_transactions", new_callable=AsyncMock, return_value=mock_transactions):
            response = client.get("/portfolio/transactions")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert body[0]["ticker"] == "AAPL"
        assert body[0]["type"] == "buy"

    def test_get_transactions_accepts_range_param(self, client, mock_transactions):
        with patch("app.routers.portfolio.PortfolioService.get_transactions", new_callable=AsyncMock, return_value=mock_transactions):
            response = client.get("/portfolio/transactions?range=1W")
        assert response.status_code == 200


class TestPortfolioPositionsEndpoint:
    def test_get_positions_returns_list(self, client, mock_positions):
        with patch("app.routers.portfolio.PortfolioService.get_positions", new_callable=AsyncMock, return_value=mock_positions):
            response = client.get("/portfolio/positions")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert body[0]["ticker"] == "AAPL"
        assert body[0]["label_names"] == ["Tech"]

    def test_get_positions_empty(self, client):
        with patch("app.routers.portfolio.PortfolioService.get_positions", new_callable=AsyncMock, return_value=[]):
            response = client.get("/portfolio/positions")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_positions_includes_pnl_fields(self, client, mock_positions):
        with patch("app.routers.portfolio.PortfolioService.get_positions", new_callable=AsyncMock, return_value=mock_positions):
            response = client.get("/portfolio/positions")
        assert response.status_code == 200
        body = response.json()
        assert "unrealized_gain_pct" in body[0]
