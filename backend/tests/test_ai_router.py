import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.auth import get_current_user_email
from app.database import get_session

TEST_EMAIL = "test@example.com"
TEST_USER_ID = "user-uuid-1234"


def override_auth():
    return TEST_EMAIL


def make_session_with_user_and_settings(user_mock, settings_mock):
    """Creates a mock session where first execute → user, second execute → settings."""
    async def override_session():
        session = AsyncMock()

        user_result = MagicMock()
        user_result.scalars.return_value.first.return_value = user_mock

        settings_result = MagicMock()
        settings_result.scalars.return_value.first.return_value = settings_mock

        session.execute.side_effect = [user_result, settings_result]
        session.commit = AsyncMock()
        session.add = MagicMock()
        yield session
    return override_session


@pytest.fixture
def mock_user():
    u = MagicMock()
    u.id = TEST_USER_ID
    u.email = TEST_EMAIL
    return u


class TestGetAISettings:
    @pytest.mark.asyncio
    async def test_not_configured(self, mock_user):
        app.dependency_overrides[get_current_user_email] = override_auth
        app.dependency_overrides[get_session] = make_session_with_user_and_settings(mock_user, None)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/ai/settings")

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json() == {"configured": False}

    @pytest.mark.asyncio
    async def test_configured(self, mock_user):
        settings = MagicMock()
        settings.provider = "anthropic"
        settings.model = "claude-sonnet-4-6"

        app.dependency_overrides[get_current_user_email] = override_auth
        app.dependency_overrides[get_session] = make_session_with_user_and_settings(mock_user, settings)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.get("/ai/settings")

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is True
        assert data["provider"] == "anthropic"
        assert data["model"] == "claude-sonnet-4-6"
        assert "api_key" not in data


class TestPostAISettings:
    @pytest.mark.asyncio
    async def test_creates_new(self, mock_user):
        app.dependency_overrides[get_current_user_email] = override_auth
        app.dependency_overrides[get_session] = make_session_with_user_and_settings(mock_user, None)

        with patch("app.routers.ai.encrypt", return_value="encrypted-key"):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post(
                    "/ai/settings",
                    json={"provider": "anthropic", "api_key": "sk-ant-test", "model": "claude-sonnet-4-6"},
                )

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert data["configured"] is True
        assert data["provider"] == "anthropic"
        assert "api_key" not in data

    @pytest.mark.asyncio
    async def test_invalid_provider_returns_422(self):
        app.dependency_overrides[get_current_user_email] = override_auth

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/ai/settings",
                json={"provider": "badprovider", "api_key": "sk-test", "model": "gpt-4o"},
            )

        app.dependency_overrides.clear()
        assert resp.status_code == 422


class TestPostAITest:
    @pytest.mark.asyncio
    async def test_no_settings_returns_error(self, mock_user):
        app.dependency_overrides[get_current_user_email] = override_auth
        app.dependency_overrides[get_session] = make_session_with_user_and_settings(mock_user, None)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/ai/test")

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "not configured" in data["error"].lower()

    @pytest.mark.asyncio
    async def test_success_anthropic(self, mock_user):
        settings = MagicMock()
        settings.provider = "anthropic"
        settings.model = "claude-sonnet-4-6"
        settings.api_key = "encrypted-key"

        app.dependency_overrides[get_current_user_email] = override_auth
        app.dependency_overrides[get_session] = make_session_with_user_and_settings(mock_user, settings)

        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(text="OK")]

        with patch("app.routers.ai.decrypt", return_value="sk-real"), \
             patch("app.routers.ai.anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_msg
            mock_cls.return_value = mock_client

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post("/ai/test")

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        assert resp.json() == {"success": True}

    @pytest.mark.asyncio
    async def test_invalid_key_anthropic(self, mock_user):
        import anthropic as anthropic_sdk

        settings = MagicMock()
        settings.provider = "anthropic"
        settings.model = "claude-sonnet-4-6"
        settings.api_key = "encrypted-bad"

        app.dependency_overrides[get_current_user_email] = override_auth
        app.dependency_overrides[get_session] = make_session_with_user_and_settings(mock_user, settings)

        with patch("app.routers.ai.decrypt", return_value="sk-bad"), \
             patch("app.routers.ai.anthropic.Anthropic") as mock_cls:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = anthropic_sdk.AuthenticationError(
                message="invalid api key",
                response=MagicMock(status_code=401),
                body={},
            )
            mock_cls.return_value = mock_client

            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
                resp = await ac.post("/ai/test")

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "invalid api key" in data["error"].lower()
