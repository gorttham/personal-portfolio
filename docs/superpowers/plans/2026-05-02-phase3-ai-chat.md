# Phase 3: AI Chat Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an AI-powered chat panel to the dashboard that lets users ask natural-language questions about their portfolio, backed by a streaming FastAPI endpoint that injects live portfolio context into every prompt.

**Architecture:** A collapsible right-side drawer on the dashboard communicates with a stateless `/ai/chat` SSE endpoint; the backend rebuilds full portfolio context from the database on every request and streams tokens back via Server-Sent Events. Users store their own Anthropic or OpenAI API key (encrypted at rest) and configure it through a dedicated `/settings/ai` page.

**Tech Stack:** Next.js 14 App Router, TypeScript, Tailwind CSS, shadcn/ui (frontend) · FastAPI, SQLAlchemy 2.0 async, `anthropic` >= 0.40.0, `openai` Python SDK, `StreamingResponse` (backend) · Neon PostgreSQL (database)

---

## Task 1: Add AI SDK Dependencies to Backend

**Files:**
- Edit: `backend/requirements.txt`

- [ ] **Step 1: Add `anthropic` and `openai` to `backend/requirements.txt`**

Open `backend/requirements.txt` and append the two lines below. Place them after the existing entries:

```
anthropic==0.40.0
openai==1.51.0
```

- [ ] **Step 2: Install and verify**

```bash
cd backend
pip install anthropic==0.40.0 openai==1.51.0
python -c "import anthropic; import openai; print('OK')"
```
Expected output:
```
OK
```

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add anthropic and openai SDK dependencies"
```

---

## Task 2: AI Service — Context Builder

**Files:**
- Create: `backend/app/services/ai.py`
- Create: `backend/tests/test_ai_service.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_ai_service.py`:

```python
import pytest
from unittest.mock import MagicMock
from datetime import date, datetime, timezone
from app.services.ai import build_portfolio_context, build_system_prompt


def make_position(ticker, name, quantity, current_price, currency, avg_cost=None):
    p = MagicMock()
    p.ticker = ticker
    p.name = name
    p.quantity = quantity
    p.current_price = current_price
    p.currency = currency
    p.avg_cost = avg_cost
    return p


def make_transaction(ticker, action, quantity, price, date_):
    t = MagicMock()
    t.ticker = ticker
    t.action = action
    t.quantity = quantity
    t.price = price
    t.date = date_
    return t


def make_label(name, tickers):
    lbl = MagicMock()
    lbl.name = name
    lbl.tickers = tickers
    return lbl


def test_build_portfolio_context_includes_positions():
    positions = [
        make_position("AAPL", "Apple Inc.", 10, 180.0, "USD", avg_cost=150.0),
        make_position("TSLA", "Tesla Inc.", 5, 200.0, "USD"),
    ]
    ctx = build_portfolio_context(positions=positions, transactions=[], labels=[])
    assert "AAPL" in ctx
    assert "Apple Inc." in ctx
    assert "TSLA" in ctx
    assert "Tesla Inc." in ctx


def test_build_portfolio_context_calculates_pct_of_total():
    positions = [
        make_position("AAPL", "Apple Inc.", 10, 100.0, "USD"),
        make_position("GOOG", "Alphabet Inc.", 5, 100.0, "USD"),
    ]
    # AAPL = 1000, GOOG = 500, total = 1500
    # AAPL = 66.67%, GOOG = 33.33%
    ctx = build_portfolio_context(positions=positions, transactions=[], labels=[])
    assert "66.7" in ctx
    assert "33.3" in ctx


def test_build_portfolio_context_shows_gain_loss_when_avg_cost_present():
    positions = [
        make_position("AAPL", "Apple Inc.", 10, 180.0, "USD", avg_cost=150.0),
    ]
    ctx = build_portfolio_context(positions=positions, transactions=[], labels=[])
    # gain = (180 - 150) / 150 * 100 = 20.0%
    assert "+20.0%" in ctx


def test_build_portfolio_context_no_gain_loss_without_avg_cost():
    positions = [
        make_position("AAPL", "Apple Inc.", 10, 180.0, "USD", avg_cost=None),
    ]
    ctx = build_portfolio_context(positions=positions, transactions=[], labels=[])
    assert "n/a" in ctx.lower() or "N/A" in ctx


def test_build_portfolio_context_includes_transactions():
    txns = [
        make_transaction("AAPL", "buy", 5, 170.0, date(2026, 4, 15)),
        make_transaction("TSLA", "sell", 2, 210.0, date(2026, 4, 20)),
    ]
    ctx = build_portfolio_context(positions=[], transactions=txns, labels=[])
    assert "AAPL" in ctx
    assert "buy" in ctx
    assert "TSLA" in ctx
    assert "sell" in ctx


def test_build_portfolio_context_includes_labels():
    labels = [make_label("Tech", ["AAPL", "GOOG"]), make_label("EV", ["TSLA"])]
    ctx = build_portfolio_context(positions=[], transactions=[], labels=labels)
    assert "Tech" in ctx
    assert "AAPL" in ctx
    assert "GOOG" in ctx
    assert "EV" in ctx
    assert "TSLA" in ctx


def test_build_portfolio_context_empty_portfolio():
    ctx = build_portfolio_context(positions=[], transactions=[], labels=[])
    assert "No positions" in ctx or "none" in ctx.lower()


def test_build_system_prompt_contains_static_preamble():
    ctx = "POSITIONS: none"
    prompt = build_system_prompt(ctx)
    assert "portfolio analyst" in prompt.lower()
    assert "financial advice" in prompt.lower()


def test_build_system_prompt_embeds_context():
    ctx = "POSITIONS: AAPL | Apple | $1800 | USD"
    prompt = build_system_prompt(ctx)
    assert ctx in prompt
```

- [ ] **Step 2: Run failing tests**

```bash
cd backend
pytest tests/test_ai_service.py -v
```
Expected: All tests FAIL with `ImportError: cannot import name 'build_portfolio_context'`

- [ ] **Step 3: Create `backend/app/services/ai.py`**

```python
from __future__ import annotations

from datetime import date
from typing import Any


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def build_portfolio_context(
    positions: list[Any],
    transactions: list[Any],
    labels: list[Any],
) -> str:
    lines: list[str] = []

    # --- Positions ---
    lines.append("Positions:")
    if not positions:
        lines.append("  No positions found.")
    else:
        total_value = sum(
            float(p.quantity) * float(p.current_price) for p in positions
        )
        for p in positions:
            value = float(p.quantity) * float(p.current_price)
            pct = (value / total_value * 100) if total_value else 0.0
            if p.avg_cost is not None:
                gain_pct = (float(p.current_price) - float(p.avg_cost)) / float(p.avg_cost) * 100
                gain_str = f"{gain_pct:+.1f}%"
            else:
                gain_str = "N/A"
            lines.append(
                f"  {p.ticker} | {p.name} | "
                f"{p.currency} {value:,.2f} | {pct:.1f}% of total | gain/loss: {gain_str}"
            )

    lines.append("")

    # --- Transactions ---
    lines.append("Recent transactions (last 30 days):")
    if not transactions:
        lines.append("  No recent transactions.")
    else:
        for t in transactions:
            txn_date = t.date.isoformat() if hasattr(t.date, "isoformat") else str(t.date)
            lines.append(
                f"  {txn_date} | {t.ticker} | {t.action} | "
                f"qty {t.quantity} | price {t.price}"
            )

    lines.append("")

    # --- Labels ---
    lines.append("Label groups:")
    if not labels:
        lines.append("  No label groups defined.")
    else:
        for lbl in labels:
            tickers_str = ", ".join(lbl.tickers) if lbl.tickers else "none"
            lines.append(f"  {lbl.name}: {tickers_str}")

    return "\n".join(lines)


def build_system_prompt(portfolio_context: str) -> str:
    return (
        "You are a portfolio analyst assistant. "
        "Answer questions about the user's holdings, performance, and allocation. "
        "Do not suggest specific trades or provide financial advice.\n\n"
        "PORTFOLIO CONTEXT\n"
        "================\n"
        + portfolio_context
    )
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
cd backend
pytest tests/test_ai_service.py -v
```
Expected:
```
tests/test_ai_service.py::test_build_portfolio_context_includes_positions PASSED
tests/test_ai_service.py::test_build_portfolio_context_calculates_pct_of_total PASSED
tests/test_ai_service.py::test_build_portfolio_context_shows_gain_loss_when_avg_cost_present PASSED
tests/test_ai_service.py::test_build_portfolio_context_no_gain_loss_without_avg_cost PASSED
tests/test_ai_service.py::test_build_portfolio_context_includes_transactions PASSED
tests/test_ai_service.py::test_build_portfolio_context_includes_labels PASSED
tests/test_ai_service.py::test_build_portfolio_context_empty_portfolio PASSED
tests/test_ai_service.py::test_build_system_prompt_contains_static_preamble PASSED
tests/test_ai_service.py::test_build_system_prompt_embeds_context PASSED
9 passed in 0.XXs
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/ai.py backend/tests/test_ai_service.py
git commit -m "feat: AI context builder and system prompt assembly"
```

---

## Task 3: AI Router — Settings and Test Endpoints

**Files:**
- Create: `backend/app/routers/ai.py`
- Create: `backend/tests/test_ai_router.py`
- Edit: `backend/app/main.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/test_ai_router.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock, patch
from app.main import app
from app.services.auth import get_current_user_email
from app.database import get_session


TEST_EMAIL = "test@example.com"


def override_auth():
    return TEST_EMAIL


@pytest.fixture
def mock_user():
    u = MagicMock()
    u.id = "user-uuid-1234"
    u.email = TEST_EMAIL
    return u


@pytest.fixture
def client_with_auth(mock_user):
    async def override_session():
        session = AsyncMock()
        # scalars().first() pattern
        result_mock = MagicMock()
        result_mock.first.return_value = mock_user
        session.execute.return_value = MagicMock(scalars=MagicMock(return_value=result_mock))
        yield session

    app.dependency_overrides[get_current_user_email] = override_auth
    app.dependency_overrides[get_session] = override_session
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_ai_settings_not_configured(client_with_auth, mock_user):
    async def override_session():
        session = AsyncMock()
        # No UserAISettings row found
        result_mock = MagicMock()
        result_mock.first.return_value = None
        # user lookup returns mock_user
        user_result = MagicMock()
        user_result.first.return_value = mock_user
        session.execute.side_effect = [
            MagicMock(scalars=MagicMock(return_value=user_result)),
            MagicMock(scalars=MagicMock(return_value=result_mock)),
        ]
        yield session

    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/ai/settings")
    assert resp.status_code == 200
    assert resp.json() == {"configured": False}


@pytest.mark.asyncio
async def test_get_ai_settings_configured(client_with_auth, mock_user):
    settings_row = MagicMock()
    settings_row.provider = "anthropic"
    settings_row.model = "claude-sonnet-4-6"

    async def override_session():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.first.return_value = mock_user
        settings_result = MagicMock()
        settings_result.first.return_value = settings_row
        session.execute.side_effect = [
            MagicMock(scalars=MagicMock(return_value=user_result)),
            MagicMock(scalars=MagicMock(return_value=settings_result)),
        ]
        yield session

    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/ai/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is True
    assert data["provider"] == "anthropic"
    assert data["model"] == "claude-sonnet-4-6"
    assert "api_key" not in data


@pytest.mark.asyncio
async def test_post_ai_settings_creates_new(client_with_auth, mock_user):
    async def override_session():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.first.return_value = mock_user
        no_settings = MagicMock()
        no_settings.first.return_value = None
        session.execute.side_effect = [
            MagicMock(scalars=MagicMock(return_value=user_result)),
            MagicMock(scalars=MagicMock(return_value=no_settings)),
        ]
        yield session

    app.dependency_overrides[get_session] = override_session

    with patch("app.routers.ai.encrypt", return_value="encrypted-key"):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post(
                "/ai/settings",
                json={"provider": "anthropic", "api_key": "sk-ant-test", "model": "claude-sonnet-4-6"},
            )
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is True
    assert data["provider"] == "anthropic"
    assert data["model"] == "claude-sonnet-4-6"
    assert "api_key" not in data


@pytest.mark.asyncio
async def test_post_ai_settings_invalid_provider(client_with_auth):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post(
            "/ai/settings",
            json={"provider": "invalidprovider", "api_key": "sk-test", "model": "gpt-4o"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_post_ai_test_success_anthropic(client_with_auth, mock_user):
    settings_row = MagicMock()
    settings_row.provider = "anthropic"
    settings_row.model = "claude-sonnet-4-6"
    settings_row.api_key = "encrypted-key"

    async def override_session():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.first.return_value = mock_user
        settings_result = MagicMock()
        settings_result.first.return_value = settings_row
        session.execute.side_effect = [
            MagicMock(scalars=MagicMock(return_value=user_result)),
            MagicMock(scalars=MagicMock(return_value=settings_result)),
        ]
        yield session

    app.dependency_overrides[get_session] = override_session

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="OK")]

    with patch("app.routers.ai.decrypt", return_value="sk-ant-real"), \
         patch("app.routers.ai.anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message
        mock_anthropic.return_value = mock_client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/ai/test")

    assert resp.status_code == 200
    assert resp.json() == {"success": True}


@pytest.mark.asyncio
async def test_post_ai_test_no_settings(client_with_auth, mock_user):
    async def override_session():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.first.return_value = mock_user
        no_settings = MagicMock()
        no_settings.first.return_value = None
        session.execute.side_effect = [
            MagicMock(scalars=MagicMock(return_value=user_result)),
            MagicMock(scalars=MagicMock(return_value=no_settings)),
        ]
        yield session

    app.dependency_overrides[get_session] = override_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.post("/ai/test")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "not configured" in data["error"].lower()


@pytest.mark.asyncio
async def test_post_ai_test_invalid_key_anthropic(client_with_auth, mock_user):
    settings_row = MagicMock()
    settings_row.provider = "anthropic"
    settings_row.model = "claude-sonnet-4-6"
    settings_row.api_key = "encrypted-bad-key"

    async def override_session():
        session = AsyncMock()
        user_result = MagicMock()
        user_result.first.return_value = mock_user
        settings_result = MagicMock()
        settings_result.first.return_value = settings_row
        session.execute.side_effect = [
            MagicMock(scalars=MagicMock(return_value=user_result)),
            MagicMock(scalars=MagicMock(return_value=settings_result)),
        ]
        yield session

    app.dependency_overrides[get_session] = override_session

    import anthropic as anthropic_sdk

    with patch("app.routers.ai.decrypt", return_value="sk-bad"), \
         patch("app.routers.ai.anthropic.Anthropic") as mock_anthropic:
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = anthropic_sdk.AuthenticationError(
            message="invalid api key",
            response=MagicMock(status_code=401),
            body={},
        )
        mock_anthropic.return_value = mock_client

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            resp = await ac.post("/ai/test")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert "invalid api key" in data["error"].lower()
```

- [ ] **Step 2: Run failing tests**

```bash
cd backend
pytest tests/test_ai_router.py -v
```
Expected: All tests FAIL with `ImportError` or `404 Not Found` because the router does not exist yet.

- [ ] **Step 3: Create `backend/app/routers/ai.py`**

```python
from __future__ import annotations

import json
from typing import AsyncGenerator, Literal

import anthropic
import openai
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.tables import User, UserAISettings, Position, Transaction, AssetLabel, AssetLabelAssignment
from app.services.auth import get_current_user_email
from app.services.encryption import encrypt, decrypt
from app.services.ai import build_portfolio_context, build_system_prompt

router = APIRouter()

VALID_PROVIDERS = {"anthropic", "openai"}
VALID_MODELS = {
    "anthropic": ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"],
    "openai": ["gpt-4o", "gpt-4o-mini"],
}


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AISettingsRequest(BaseModel):
    provider: Literal["anthropic", "openai"]
    api_key: str
    model: str

    @field_validator("model")
    @classmethod
    def validate_model(cls, v: str, info) -> str:
        provider = info.data.get("provider")
        if provider and v not in VALID_MODELS.get(provider, []):
            raise ValueError(f"Model '{v}' is not valid for provider '{provider}'")
        return v


class ChatRequest(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_user(email: str, session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def _get_ai_settings(user_id: str, session: AsyncSession) -> UserAISettings | None:
    result = await session.execute(
        select(UserAISettings).where(UserAISettings.user_id == user_id)
    )
    return result.scalars().first()


# ---------------------------------------------------------------------------
# GET /ai/settings
# ---------------------------------------------------------------------------

@router.get("/settings")
async def get_ai_settings(
    email: str = Depends(get_current_user_email),
    session: AsyncSession = Depends(get_session),
):
    user = await _get_user(email, session)
    settings = await _get_ai_settings(user.id, session)
    if not settings:
        return {"configured": False}
    return {
        "configured": True,
        "provider": settings.provider,
        "model": settings.model,
    }


# ---------------------------------------------------------------------------
# POST /ai/settings
# ---------------------------------------------------------------------------

@router.post("/settings")
async def save_ai_settings(
    body: AISettingsRequest,
    email: str = Depends(get_current_user_email),
    session: AsyncSession = Depends(get_session),
):
    user = await _get_user(email, session)
    settings = await _get_ai_settings(user.id, session)

    encrypted_key = encrypt(body.api_key)

    if settings:
        settings.provider = body.provider
        settings.api_key = encrypted_key
        settings.model = body.model
    else:
        settings = UserAISettings(
            user_id=user.id,
            provider=body.provider,
            api_key=encrypted_key,
            model=body.model,
        )
        session.add(settings)

    await session.commit()

    return {
        "configured": True,
        "provider": body.provider,
        "model": body.model,
    }


# ---------------------------------------------------------------------------
# POST /ai/test
# ---------------------------------------------------------------------------

@router.post("/test")
async def test_ai_connection(
    email: str = Depends(get_current_user_email),
    session: AsyncSession = Depends(get_session),
):
    user = await _get_user(email, session)
    settings = await _get_ai_settings(user.id, session)

    if not settings:
        return {"success": False, "error": "AI not configured. Please add your API key in Settings."}

    raw_key = decrypt(settings.api_key)

    try:
        if settings.provider == "anthropic":
            client = anthropic.Anthropic(api_key=raw_key)
            client.messages.create(
                model=settings.model,
                max_tokens=5,
                messages=[{"role": "user", "content": "Say OK"}],
            )
        else:
            client = openai.OpenAI(api_key=raw_key)
            client.chat.completions.create(
                model=settings.model,
                max_tokens=5,
                messages=[{"role": "user", "content": "Say OK"}],
            )
        return {"success": True}

    except (anthropic.AuthenticationError, openai.AuthenticationError) as exc:
        return {"success": False, "error": f"Invalid API key: {exc}"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# POST /ai/chat  (SSE streaming)
# ---------------------------------------------------------------------------

async def _stream_anthropic(client: anthropic.Anthropic, model: str, system: str, message: str) -> AsyncGenerator[str, None]:
    with client.messages.stream(
        model=model,
        max_tokens=1024,
        system=system,
        messages=[{"role": "user", "content": message}],
    ) as stream:
        for text in stream.text_stream:
            yield f"data: {json.dumps({'token': text})}\n\n"
    yield f"data: {json.dumps({'done': True})}\n\n"


async def _stream_openai(client: openai.OpenAI, model: str, system: str, message: str) -> AsyncGenerator[str, None]:
    stream = client.chat.completions.create(
        model=model,
        max_tokens=1024,
        stream=True,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": message},
        ],
    )
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield f"data: {json.dumps({'token': delta.content})}\n\n"
    yield f"data: {json.dumps({'done': True})}\n\n"


@router.post("/chat")
async def chat(
    body: ChatRequest,
    email: str = Depends(get_current_user_email),
    session: AsyncSession = Depends(get_session),
):
    user = await _get_user(email, session)
    settings = await _get_ai_settings(user.id, session)

    if not settings:
        raise HTTPException(status_code=400, detail="AI not configured")

    # --- Load portfolio context ---
    pos_result = await session.execute(
        select(Position).where(Position.user_id == user.id)
    )
    positions = pos_result.scalars().all()

    from datetime import datetime, timedelta, timezone
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    txn_result = await session.execute(
        select(Transaction).where(
            Transaction.user_id == user.id,
            Transaction.date >= thirty_days_ago,
        )
    )
    transactions = txn_result.scalars().all()

    # Build label groups: {label_name: [ticker, ...]}
    label_result = await session.execute(
        select(AssetLabel).where(AssetLabel.user_id == user.id)
    )
    raw_labels = label_result.scalars().all()

    class _LabelGroup:
        def __init__(self, name: str, tickers: list[str]):
            self.name = name
            self.tickers = tickers

    label_groups: list[_LabelGroup] = []
    for lbl in raw_labels:
        assign_result = await session.execute(
            select(AssetLabelAssignment).where(AssetLabelAssignment.label_id == lbl.id)
        )
        assignments = assign_result.scalars().all()
        label_groups.append(_LabelGroup(lbl.name, [a.ticker for a in assignments]))

    context = build_portfolio_context(
        positions=list(positions),
        transactions=list(transactions),
        labels=label_groups,
    )
    system_prompt = build_system_prompt(context)

    raw_key = decrypt(settings.api_key)

    if settings.provider == "anthropic":
        client = anthropic.Anthropic(api_key=raw_key)
        generator = _stream_anthropic(client, settings.model, system_prompt, body.message)
    else:
        client = openai.OpenAI(api_key=raw_key)
        generator = _stream_openai(client, settings.model, system_prompt, body.message)

    return StreamingResponse(generator, media_type="text/event-stream")
```

- [ ] **Step 4: Register the router in `backend/app/main.py`**

In `backend/app/main.py`, add the import and `include_router` call. The existing file looks like:

```python
from app.routers import auth, brokerages, sync
```

Change it to:

```python
from app.routers import auth, brokerages, sync, ai as ai_router
```

And add after the existing `include_router` calls:

```python
app.include_router(ai_router.router, prefix="/ai", tags=["ai"])
```

- [ ] **Step 5: Run tests — expect all pass**

```bash
cd backend
pytest tests/test_ai_router.py -v
```
Expected:
```
tests/test_ai_router.py::test_get_ai_settings_not_configured PASSED
tests/test_ai_router.py::test_get_ai_settings_configured PASSED
tests/test_ai_router.py::test_post_ai_settings_creates_new PASSED
tests/test_ai_router.py::test_post_ai_settings_invalid_provider PASSED
tests/test_ai_router.py::test_post_ai_test_success_anthropic PASSED
tests/test_ai_router.py::test_post_ai_test_no_settings PASSED
tests/test_ai_router.py::test_post_ai_test_invalid_key_anthropic PASSED
7 passed in 0.XXs
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/ai.py backend/app/main.py backend/tests/test_ai_router.py
git commit -m "feat: AI settings, test-connection, and streaming chat endpoints"
```

---

## Task 4: AI Settings Page

**Files:**
- Create: `frontend/app/settings/ai/page.tsx`

- [ ] **Step 1: Create the directory**

```bash
mkdir -p frontend/app/settings/ai
```

- [ ] **Step 2: Create `frontend/app/settings/ai/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";

const MODELS: Record<string, string[]> = {
  anthropic: ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5-20251001"],
  openai: ["gpt-4o", "gpt-4o-mini"],
};

type Status = "idle" | "saving" | "testing" | "saved" | "error";

export default function AISettingsPage() {
  const { data: session } = useSession();
  const router = useRouter();

  const [provider, setProvider] = useState<"anthropic" | "openai">("anthropic");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState(MODELS.anthropic[0]);
  const [isConfigured, setIsConfigured] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [message, setMessage] = useState("");
  const [testResult, setTestResult] = useState<{ success: boolean; error?: string } | null>(null);

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

  useEffect(() => {
    if (!session?.backendToken) return;
    fetch(`${backendUrl}/ai/settings`, {
      headers: { Authorization: `Bearer ${session.backendToken}` },
    })
      .then((r) => r.json())
      .then((data) => {
        if (data.configured) {
          setIsConfigured(true);
          setProvider(data.provider);
          setModel(data.model);
        }
      })
      .catch(() => {});
  }, [session, backendUrl]);

  // When provider changes, reset model to first valid option
  const handleProviderChange = (val: "anthropic" | "openai") => {
    setProvider(val);
    setModel(MODELS[val][0]);
    setTestResult(null);
  };

  const handleSave = async () => {
    if (!apiKey && !isConfigured) {
      setMessage("Please enter an API key.");
      setStatus("error");
      return;
    }
    setStatus("saving");
    setMessage("");
    try {
      const body: Record<string, string> = { provider, model };
      if (apiKey) body.api_key = apiKey;
      else body.api_key = "__KEEP__"; // placeholder; backend ignores this sentinel

      const res = await fetch(`${backendUrl}/ai/settings`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${session?.backendToken}`,
        },
        body: JSON.stringify({ provider, api_key: apiKey, model }),
      });
      if (!res.ok) throw new Error(await res.text());
      const data = await res.json();
      setIsConfigured(data.configured);
      setApiKey(""); // clear the field — key is now masked
      setStatus("saved");
      setMessage("Settings saved successfully.");
    } catch (err: unknown) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Failed to save settings.");
    }
  };

  const handleTest = async () => {
    setStatus("testing");
    setTestResult(null);
    try {
      const res = await fetch(`${backendUrl}/ai/test`, {
        method: "POST",
        headers: { Authorization: `Bearer ${session?.backendToken}` },
      });
      const data = await res.json();
      setTestResult(data);
    } catch {
      setTestResult({ success: false, error: "Network error" });
    } finally {
      setStatus("idle");
    }
  };

  return (
    <div className="max-w-lg mx-auto py-10 px-4 space-y-8">
      <div>
        <h1 className="text-2xl font-bold">AI Settings</h1>
        <p className="text-muted-foreground mt-1">
          Connect your own Anthropic or OpenAI API key to enable the AI chat panel.
        </p>
      </div>

      {/* Provider */}
      <div className="space-y-2">
        <Label>Provider</Label>
        <RadioGroup
          value={provider}
          onValueChange={(v) => handleProviderChange(v as "anthropic" | "openai")}
          className="flex gap-6"
        >
          <div className="flex items-center gap-2">
            <RadioGroupItem value="anthropic" id="prov-anthropic" />
            <Label htmlFor="prov-anthropic">Anthropic</Label>
          </div>
          <div className="flex items-center gap-2">
            <RadioGroupItem value="openai" id="prov-openai" />
            <Label htmlFor="prov-openai">OpenAI</Label>
          </div>
        </RadioGroup>
      </div>

      {/* Model */}
      <div className="space-y-2">
        <Label htmlFor="model-select">Model</Label>
        <Select value={model} onValueChange={setModel}>
          <SelectTrigger id="model-select" className="w-full">
            <SelectValue placeholder="Select model" />
          </SelectTrigger>
          <SelectContent>
            {MODELS[provider].map((m) => (
              <SelectItem key={m} value={m}>
                {m}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* API Key */}
      <div className="space-y-2">
        <Label htmlFor="api-key">
          API Key{" "}
          {isConfigured && (
            <span className="text-xs text-muted-foreground ml-1">(leave blank to keep existing key)</span>
          )}
        </Label>
        <Input
          id="api-key"
          type="password"
          placeholder={isConfigured ? "••••••••••••••••" : "sk-ant-... or sk-..."}
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          autoComplete="off"
        />
      </div>

      {/* Status messages */}
      {status === "saved" && (
        <Alert variant="default" className="border-green-500 text-green-700">
          <CheckCircle className="h-4 w-4" />
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}
      {status === "error" && (
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}

      {/* Test result */}
      {testResult && (
        <Alert
          variant={testResult.success ? "default" : "destructive"}
          className={testResult.success ? "border-green-500 text-green-700" : ""}
        >
          {testResult.success ? (
            <CheckCircle className="h-4 w-4" />
          ) : (
            <XCircle className="h-4 w-4" />
          )}
          <AlertDescription>
            {testResult.success
              ? "Connection successful — API key is valid."
              : `Connection failed: ${testResult.error}`}
          </AlertDescription>
        </Alert>
      )}

      {/* Actions */}
      <div className="flex gap-3">
        <Button onClick={handleSave} disabled={status === "saving" || status === "testing"}>
          {status === "saving" ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving…
            </>
          ) : (
            "Save"
          )}
        </Button>
        <Button
          variant="outline"
          onClick={handleTest}
          disabled={!isConfigured || status === "saving" || status === "testing"}
        >
          {status === "testing" ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Testing…
            </>
          ) : (
            "Test connection"
          )}
        </Button>
        <Button variant="ghost" onClick={() => router.back()}>
          Back
        </Button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Verify the page compiles**

```bash
cd frontend
npx tsc --noEmit 2>&1 | grep "settings/ai"
```
Expected: no output (no errors for this file).

- [ ] **Step 4: Commit**

```bash
git add frontend/app/settings/ai/page.tsx
git commit -m "feat: /settings/ai page — provider, model, API key, test connection"
```

---

## Task 5: Add AI Settings Link to Sidebar Nav

**Files:**
- Edit: `frontend/app/dashboard/page.tsx` (or the sidebar component, whichever contains the nav links)

- [ ] **Step 1: Locate the sidebar nav links**

Open `frontend/app/dashboard/page.tsx` and find where the sidebar navigation links are rendered. Look for a pattern like:

```tsx
<nav>
  {/* ...nav items... */}
</nav>
```

- [ ] **Step 2: Add the AI Settings nav link**

Inside the sidebar navigation links section, add:

```tsx
<Link
  href="/settings/ai"
  className="flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium hover:bg-accent hover:text-accent-foreground transition-colors"
>
  <span>⚙️ AI Settings</span>
</Link>
```

- [ ] **Step 3: Verify compilation**

```bash
cd frontend
npx tsc --noEmit 2>&1 | grep -i "dashboard\|sidebar"
```
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/dashboard/page.tsx
git commit -m "feat: add AI Settings link to dashboard sidebar nav"
```

---

## Task 6: SSE Streaming Hook

**Files:**
- Create: `frontend/lib/chat.ts`

- [ ] **Step 1: Create `frontend/lib/chat.ts`**

```typescript
export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

/**
 * Sends a message to the /ai/chat endpoint and streams the response
 * token-by-token via SSE, calling `onToken` for each token and
 * `onDone` when the stream finishes.
 *
 * Returns a function that aborts the stream when called.
 */
export function streamChatMessage({
  message,
  backendUrl,
  backendToken,
  onToken,
  onDone,
  onError,
}: {
  message: string;
  backendUrl: string;
  backendToken: string;
  onToken: (token: string) => void;
  onDone: () => void;
  onError: (err: string) => void;
}): () => void {
  const controller = new AbortController();

  (async () => {
    let response: Response;
    try {
      response = await fetch(`${backendUrl}/ai/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${backendToken}`,
        },
        body: JSON.stringify({ message }),
        signal: controller.signal,
      });
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        onError("Failed to connect to AI service.");
      }
      return;
    }

    if (!response.ok) {
      onError(`AI service error: ${response.status}`);
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      onError("No response body from AI service.");
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        // Keep the last (possibly incomplete) line in the buffer
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;
          try {
            const parsed = JSON.parse(raw) as { token?: string; done?: boolean };
            if (parsed.done) {
              onDone();
              return;
            }
            if (typeof parsed.token === "string") {
              onToken(parsed.token);
            }
          } catch {
            // malformed SSE line — skip
          }
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        onError("Stream interrupted.");
      }
    } finally {
      reader.releaseLock();
    }

    onDone();
  })();

  return () => controller.abort();
}
```

- [ ] **Step 2: Verify the file compiles**

```bash
cd frontend
npx tsc --noEmit 2>&1 | grep "chat.ts"
```
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/chat.ts
git commit -m "feat: SSE streaming hook for AI chat"
```

---

## Task 7: ChatPanel Component

**Files:**
- Create: `frontend/components/dashboard/ChatPanel.tsx`

- [ ] **Step 1: Create directory**

```bash
mkdir -p frontend/components/dashboard
```

- [ ] **Step 2: Create `frontend/components/dashboard/ChatPanel.tsx`**

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import Link from "next/link";
import { X, Send, Loader2, BotMessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { streamChatMessage, type ChatMessage } from "@/lib/chat";

interface AISummary {
  configured: boolean;
  provider?: string;
  model?: string;
}

interface ChatPanelProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ChatPanel({ isOpen, onClose }: ChatPanelProps) {
  const { data: session } = useSession();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [aiSummary, setAISummary] = useState<AISummary | null>(null);
  const abortRef = useRef<(() => void) | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000";

  // Fetch AI configuration status when panel opens
  useEffect(() => {
    if (!isOpen || !session?.backendToken) return;
    fetch(`${backendUrl}/ai/settings`, {
      headers: { Authorization: `Bearer ${session.backendToken}` },
    })
      .then((r) => r.json())
      .then((data: AISummary) => setAISummary(data))
      .catch(() => setAISummary({ configured: false }));
  }, [isOpen, session, backendUrl]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isStreaming || !session?.backendToken) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);
    setIsStreaming(true);

    const abort = streamChatMessage({
      message: text,
      backendUrl,
      backendToken: session.backendToken as string,
      onToken: (token) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          if (last.role === "assistant") {
            updated[updated.length - 1] = {
              ...last,
              content: last.content + token,
            };
          }
          return updated;
        });
      },
      onDone: () => {
        setIsStreaming(false);
        abortRef.current = null;
      },
      onError: (err) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: `Error: ${err}` };
          return updated;
        });
        setIsStreaming(false);
        abortRef.current = null;
      },
    });

    abortRef.current = abort;
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleClose = () => {
    abortRef.current?.();
    onClose();
  };

  const isConfigured = aiSummary?.configured ?? false;

  return (
    <>
      {/* Backdrop overlay (mobile) */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-30 md:hidden"
          onClick={handleClose}
          aria-hidden="true"
        />
      )}

      {/* Drawer */}
      <aside
        className={cn(
          "fixed top-0 right-0 h-full w-80 md:w-96 bg-background border-l shadow-xl z-40",
          "flex flex-col transition-transform duration-300 ease-in-out",
          isOpen ? "translate-x-0" : "translate-x-full"
        )}
        aria-label="AI Chat Panel"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b shrink-0">
          <div className="flex items-center gap-2">
            <BotMessageSquare className="h-5 w-5 text-muted-foreground" />
            <div>
              <p className="text-sm font-semibold leading-none">
                {aiSummary?.provider
                  ? aiSummary.provider.charAt(0).toUpperCase() + aiSummary.provider.slice(1)
                  : "AI Assistant"}
              </p>
              {aiSummary?.model && (
                <p className="text-xs text-muted-foreground mt-0.5">{aiSummary.model}</p>
              )}
            </div>
            {/* Status dot */}
            <span
              className={cn(
                "ml-1 inline-block h-2 w-2 rounded-full",
                isConfigured ? "bg-green-500" : "bg-red-500"
              )}
              title={isConfigured ? "Configured" : "Not configured"}
            />
          </div>
          <Button variant="ghost" size="icon" onClick={handleClose} aria-label="Close chat panel">
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Not configured state */}
        {!isConfigured && (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 px-6 text-center">
            <BotMessageSquare className="h-10 w-10 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              No AI provider configured. Add your API key to start chatting about your portfolio.
            </p>
            <Button asChild variant="outline" size="sm">
              <Link href="/settings/ai">Configure AI in Settings</Link>
            </Button>
          </div>
        )}

        {/* Chat thread */}
        {isConfigured && (
          <>
            <ScrollArea className="flex-1 px-4 py-3">
              {messages.length === 0 && (
                <p className="text-sm text-muted-foreground text-center mt-8">
                  Ask anything about your portfolio…
                </p>
              )}
              <div className="flex flex-col gap-3">
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className={cn(
                      "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                      msg.role === "user"
                        ? "self-end bg-primary text-primary-foreground"
                        : "self-start bg-muted text-foreground"
                    )}
                  >
                    {msg.content}
                    {msg.role === "assistant" && msg.content === "" && isStreaming && (
                      <Loader2 className="h-3 w-3 animate-spin inline-block ml-1" />
                    )}
                  </div>
                ))}
              </div>
              <div ref={bottomRef} />
            </ScrollArea>

            {/* Input area */}
            <div className="flex items-center gap-2 px-4 py-3 border-t shrink-0">
              <Input
                placeholder="Ask about your portfolio…"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={isStreaming}
                className="flex-1"
                aria-label="Chat input"
              />
              <Button
                size="icon"
                onClick={handleSend}
                disabled={!input.trim() || isStreaming}
                aria-label="Send message"
              >
                {isStreaming ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </Button>
            </div>
          </>
        )}
      </aside>
    </>
  );
}
```

- [ ] **Step 3: Verify compilation**

```bash
cd frontend
npx tsc --noEmit 2>&1 | grep "ChatPanel"
```
Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add frontend/components/dashboard/ChatPanel.tsx
git commit -m "feat: ChatPanel collapsible SSE-streaming chat drawer"
```

---

## Task 8: Wire ChatPanel into the Dashboard

**Files:**
- Edit: `frontend/app/dashboard/page.tsx`

- [ ] **Step 1: Add imports to `frontend/app/dashboard/page.tsx`**

At the top of `frontend/app/dashboard/page.tsx`, add:

```tsx
import { useState } from "react";
import { ChatPanel } from "@/components/dashboard/ChatPanel";
import { BotMessageSquare } from "lucide-react";
import { Button } from "@/components/ui/button";
```

- [ ] **Step 2: Add state for the chat panel open/close toggle**

Inside the page component function, add:

```tsx
const [chatOpen, setChatOpen] = useState(false);
```

- [ ] **Step 3: Add the toggle button to the dashboard top-right area**

Locate the top header/toolbar area in the dashboard JSX and add the toggle button. Place it in the top-right header area alongside any existing buttons:

```tsx
<Button
  variant="outline"
  size="sm"
  onClick={() => setChatOpen(true)}
  className="flex items-center gap-2"
>
  <BotMessageSquare className="h-4 w-4" />
  <span>AI Chat</span>
</Button>
```

- [ ] **Step 4: Add the ChatPanel component before the closing tag of the root element**

At the end of the dashboard page JSX, just before the outermost closing `</div>` or `</>`, add:

```tsx
<ChatPanel isOpen={chatOpen} onClose={() => setChatOpen(false)} />
```

- [ ] **Step 5: Verify compilation**

```bash
cd frontend
npx tsc --noEmit 2>&1 | grep -i "dashboard"
```
Expected: no output.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/dashboard/page.tsx
git commit -m "feat: wire ChatPanel into dashboard with open/close toggle"
```

---

## Task 9: End-to-End Smoke Test

**Files:**
- No new files — manual verification steps

- [ ] **Step 1: Start the backend**

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```
Expected:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

- [ ] **Step 2: Verify the AI router is reachable (no auth)**

```bash
curl -s http://localhost:8000/openapi.json | python3 -c "import sys, json; paths = json.load(sys.stdin)['paths']; print([p for p in paths if '/ai' in p])"
```
Expected output:
```
['/ai/settings', '/ai/test', '/ai/chat']
```

- [ ] **Step 3: Start the frontend**

```bash
cd frontend
npm run dev
```
Expected:
```
▲ Next.js 14.x.x
- Local: http://localhost:3000
✓ Ready in Xs
```

- [ ] **Step 4: Navigate to `/settings/ai` and confirm the page renders**

Open a browser at `http://localhost:3000/settings/ai`. Confirm:
- Radio buttons for Anthropic / OpenAI are visible
- Model dropdown is populated
- API key password input is present
- "Save" and "Test connection" buttons are rendered

- [ ] **Step 5: Open the dashboard and confirm the AI Chat button renders**

Navigate to `http://localhost:3000/dashboard`. Confirm:
- "AI Chat" button appears in the top-right header area
- Clicking it slides open the ChatPanel from the right
- When AI is not configured, the panel shows "Configure AI in Settings" with a link
- The status dot is red when unconfigured

- [ ] **Step 6: Run all backend tests**

```bash
cd backend
pytest tests/test_ai_service.py tests/test_ai_router.py -v
```
Expected:
```
tests/test_ai_service.py::test_build_portfolio_context_includes_positions PASSED
tests/test_ai_service.py::test_build_portfolio_context_calculates_pct_of_total PASSED
tests/test_ai_service.py::test_build_portfolio_context_shows_gain_loss_when_avg_cost_present PASSED
tests/test_ai_service.py::test_build_portfolio_context_no_gain_loss_without_avg_cost PASSED
tests/test_ai_service.py::test_build_portfolio_context_includes_transactions PASSED
tests/test_ai_service.py::test_build_portfolio_context_includes_labels PASSED
tests/test_ai_service.py::test_build_portfolio_context_empty_portfolio PASSED
tests/test_ai_service.py::test_build_system_prompt_contains_static_preamble PASSED
tests/test_ai_service.py::test_build_system_prompt_embeds_context PASSED
tests/test_ai_router.py::test_get_ai_settings_not_configured PASSED
tests/test_ai_router.py::test_get_ai_settings_configured PASSED
tests/test_ai_router.py::test_post_ai_settings_creates_new PASSED
tests/test_ai_router.py::test_post_ai_settings_invalid_provider PASSED
tests/test_ai_router.py::test_post_ai_test_success_anthropic PASSED
tests/test_ai_router.py::test_post_ai_test_no_settings PASSED
tests/test_ai_router.py::test_post_ai_test_invalid_key_anthropic PASSED
16 passed in 0.XXs
```

- [ ] **Step 7: Final commit**

```bash
git add .
git commit -m "feat: Phase 3 complete — AI chat panel with streaming, settings page, and test connection"
```
