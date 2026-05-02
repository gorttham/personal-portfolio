# Phase 1: Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the backend data pipeline and frontend connection UI — users can sign in, connect their Moomoo, Longbridge, and IBKR brokerage accounts, and trigger a portfolio data sync.

**Architecture:** Next.js 14 frontend on Vercel handles auth via NextAuth.js v5 (Google/GitHub OAuth) and calls a FastAPI backend on Railway. The backend stores all data in Neon PostgreSQL, encrypts brokerage credentials with Fernet, and syncs portfolio data 3× daily via Railway cron.

**Tech Stack:** Next.js 14 (App Router), TypeScript, NextAuth.js v5, Tailwind CSS, shadcn/ui (frontend) · FastAPI, SQLAlchemy 2.0 async, Alembic, asyncpg, PyJWT, cryptography, longbridge SDK, futu-api SDK, httpx (backend) · Neon PostgreSQL (database)

---

## File Map

```
personal-portfolio/
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                  # Root layout + SessionProvider
│   │   ├── page.tsx                    # Landing page
│   │   ├── (auth)/login/page.tsx       # Login page
│   │   ├── dashboard/page.tsx          # Dashboard stub (Phase 2)
│   │   └── connect/page.tsx            # Brokerage connection page
│   ├── components/connect/
│   │   ├── BrokerCard.tsx              # Connected/disconnected broker card
│   │   └── TokenDrawer.tsx             # Slide-in drawer for API token input
│   ├── lib/
│   │   ├── auth.ts                     # NextAuth config (providers, callbacks)
│   │   └── api.ts                      # Typed fetch wrapper → FastAPI
│   ├── middleware.ts                    # Protect /dashboard and /connect routes
│   ├── next.config.ts
│   ├── tailwind.config.ts
│   ├── components.json                 # shadcn/ui config
│   ├── package.json
│   └── .env.local.example
│
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI app, CORS, router registration
│   │   ├── database.py                 # Neon async engine + session dependency
│   │   ├── models/
│   │   │   └── tables.py               # All 9 SQLAlchemy models
│   │   ├── schemas/
│   │   │   └── portfolio.py            # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── encryption.py           # Fernet encrypt/decrypt helpers
│   │   │   ├── auth.py                 # NextAuth JWT validation dependency
│   │   │   └── sync.py                 # Sync orchestrator (called by cron)
│   │   ├── adapters/
│   │   │   ├── base.py                 # ABC + shared dataclasses
│   │   │   ├── longbridge.py           # Longbridge adapter
│   │   │   ├── moomoo.py               # Moomoo/Futu adapter
│   │   │   └── ibkr.py                 # IBKR Client Portal adapter
│   │   └── routers/
│   │       ├── auth.py                 # POST /auth/session (upsert user)
│   │       ├── brokerages.py           # CRUD + OAuth endpoints
│   │       └── sync.py                 # POST /sync (cron trigger)
│   ├── tests/
│   │   ├── conftest.py                 # Fixtures: db session, test user, encrypted creds
│   │   ├── test_encryption.py
│   │   ├── test_auth.py
│   │   ├── test_adapters/
│   │   │   ├── test_longbridge.py
│   │   │   ├── test_moomoo.py
│   │   │   └── test_ibkr.py
│   │   └── test_sync.py
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_initial_schema.py
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── .env.example
│   └── Procfile
│
└── .gitignore
```

---

## Task 1: Monorepo Structure & .gitignore

**Files:**
- Create: `.gitignore`
- Create: `frontend/` directory (empty, populated in Task 13)
- Create: `backend/` directory (empty, populated in Task 2)

- [ ] **Step 1: Create .gitignore**

```
# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
.env
*.egg-info/
dist/
.pytest_cache/
.mypy_cache/

# Node
node_modules/
.next/
out/
.env.local
.env*.local
*.tsbuildinfo

# Misc
.DS_Store
.superpowers/
*.log
```

- [ ] **Step 2: Create directory stubs**

```bash
mkdir -p backend/app/models backend/app/schemas backend/app/services \
         backend/app/adapters backend/app/routers \
         backend/tests/test_adapters backend/alembic/versions \
         frontend/app/\(auth\)/login frontend/app/dashboard \
         frontend/app/connect frontend/components/connect frontend/lib
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore backend/ frontend/
git commit -m "chore: scaffold monorepo directory structure"
```

---

## Task 2: Backend Scaffolding

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/Procfile`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy[asyncio]==2.0.35
asyncpg==0.29.0
alembic==1.13.3
pydantic==2.9.2
pydantic-settings==2.5.2
cryptography==43.0.3
PyJWT==2.9.0
httpx==0.27.2
longbridge==1.0.22
futu-api==9.2.5408
python-dotenv==1.0.1
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-mock==3.14.0
```

- [ ] **Step 2: Create `backend/.env.example`**

```
DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.neon.tech/neondb?sslmode=require
ENCRYPTION_KEY=                # generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
NEXTAUTH_SECRET=               # must match AUTH_SECRET in frontend .env.local
SYNC_SECRET=                   # random string to protect the /sync cron endpoint
LONGBRIDGE_APP_KEY=
LONGBRIDGE_APP_SECRET=
LONGBRIDGE_REDIRECT_URI=https://your-backend.railway.app/brokerages/longbridge/oauth/callback
FRONTEND_URL=https://your-app.vercel.app
```

- [ ] **Step 3: Create `backend/Procfile`**

```
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

- [ ] **Step 4: Create `backend/app/__init__.py`** (empty file)

```bash
touch backend/app/__init__.py
touch backend/app/models/__init__.py
touch backend/app/schemas/__init__.py
touch backend/app/services/__init__.py
touch backend/app/adapters/__init__.py
touch backend/app/routers/__init__.py
touch backend/tests/__init__.py
touch backend/tests/test_adapters/__init__.py
```

- [ ] **Step 5: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, brokerages, sync
import os

app = FastAPI(title="Portfolio Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(brokerages.router, prefix="/brokerages", tags=["brokerages"])
app.include_router(sync.router, prefix="/sync", tags=["sync"])


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 6: Verify app starts**

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Expected: `Uvicorn running on http://127.0.0.1:8000`

- [ ] **Step 7: Commit**

```bash
git add backend/
git commit -m "feat: backend FastAPI scaffold with CORS and health endpoint"
```

---

## Task 3: Database Connection

**Files:**
- Create: `backend/app/database.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_database.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session

@pytest.mark.asyncio
async def test_get_session_yields_async_session():
    async for session in get_session():
        assert isinstance(session, AsyncSession)
        break
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_database.py -v
```
Expected: FAIL — `ImportError: cannot import name 'get_session'`

- [ ] **Step 3: Create `backend/app/database.py`**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost/portfolio")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_session():
    async with AsyncSessionLocal() as session:
        yield session
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_database.py -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/database.py backend/tests/test_database.py
git commit -m "feat: async SQLAlchemy database connection with Neon"
```

---

## Task 4: SQLAlchemy Models

**Files:**
- Create: `backend/app/models/tables.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_models.py`:

```python
from app.models.tables import (
    User, BrokerageConnection, Account, Position,
    PortfolioSnapshot, Transaction, AssetLabel,
    AssetLabelAssignment, SyncLog, UserAISettings,
    BrokerType, ConnectionStatus, TransactionType, AIProvider
)

def test_all_models_importable():
    assert User.__tablename__ == "users"
    assert BrokerageConnection.__tablename__ == "brokerage_connections"
    assert Account.__tablename__ == "accounts"
    assert Position.__tablename__ == "positions"
    assert PortfolioSnapshot.__tablename__ == "portfolio_snapshots"
    assert Transaction.__tablename__ == "transactions"
    assert AssetLabel.__tablename__ == "asset_labels"
    assert AssetLabelAssignment.__tablename__ == "asset_label_assignments"
    assert SyncLog.__tablename__ == "sync_logs"
    assert UserAISettings.__tablename__ == "user_ai_settings"

def test_broker_type_values():
    assert set(BrokerType) == {BrokerType.moomoo, BrokerType.longbridge, BrokerType.ibkr}

def test_position_has_upsert_index():
    index_names = [idx.name for idx in Position.__table__.indexes]
    assert "ix_positions_account_ticker" in index_names
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_models.py -v
```
Expected: FAIL — `ImportError: cannot import name 'User'`

- [ ] **Step 3: Create `backend/app/models/tables.py`**

```python
import uuid
import enum
from datetime import datetime
from decimal import Decimal
from sqlalchemy import (
    String, Text, Numeric, DateTime, ForeignKey,
    Enum as SAEnum, UniqueConstraint, Index
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class BrokerType(str, enum.Enum):
    moomoo = "moomoo"
    longbridge = "longbridge"
    ibkr = "ibkr"


class ConnectionStatus(str, enum.Enum):
    active = "active"
    expired = "expired"
    error = "error"


class SyncStatus(str, enum.Enum):
    success = "success"
    error = "error"


class TransactionType(str, enum.Enum):
    buy = "buy"
    sell = "sell"


class AIProvider(str, enum.Enum):
    anthropic = "anthropic"
    openai = "openai"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class BrokerageConnection(Base):
    __tablename__ = "brokerage_connections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    broker: Mapped[BrokerType] = mapped_column(SAEnum(BrokerType), nullable=False)
    credentials: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ConnectionStatus] = mapped_column(SAEnum(ConnectionStatus), default=ConnectionStatus.active)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brokerage_connections.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    broker_account_id: Mapped[str] = mapped_column(String, nullable=False)
    account_type: Mapped[str | None] = mapped_column(String)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    name: Mapped[str | None] = mapped_column(String)


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("account_id", "ticker", name="ix_positions_account_ticker"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str | None] = mapped_column(String)
    quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    avg_cost: Mapped[Decimal | None] = mapped_column(Numeric)
    current_price: Mapped[Decimal | None] = mapped_column(Numeric)
    current_value: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    asset_class: Mapped[str | None] = mapped_column(String)
    sector: Mapped[str | None] = mapped_column(String)
    country: Mapped[str | None] = mapped_column(String)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint("user_id", "broker_transaction_id", name="ix_transactions_user_broker_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[TransactionType] = mapped_column(SAEnum(TransactionType), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    broker_transaction_id: Mapped[str] = mapped_column(String, nullable=False)


class AssetLabel(Base):
    __tablename__ = "asset_labels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class AssetLabelAssignment(Base):
    __tablename__ = "asset_label_assignments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    label_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("asset_labels.id"), nullable=False)
    ticker: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class SyncLog(Base):
    __tablename__ = "sync_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    connection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brokerage_connections.id"), nullable=False)
    status: Mapped[SyncStatus] = mapped_column(SAEnum(SyncStatus), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class UserAISettings(Base):
    __tablename__ = "user_ai_settings"
    __table_args__ = (UniqueConstraint("user_id", name="ix_user_ai_settings_user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    provider: Mapped[AIProvider] = mapped_column(SAEnum(AIProvider), nullable=False)
    api_key: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_models.py -v
```
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/ backend/tests/test_models.py
git commit -m "feat: SQLAlchemy models for all 9 database tables"
```

---

## Task 5: Alembic Migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/0001_initial_schema.py`

- [ ] **Step 1: Initialise Alembic**

```bash
cd backend
alembic init alembic
```
Expected: creates `alembic/` directory and `alembic.ini`

- [ ] **Step 2: Update `backend/alembic.ini`** — set the sqlalchemy.url line to use env var

Replace the `sqlalchemy.url` line:
```ini
sqlalchemy.url = %(DATABASE_URL)s
```

- [ ] **Step 3: Replace `backend/alembic/env.py`**

```python
import asyncio
import os
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.database import Base
from app.models import tables  # noqa: F401 — registers all models

config = context.config
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", ""))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(url=config.get_main_option("sqlalchemy.url"), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: Generate initial migration**

```bash
cd backend
alembic revision --autogenerate -m "initial schema"
```
Expected: creates `alembic/versions/<hash>_initial_schema.py`

- [ ] **Step 5: Run migration against Neon**

```bash
DATABASE_URL=<your-neon-url> alembic upgrade head
```
Expected: `Running upgrade  -> <hash>, initial schema`

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/ backend/alembic.ini
git commit -m "feat: Alembic migrations — initial schema for all tables"
```

---

## Task 6: Encryption Service

**Files:**
- Create: `backend/app/services/encryption.py`
- Create: `backend/tests/test_encryption.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_encryption.py
import pytest
from app.services.encryption import encrypt, decrypt


def test_encrypt_returns_string():
    result = encrypt("secret", "test-key-32-chars-padded-to-fit!!")
    assert isinstance(result, str)
    assert result != "secret"


def test_decrypt_reverses_encrypt():
    key_str = "test-key-32-chars-padded-to-fit!!"
    ciphertext = encrypt("my api token", key_str)
    assert decrypt(ciphertext, key_str) == "my api token"


def test_different_encryptions_are_different():
    key_str = "test-key-32-chars-padded-to-fit!!"
    a = encrypt("same", key_str)
    b = encrypt("same", key_str)
    assert a != b  # Fernet uses random IV


def test_decrypt_wrong_key_raises():
    key_str = "test-key-32-chars-padded-to-fit!!"
    from cryptography.fernet import Fernet
    other_key = Fernet.generate_key().decode()
    ciphertext = encrypt("secret", key_str)
    with pytest.raises(Exception):
        decrypt(ciphertext, other_key)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
pytest tests/test_encryption.py -v
```
Expected: FAIL — `ImportError: cannot import name 'encrypt'`

- [ ] **Step 3: Create `backend/app/services/encryption.py`**

```python
import base64
import os
from cryptography.fernet import Fernet


def _make_fernet(key_str: str) -> Fernet:
    # Fernet requires a 32-byte URL-safe base64-encoded key.
    # If key_str is already a valid Fernet key (44 chars base64), use as-is.
    # Otherwise pad/hash to 32 bytes for deterministic test keys.
    try:
        return Fernet(key_str.encode())
    except Exception:
        padded = key_str.encode().ljust(32)[:32]
        return Fernet(base64.urlsafe_b64encode(padded))


def encrypt(plaintext: str, key_str: str | None = None) -> str:
    key = key_str or os.environ["ENCRYPTION_KEY"]
    return _make_fernet(key).encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str, key_str: str | None = None) -> str:
    key = key_str or os.environ["ENCRYPTION_KEY"]
    return _make_fernet(key).decrypt(ciphertext.encode()).decode()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_encryption.py -v
```
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/encryption.py backend/tests/test_encryption.py
git commit -m "feat: Fernet encryption/decryption service for credentials"
```

---

## Task 7: Auth Service (NextAuth JWT Validation)

**Files:**
- Create: `backend/app/services/auth.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_auth.py
import time
import jwt
import pytest
from app.services.auth import decode_nextauth_token, AuthError

SECRET = "test-nextauth-secret"

def make_token(payload: dict, secret: str = SECRET) -> str:
    return jwt.encode(payload, secret, algorithm="HS256")


def test_valid_token_returns_email():
    token = make_token({"email": "user@example.com", "exp": int(time.time()) + 3600})
    result = decode_nextauth_token(token, SECRET)
    assert result["email"] == "user@example.com"


def test_expired_token_raises():
    token = make_token({"email": "user@example.com", "exp": int(time.time()) - 1})
    with pytest.raises(AuthError, match="expired"):
        decode_nextauth_token(token, SECRET)


def test_wrong_secret_raises():
    token = make_token({"email": "user@example.com", "exp": int(time.time()) + 3600})
    with pytest.raises(AuthError, match="invalid"):
        decode_nextauth_token(token, "wrong-secret")


def test_missing_email_raises():
    token = make_token({"sub": "123", "exp": int(time.time()) + 3600})
    with pytest.raises(AuthError, match="email"):
        decode_nextauth_token(token, SECRET)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_auth.py -v
```
Expected: FAIL — `ImportError: cannot import name 'decode_nextauth_token'`

- [ ] **Step 3: Create `backend/app/services/auth.py`**

```python
import os
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_scheme = HTTPBearer()


class AuthError(Exception):
    pass


def decode_nextauth_token(token: str, secret: str) -> dict:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthError("Token expired")
    except jwt.InvalidTokenError:
        raise AuthError("Token invalid")

    if "email" not in payload:
        raise AuthError("Token missing email claim")

    return payload


async def get_current_user_email(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    secret = os.environ["NEXTAUTH_SECRET"]
    try:
        payload = decode_nextauth_token(credentials.credentials, secret)
    except AuthError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    return payload["email"]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_auth.py -v
```
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/auth.py backend/tests/test_auth.py
git commit -m "feat: NextAuth JWT validation dependency for FastAPI"
```

---

## Task 8: Adapter Base Class & Shared Data Types

**Files:**
- Create: `backend/app/adapters/base.py`

- [ ] **Step 1: Write failing test**

Create `backend/tests/test_adapters/test_base.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_adapters/test_base.py -v
```
Expected: FAIL — `ImportError`

- [ ] **Step 3: Create `backend/app/adapters/base.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
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
    async def get_accounts(self) -> list[AdapterAccount]:
        ...

    @abstractmethod
    async def get_positions(self, account_id: str) -> list[AdapterPosition]:
        ...

    @abstractmethod
    async def get_transactions(self, account_id: str, since: datetime) -> list[AdapterTransaction]:
        ...

    @abstractmethod
    async def get_balance(self, account_id: str) -> AdapterBalance:
        ...
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_adapters/test_base.py -v
```
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/adapters/base.py backend/tests/test_adapters/test_base.py
git commit -m "feat: brokerage adapter ABC and shared data types"
```

---

## Task 9: Longbridge Adapter

**Files:**
- Create: `backend/app/adapters/longbridge.py`
- Create: `backend/tests/test_adapters/test_longbridge.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_adapters/test_longbridge.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from datetime import datetime, timezone
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_adapters/test_longbridge.py -v
```
Expected: FAIL — `ImportError: cannot import name 'LongbridgeAdapter'`

- [ ] **Step 3: Create `backend/app/adapters/longbridge.py`**

```python
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from longbridge.openapi import TradeContext, Config
from app.adapters.base import (
    BrokerageAdapter, AdapterAccount, AdapterPosition,
    AdapterTransaction, AdapterBalance, TransactionType
)


class LongbridgeAdapter(BrokerageAdapter):
    def __init__(self, credentials: dict):
        self._creds = credentials

    @asynccontextmanager
    async def _get_trade_context(self):
        config = Config(
            app_key=self._creds["app_key"],
            app_secret=self._creds["app_secret"],
            access_token=self._creds["access_token"],
        )
        ctx = TradeContext(config)
        try:
            yield ctx
        finally:
            pass

    async def get_accounts(self) -> list[AdapterAccount]:
        async with self._get_trade_context() as ctx:
            resp = await ctx.account_balance()
            return [
                AdapterAccount(
                    broker_account_id=acct.account_id,
                    account_type=acct.account_type.name,
                    currency=acct.currency,
                    name=f"Longbridge {acct.account_type.name}",
                )
                for acct in resp.list
            ]

    async def get_positions(self, account_id: str) -> list[AdapterPosition]:
        async with self._get_trade_context() as ctx:
            resp = await ctx.stock_positions()
            positions = []
            for channel in resp.channels:
                for pos in channel.positions:
                    market = getattr(pos, "market", None)
                    country = market.name if market else None
                    positions.append(AdapterPosition(
                        ticker=pos.symbol,
                        name=pos.symbol_name,
                        quantity=Decimal(str(pos.quantity)),
                        avg_cost=Decimal(str(pos.cost_price)) if pos.cost_price else None,
                        current_price=Decimal(str(pos.current_price)) if pos.current_price else None,
                        current_value=Decimal(str(pos.market_value)),
                        currency=pos.currency,
                        asset_class="stock",
                        sector=getattr(pos, "sector", None),
                        country=country,
                    ))
            return positions

    async def get_transactions(self, account_id: str, since: datetime) -> list[AdapterTransaction]:
        async with self._get_trade_context() as ctx:
            resp = await ctx.history_executions()
            txns = []
            for order in resp.orders:
                executed_at = order.trade_done_at.replace(tzinfo=timezone.utc) if order.trade_done_at else None
                if not executed_at or executed_at < since:
                    continue
                txns.append(AdapterTransaction(
                    broker_transaction_id=order.order_id,
                    ticker=order.symbol,
                    type=TransactionType.buy if order.side.name == "Buy" else TransactionType.sell,
                    quantity=Decimal(str(order.executed_quantity)),
                    price=Decimal(str(order.executed_price)),
                    total_value=Decimal(str(order.executed_quantity)) * Decimal(str(order.executed_price)),
                    currency=order.currency,
                    executed_at=executed_at,
                ))
            return txns

    async def get_balance(self, account_id: str) -> AdapterBalance:
        async with self._get_trade_context() as ctx:
            resp = await ctx.account_balance()
            for acct in resp.list:
                if acct.account_id == account_id:
                    return AdapterBalance(
                        account_id=account_id,
                        total_value=Decimal(str(acct.total_cash)),
                        currency=acct.currency,
                    )
        raise ValueError(f"Account {account_id} not found")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_adapters/test_longbridge.py -v
```
Expected: 2 PASS (the third test just checks structure)

- [ ] **Step 5: Commit**

```bash
git add backend/app/adapters/longbridge.py backend/tests/test_adapters/test_longbridge.py
git commit -m "feat: Longbridge brokerage adapter with OAuth token auth"
```

---

## Task 10: Moomoo Adapter

**Files:**
- Create: `backend/app/adapters/moomoo.py`
- Create: `backend/tests/test_adapters/test_moomoo.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_adapters/test_moomoo.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_adapters/test_moomoo.py -v
```
Expected: FAIL — `ImportError`

- [ ] **Step 3: Create `backend/app/adapters/moomoo.py`**

```python
from decimal import Decimal
from datetime import datetime, timezone
import asyncio
from app.adapters.base import (
    BrokerageAdapter, AdapterAccount, AdapterPosition,
    AdapterTransaction, AdapterBalance, TransactionType
)

try:
    from futu import OpenSecTradeContext, TrdEnv, TrdMarket, RET_OK
except ImportError:
    OpenSecTradeContext = None  # allow import without futu-api installed in test env
    RET_OK = "0"


ASSET_CLASS_MAP = {
    "STOCK": "stock",
    "ETF": "etf",
    "BOND": "bond",
    "WARRANT": "stock",
}


class MoomooAdapter(BrokerageAdapter):
    def __init__(self, credentials: dict):
        self._creds = credentials

    def _make_context(self):
        env = TrdEnv.REAL if self._creds.get("trade_env", "REAL") == "REAL" else TrdEnv.SIMULATE
        return OpenSecTradeContext(
            host=self._creds.get("host", "127.0.0.1"),
            port=int(self._creds.get("port", 11111)),
            trd_env=env,
        )

    async def get_accounts(self) -> list[AdapterAccount]:
        return [AdapterAccount(
            broker_account_id=str(self._creds["acc_id"]),
            account_type=self._creds.get("trade_env", "REAL"),
            currency="USD",
            name="Moomoo Account",
        )]

    async def get_positions(self, account_id: str) -> list[AdapterPosition]:
        def _fetch():
            with self._make_context() as ctx:
                ret, data = ctx.position_list_query(acc_id=int(account_id))
                if ret != RET_OK or data is None:
                    return []
                positions = []
                for _, row in data.iterrows():
                    market = str(row.get("sec_market", ""))
                    stock_type = str(row.get("stock_type", "STOCK"))
                    positions.append(AdapterPosition(
                        ticker=row["code"],
                        name=row["stock_name"],
                        quantity=Decimal(str(row["qty"])),
                        avg_cost=Decimal(str(row["cost_price"])) if row["cost_price"] else None,
                        current_price=Decimal(str(row["current_price"])) if row["current_price"] else None,
                        current_value=Decimal(str(row["market_val"])),
                        currency=row.get("currency", "USD"),
                        asset_class=ASSET_CLASS_MAP.get(stock_type, "stock"),
                        country=market if market else None,
                    ))
                return positions

        return await asyncio.to_thread(_fetch)

    async def get_transactions(self, account_id: str, since: datetime) -> list[AdapterTransaction]:
        def _fetch():
            with self._make_context() as ctx:
                ret, data = ctx.history_order_list_query(acc_id=int(account_id))
                if ret != RET_OK or data is None:
                    return []
                txns = []
                for _, row in data.iterrows():
                    if row.get("order_status") != "FILLED_ALL":
                        continue
                    executed_at = datetime.fromisoformat(str(row["updated_time"])).replace(tzinfo=timezone.utc)
                    if executed_at < since:
                        continue
                    qty = Decimal(str(row["dealt_qty"]))
                    price = Decimal(str(row["dealt_avg_price"]))
                    txns.append(AdapterTransaction(
                        broker_transaction_id=str(row["order_id"]),
                        ticker=row["code"],
                        type=TransactionType.buy if row["trd_side"] == "BUY" else TransactionType.sell,
                        quantity=qty,
                        price=price,
                        total_value=qty * price,
                        currency=row.get("currency", "USD"),
                        executed_at=executed_at,
                    ))
                return txns

        return await asyncio.to_thread(_fetch)

    async def get_balance(self, account_id: str) -> AdapterBalance:
        def _fetch():
            with self._make_context() as ctx:
                ret, data = ctx.accinfo_query(acc_id=int(account_id))
                if ret != RET_OK or data is None:
                    raise ValueError("Failed to fetch Moomoo balance")
                row = data.iloc[0]
                return AdapterBalance(
                    account_id=account_id,
                    total_value=Decimal(str(row["total_assets"])),
                    currency=row.get("currency", "USD"),
                )

        return await asyncio.to_thread(_fetch)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_adapters/test_moomoo.py -v
```
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/adapters/moomoo.py backend/tests/test_adapters/test_moomoo.py
git commit -m "feat: Moomoo/Futu brokerage adapter using futu-api SDK"
```

---

## Task 11: IBKR Adapter

**Files:**
- Create: `backend/app/adapters/ibkr.py`
- Create: `backend/tests/test_adapters/test_ibkr.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_adapters/test_ibkr.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timezone
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
            "conid": 265598,
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
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get.return_value = MagicMock(
            status_code=200,
            json=lambda: mock_response,
        )
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_adapters/test_ibkr.py -v
```
Expected: FAIL — `ImportError`

- [ ] **Step 3: Create `backend/app/adapters/ibkr.py`**

```python
import httpx
from decimal import Decimal
from datetime import datetime, timezone
from app.adapters.base import (
    BrokerageAdapter, AdapterAccount, AdapterPosition,
    AdapterTransaction, AdapterBalance, TransactionType
)

ASSET_CLASS_MAP = {
    "STK": "stock",
    "ETF": "etf",
    "BOND": "bond",
    "OPT": "stock",
    "FUND": "etf",
    "CMDTY": "metal",
    "CRYPTO": "crypto",
}


class IBKRAdapter(BrokerageAdapter):
    def __init__(self, credentials: dict):
        self._creds = credentials
        self._base_url = credentials.get("base_url", "https://localhost:5000/v1/api")
        self._account_id = credentials["account_id"]

    async def _get(self, path: str) -> dict | list:
        # IBKR Client Portal API runs locally; SSL cert is self-signed.
        async with httpx.AsyncClient(verify=False, base_url=self._base_url) as client:
            resp = client.get(path)
            resp.raise_for_status()
            return resp.json()

    async def get_accounts(self) -> list[AdapterAccount]:
        return [AdapterAccount(
            broker_account_id=self._account_id,
            account_type="IBKR",
            currency="USD",
            name=f"IBKR {self._account_id}",
        )]

    async def get_positions(self, account_id: str) -> list[AdapterPosition]:
        async with httpx.AsyncClient(verify=False, base_url=self._base_url) as client:
            resp = client.get(f"/portfolio/{account_id}/positions/0")
            resp.raise_for_status()
            data = resp.json()

        positions = []
        for item in data:
            asset_class_raw = item.get("assetClass", "STK")
            positions.append(AdapterPosition(
                ticker=item["ticker"],
                name=item.get("companyName", item["ticker"]),
                quantity=Decimal(str(item["position"])),
                avg_cost=Decimal(str(item["avgCost"])) if item.get("avgCost") else None,
                current_price=Decimal(str(item["mktPrice"])) if item.get("mktPrice") else None,
                current_value=Decimal(str(item["mktValue"])),
                currency=item.get("currency", "USD"),
                asset_class=ASSET_CLASS_MAP.get(asset_class_raw, "stock"),
                sector=item.get("sector"),
                country=item.get("listingExchange"),
            ))
        return positions

    async def get_transactions(self, account_id: str, since: datetime) -> list[AdapterTransaction]:
        async with httpx.AsyncClient(verify=False, base_url=self._base_url) as client:
            resp = client.get(f"/iserver/account/trades")
            resp.raise_for_status()
            data = resp.json()

        txns = []
        for item in data:
            executed_at = datetime.fromtimestamp(item["trade_time"] / 1000, tz=timezone.utc)
            if executed_at < since:
                continue
            qty = Decimal(str(abs(item["size"])))
            price = Decimal(str(item["price"]))
            txns.append(AdapterTransaction(
                broker_transaction_id=str(item["execution_id"]),
                ticker=item["symbol"],
                type=TransactionType.buy if item["side"] == "B" else TransactionType.sell,
                quantity=qty,
                price=price,
                total_value=qty * price,
                currency=item.get("currency", "USD"),
                executed_at=executed_at,
            ))
        return txns

    async def get_balance(self, account_id: str) -> AdapterBalance:
        async with httpx.AsyncClient(verify=False, base_url=self._base_url) as client:
            resp = client.get(f"/portfolio/{account_id}/summary")
            resp.raise_for_status()
            data = resp.json()

        net_liquidation = data.get("netliquidation", {}).get("amount", 0)
        currency = data.get("netliquidation", {}).get("currency", "USD")
        return AdapterBalance(
            account_id=account_id,
            total_value=Decimal(str(net_liquidation)),
            currency=currency,
        )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_adapters/test_ibkr.py -v
```
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/adapters/ibkr.py backend/tests/test_adapters/test_ibkr.py
git commit -m "feat: IBKR Client Portal REST adapter"
```

---

## Task 12: Sync Service

**Files:**
- Create: `backend/app/services/sync.py`
- Create: `backend/tests/test_sync.py`

- [ ] **Step 1: Write failing test**

```python
# backend/tests/test_sync.py
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_sync.py -v
```
Expected: FAIL — `ImportError`

- [ ] **Step 3: Create `backend/app/services/sync.py`**

```python
import json
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.tables import (
    BrokerageConnection, Account, Position, PortfolioSnapshot,
    Transaction, SyncLog, ConnectionStatus, SyncStatus, TransactionType
)
from app.adapters.base import BrokerageAdapter
from app.adapters.longbridge import LongbridgeAdapter
from app.adapters.moomoo import MoomooAdapter
from app.adapters.ibkr import IBKRAdapter
from app.services.encryption import decrypt


def build_adapter(broker: str, credentials: dict) -> BrokerageAdapter:
    if broker == "longbridge":
        return LongbridgeAdapter(credentials)
    if broker == "moomoo":
        return MoomooAdapter(credentials)
    if broker == "ibkr":
        return IBKRAdapter(credentials)
    raise ValueError(f"Unknown broker: {broker}")


async def run_sync_for_connection(connection: BrokerageConnection, session: AsyncSession) -> dict:
    try:
        raw_creds = decrypt(connection.credentials)
        credentials = json.loads(raw_creds)
        adapter = build_adapter(connection.broker, credentials)

        accounts = await adapter.get_accounts()
        since = datetime.now(timezone.utc) - timedelta(days=90)

        for acct_data in accounts:
            # Upsert account
            result = await session.execute(
                select(Account).where(
                    Account.connection_id == connection.id,
                    Account.broker_account_id == acct_data.broker_account_id,
                )
            )
            account = result.scalar_one_or_none()
            if not account:
                account = Account(
                    id=uuid.uuid4(),
                    connection_id=connection.id,
                    user_id=connection.user_id,
                    broker_account_id=acct_data.broker_account_id,
                    account_type=acct_data.account_type,
                    currency=acct_data.currency,
                    name=acct_data.name,
                )
                session.add(account)
                await session.commit()

            # Upsert positions
            positions = await adapter.get_positions(acct_data.broker_account_id)
            for pos in positions:
                result = await session.execute(
                    select(Position).where(
                        Position.account_id == account.id,
                        Position.ticker == pos.ticker,
                    )
                )
                existing = result.scalar_one_or_none()
                if existing:
                    existing.quantity = pos.quantity
                    existing.avg_cost = pos.avg_cost
                    existing.current_price = pos.current_price
                    existing.current_value = pos.current_value
                    existing.updated_at = datetime.now(timezone.utc)
                else:
                    session.add(Position(
                        id=uuid.uuid4(),
                        account_id=account.id,
                        user_id=connection.user_id,
                        ticker=pos.ticker,
                        name=pos.name,
                        quantity=pos.quantity,
                        avg_cost=pos.avg_cost,
                        current_price=pos.current_price,
                        current_value=pos.current_value,
                        currency=pos.currency,
                        asset_class=pos.asset_class,
                        sector=pos.sector,
                        country=pos.country,
                    ))

            # Snapshot portfolio value
            balance = await adapter.get_balance(acct_data.broker_account_id)
            session.add(PortfolioSnapshot(
                id=uuid.uuid4(),
                user_id=connection.user_id,
                account_id=account.id,
                total_value=balance.total_value,
                currency=balance.currency,
            ))

            # Insert new transactions (dedup by broker_transaction_id)
            transactions = await adapter.get_transactions(acct_data.broker_account_id, since)
            for txn in transactions:
                result = await session.execute(
                    select(Transaction).where(
                        Transaction.user_id == connection.user_id,
                        Transaction.broker_transaction_id == txn.broker_transaction_id,
                    )
                )
                if result.scalar_one_or_none() is None:
                    session.add(Transaction(
                        id=uuid.uuid4(),
                        account_id=account.id,
                        user_id=connection.user_id,
                        ticker=txn.ticker,
                        type=TransactionType(txn.type.value),
                        quantity=txn.quantity,
                        price=txn.price,
                        total_value=txn.total_value,
                        currency=txn.currency,
                        executed_at=txn.executed_at,
                        broker_transaction_id=txn.broker_transaction_id,
                    ))

        connection.last_synced_at = datetime.now(timezone.utc)
        connection.status = ConnectionStatus.active
        session.add(SyncLog(
            id=uuid.uuid4(),
            user_id=connection.user_id,
            connection_id=connection.id,
            status=SyncStatus.success,
        ))
        await session.commit()
        return {"status": "success"}

    except Exception as e:
        connection.status = ConnectionStatus.error
        session.add(SyncLog(
            id=uuid.uuid4(),
            user_id=connection.user_id,
            connection_id=connection.id,
            status=SyncStatus.error,
            error_message=str(e),
        ))
        await session.commit()
        return {"status": "error", "error": str(e)}


async def run_all_syncs(session: AsyncSession) -> list[dict]:
    result = await session.execute(
        select(BrokerageConnection).where(
            BrokerageConnection.status.in_([ConnectionStatus.active, ConnectionStatus.error])
        )
    )
    connections = result.scalars().all()
    return [await run_sync_for_connection(conn, session) for conn in connections]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_sync.py -v
```
Expected: 2 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/sync.py backend/tests/test_sync.py
git commit -m "feat: sync service — orchestrates adapter calls and writes to DB"
```

---

## Task 13: Pydantic Schemas & API Routers

**Files:**
- Create: `backend/app/schemas/portfolio.py`
- Create: `backend/app/routers/auth.py`
- Create: `backend/app/routers/brokerages.py`
- Create: `backend/app/routers/sync.py`

- [ ] **Step 1: Create `backend/app/schemas/portfolio.py`**

```python
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class UserUpsertRequest(BaseModel):
    email: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: Optional[str]
    avatar_url: Optional[str]

    model_config = {"from_attributes": True}


class BrokerageConnectionResponse(BaseModel):
    id: uuid.UUID
    broker: str
    status: str
    last_synced_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class ConnectTokenRequest(BaseModel):
    broker: str  # "moomoo" or "ibkr"
    credentials: dict  # raw creds — will be encrypted before storing


class LongbridgeOAuthCallbackRequest(BaseModel):
    code: str
    state: str
```

- [ ] **Step 2: Create `backend/app/routers/auth.py`**

```python
import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models.tables import User
from app.schemas.portfolio import UserUpsertRequest, UserResponse
from app.services.auth import get_current_user_email

router = APIRouter()


@router.post("/session", response_model=UserResponse)
async def upsert_user(
    body: UserUpsertRequest,
    email: str = Depends(get_current_user_email),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(id=uuid.uuid4(), email=email, name=body.name, avatar_url=body.avatar_url)
        session.add(user)
        await session.commit()
    return user
```

- [ ] **Step 3: Create `backend/app/routers/brokerages.py`**

```python
import json
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_session
from app.models.tables import User, BrokerageConnection, ConnectionStatus, BrokerType
from app.schemas.portfolio import BrokerageConnectionResponse, ConnectTokenRequest
from app.services.auth import get_current_user_email
from app.services.encryption import encrypt, decrypt

router = APIRouter()


async def _get_user(email: str, session: AsyncSession) -> User:
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found — call /auth/session first")
    return user


@router.get("", response_model=list[BrokerageConnectionResponse])
async def list_connections(
    email: str = Depends(get_current_user_email),
    session: AsyncSession = Depends(get_session),
):
    user = await _get_user(email, session)
    result = await session.execute(
        select(BrokerageConnection).where(BrokerageConnection.user_id == user.id)
    )
    return result.scalars().all()


@router.post("/connect", response_model=BrokerageConnectionResponse)
async def connect_token_broker(
    body: ConnectTokenRequest,
    email: str = Depends(get_current_user_email),
    session: AsyncSession = Depends(get_session),
):
    if body.broker not in ("moomoo", "ibkr"):
        raise HTTPException(status_code=400, detail="Use /brokerages/longbridge/oauth/start for Longbridge")
    user = await _get_user(email, session)
    encrypted = encrypt(json.dumps(body.credentials))
    conn = BrokerageConnection(
        id=uuid.uuid4(),
        user_id=user.id,
        broker=BrokerType(body.broker),
        credentials=encrypted,
        status=ConnectionStatus.active,
    )
    session.add(conn)
    await session.commit()
    return conn


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: uuid.UUID,
    email: str = Depends(get_current_user_email),
    session: AsyncSession = Depends(get_session),
):
    user = await _get_user(email, session)
    result = await session.execute(
        select(BrokerageConnection).where(
            BrokerageConnection.id == connection_id,
            BrokerageConnection.user_id == user.id,
        )
    )
    conn = result.scalar_one_or_none()
    if conn is None:
        raise HTTPException(status_code=404, detail="Connection not found")
    await session.delete(conn)
    await session.commit()


@router.get("/longbridge/oauth/start")
async def longbridge_oauth_start(email: str = Depends(get_current_user_email)):
    app_key = os.environ["LONGBRIDGE_APP_KEY"]
    redirect_uri = os.environ["LONGBRIDGE_REDIRECT_URI"]
    import urllib.parse
    params = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": app_key,
        "redirect_uri": redirect_uri,
        "state": email,
    })
    return RedirectResponse(f"https://open.longportapp.com/oauth?{params}")


@router.get("/longbridge/oauth/callback")
async def longbridge_oauth_callback(
    code: str,
    state: str,
    session: AsyncSession = Depends(get_session),
):
    import httpx
    token_resp = httpx.post(
        "https://open.longportapp.com/v1/token",
        json={
            "code": code,
            "client_id": os.environ["LONGBRIDGE_APP_KEY"],
            "client_secret": os.environ["LONGBRIDGE_APP_SECRET"],
            "redirect_uri": os.environ["LONGBRIDGE_REDIRECT_URI"],
            "grant_type": "authorization_code",
        },
    )
    token_resp.raise_for_status()
    token_data = token_resp.json()

    result = await session.execute(select(User).where(User.email == state))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=400, detail="Unknown user in OAuth state")

    credentials = {
        "app_key": os.environ["LONGBRIDGE_APP_KEY"],
        "app_secret": os.environ["LONGBRIDGE_APP_SECRET"],
        "access_token": token_data["access_token"],
        "refresh_token": token_data.get("refresh_token"),
    }
    conn = BrokerageConnection(
        id=uuid.uuid4(),
        user_id=user.id,
        broker=BrokerType.longbridge,
        credentials=encrypt(json.dumps(credentials)),
        status=ConnectionStatus.active,
    )
    session.add(conn)
    await session.commit()
    return RedirectResponse(f"{os.environ['FRONTEND_URL']}/connect?connected=longbridge")
```

- [ ] **Step 4: Create `backend/app/routers/sync.py`**

```python
import os
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_session
from app.services.sync import run_all_syncs

router = APIRouter()


@router.post("")
async def trigger_sync(
    x_sync_secret: str = Header(..., alias="X-Sync-Secret"),
    session: AsyncSession = Depends(get_session),
):
    if x_sync_secret != os.environ.get("SYNC_SECRET", ""):
        raise HTTPException(status_code=401, detail="Invalid sync secret")
    results = await run_all_syncs(session)
    return {"results": results}
```

- [ ] **Step 5: Verify all routes are registered**

```bash
cd backend
uvicorn app.main:app --reload &
curl http://localhost:8000/health
curl http://localhost:8000/openapi.json | python3 -c "import sys,json; paths=json.load(sys.stdin)['paths']; [print(p) for p in paths]"
```
Expected output includes: `/health`, `/auth/session`, `/brokerages`, `/brokerages/connect`, `/brokerages/longbridge/oauth/start`, `/sync`

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/ backend/app/routers/
git commit -m "feat: Pydantic schemas and API routers (auth, brokerages, sync)"
```

---

## Task 14: Frontend Scaffolding

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/components.json`
- Create: `frontend/.env.local.example`

- [ ] **Step 1: Initialise Next.js app**

```bash
cd frontend
npx create-next-app@14 . --typescript --tailwind --eslint --app --no-src-dir --import-alias "@/*"
```
Expected: installs dependencies, creates `app/`, `public/`, config files.

- [ ] **Step 2: Install additional dependencies**

```bash
cd frontend
npm install next-auth@beta
npm install recharts
npm install lucide-react
npm install clsx tailwind-merge
```

- [ ] **Step 3: Initialise shadcn/ui**

```bash
cd frontend
npx shadcn@latest init
```
When prompted: style = Default, base color = Slate, CSS variables = yes.

- [ ] **Step 4: Add required shadcn components**

```bash
npx shadcn@latest add button card drawer input label badge separator
```

- [ ] **Step 5: Create `frontend/.env.local.example`**

```
AUTH_SECRET=                  # generate with: openssl rand -base64 32
AUTH_GOOGLE_ID=
AUTH_GOOGLE_SECRET=
AUTH_GITHUB_ID=
AUTH_GITHUB_SECRET=
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
```

- [ ] **Step 6: Update `frontend/tailwind.config.ts`** — add dark mode and custom colours

```typescript
import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0a0a0f",
        surface: "rgba(255,255,255,0.04)",
        border: "rgba(255,255,255,0.08)",
        accent: "#6366f1",
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 7: Verify app builds**

```bash
cd frontend
npm run build
```
Expected: Build succeeds with no errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: Next.js 14 frontend scaffold with Tailwind and shadcn/ui"
```

---

## Task 15: NextAuth Setup

**Files:**
- Create: `frontend/lib/auth.ts`
- Create: `frontend/app/api/auth/[...nextauth]/route.ts`
- Modify: `frontend/app/layout.tsx`
- Create: `frontend/middleware.ts`

- [ ] **Step 1: Create `frontend/lib/auth.ts`**

```typescript
import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import GitHub from "next-auth/providers/github";
import { encode } from "next-auth/jwt";

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Google({
      clientId: process.env.AUTH_GOOGLE_ID!,
      clientSecret: process.env.AUTH_GOOGLE_SECRET!,
    }),
    GitHub({
      clientId: process.env.AUTH_GITHUB_ID!,
      clientSecret: process.env.AUTH_GITHUB_SECRET!,
    }),
  ],
  session: { strategy: "jwt" },
  callbacks: {
    async jwt({ token, profile }) {
      if (profile) {
        token.avatar_url = (profile as any).avatar_url ?? (profile as any).picture;
      }
      return token;
    },
    async session({ session, token }) {
      // Re-encode the JWT as a string and expose it to the client.
      // The FastAPI backend verifies this using the same AUTH_SECRET.
      (session as any).backendToken = await encode({
        token,
        secret: process.env.AUTH_SECRET!,
      });
      return session;
    },
  },
});
```

- [ ] **Step 2: Create `frontend/app/api/auth/[...nextauth]/route.ts`**

```typescript
import { handlers } from "@/lib/auth";
export const { GET, POST } = handlers;
```

- [ ] **Step 3: Update `frontend/app/layout.tsx`**

```typescript
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { SessionProvider } from "next-auth/react";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Portfolio Tracker",
  description: "Unified brokerage analytics dashboard",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-background text-white min-h-screen`}>
        <SessionProvider>{children}</SessionProvider>
      </body>
    </html>
  );
}
```

- [ ] **Step 4: Create `frontend/middleware.ts`**

```typescript
import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

export default auth((req) => {
  const isLoggedIn = !!req.auth;
  const isProtected = req.nextUrl.pathname.startsWith("/dashboard") ||
                      req.nextUrl.pathname.startsWith("/connect") ||
                      req.nextUrl.pathname.startsWith("/settings");

  if (isProtected && !isLoggedIn) {
    return NextResponse.redirect(new URL("/", req.nextUrl));
  }
});

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
```

- [ ] **Step 5: Create `frontend/lib/api.ts`**

```typescript
import { auth } from "@/lib/auth";
import { getToken } from "next-auth/jwt";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
  token: string
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API error ${res.status}: ${error}`);
  }
  return res.json();
}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/ frontend/app/api/ frontend/app/layout.tsx frontend/middleware.ts
git commit -m "feat: NextAuth v5 with Google and GitHub providers, JWT sessions"
```

---

## Task 16: Landing Page & Login

**Files:**
- Modify: `frontend/app/page.tsx`
- Create: `frontend/app/(auth)/login/page.tsx`

- [ ] **Step 1: Create `frontend/app/page.tsx`**

```typescript
import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import { signIn } from "@/lib/auth";
import { Button } from "@/components/ui/button";

export default async function LandingPage() {
  const session = await auth();
  if (session) redirect("/dashboard");

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-2xl w-full space-y-10 text-center">
        <div className="space-y-4">
          <h1 className="text-5xl font-bold tracking-tight bg-gradient-to-r from-white to-white/60 bg-clip-text text-transparent">
            Portfolio Tracker
          </h1>
          <p className="text-lg text-white/50">
            Aggregate all your brokerage accounts. One dashboard. AI-powered insights.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-4 text-sm text-white/40">
          <div className="rounded-xl border border-border bg-surface p-4">
            <div className="text-accent text-2xl mb-2">⚡</div>
            <p>Connect Moomoo, Longbridge & IBKR in one click</p>
          </div>
          <div className="rounded-xl border border-border bg-surface p-4">
            <div className="text-accent text-2xl mb-2">📈</div>
            <p>Portfolio performance charts with buy/sell markers</p>
          </div>
          <div className="rounded-xl border border-border bg-surface p-4">
            <div className="text-accent text-2xl mb-2">🤖</div>
            <p>Ask Claude or GPT-4 questions about your holdings</p>
          </div>
        </div>

        <div className="flex gap-4 justify-center">
          <form
            action={async () => {
              "use server";
              await signIn("google", { redirectTo: "/dashboard" });
            }}
          >
            <Button type="submit" className="bg-accent hover:bg-accent/90 px-8">
              Sign in with Google
            </Button>
          </form>
          <form
            action={async () => {
              "use server";
              await signIn("github", { redirectTo: "/dashboard" });
            }}
          >
            <Button type="submit" variant="outline" className="border-border px-8">
              Sign in with GitHub
            </Button>
          </form>
        </div>
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Create `frontend/app/dashboard/page.tsx`** (stub for Phase 2)

```typescript
import { auth } from "@/lib/auth";
import { redirect } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default async function DashboardPage() {
  const session = await auth();
  if (!session) redirect("/");

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4">
      <h1 className="text-2xl font-semibold">Dashboard</h1>
      <p className="text-white/40">Charts coming in Phase 2.</p>
      <Link href="/connect">
        <Button className="bg-accent hover:bg-accent/90">Connect Brokerages →</Button>
      </Link>
    </main>
  );
}
```

- [ ] **Step 3: Verify landing page renders**

```bash
cd frontend && npm run dev
```
Open `http://localhost:3000` — should show hero section with two sign-in buttons.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/page.tsx frontend/app/dashboard/page.tsx
git commit -m "feat: landing page with OAuth sign-in buttons and dashboard stub"
```

---

## Task 17: Connect Page (Brokerage Connection UI)

**Files:**
- Create: `frontend/components/connect/BrokerCard.tsx`
- Create: `frontend/components/connect/TokenDrawer.tsx`
- Create: `frontend/app/connect/page.tsx`

- [ ] **Step 1: Create `frontend/components/connect/BrokerCard.tsx`**

```typescript
"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CheckCircle, XCircle, Loader2 } from "lucide-react";

interface BrokerCardProps {
  name: string;
  logo: string;
  description: string;
  connected: boolean;
  lastSynced: string | null;
  onConnect: () => void;
  onDisconnect: () => void;
  loading?: boolean;
}

export function BrokerCard({
  name, logo, description, connected, lastSynced, onConnect, onDisconnect, loading
}: BrokerCardProps) {
  return (
    <div className="rounded-xl border border-border bg-surface p-6 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{logo}</span>
          <div>
            <h3 className="font-semibold">{name}</h3>
            <p className="text-sm text-white/40">{description}</p>
          </div>
        </div>
        {connected ? (
          <CheckCircle className="text-green-400 h-5 w-5" />
        ) : (
          <XCircle className="text-white/20 h-5 w-5" />
        )}
      </div>

      {connected && lastSynced && (
        <p className="text-xs text-white/30">Last synced: {lastSynced}</p>
      )}

      <div className="flex gap-2">
        {!connected ? (
          <Button
            onClick={onConnect}
            disabled={loading}
            className="bg-accent hover:bg-accent/90 flex-1"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Connect"}
          </Button>
        ) : (
          <Button
            onClick={onDisconnect}
            variant="outline"
            className="border-border text-white/60 hover:text-white flex-1"
          >
            Disconnect
          </Button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create `frontend/components/connect/TokenDrawer.tsx`**

```typescript
"use client";

import { useState } from "react";
import {
  Drawer, DrawerContent, DrawerHeader, DrawerTitle, DrawerDescription
} from "@/components/ui/drawer";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface Field {
  key: string;
  label: string;
  placeholder: string;
  type?: string;
}

interface TokenDrawerProps {
  open: boolean;
  onClose: () => void;
  brokerName: string;
  fields: Field[];
  instructions: string;
  onSubmit: (values: Record<string, string>) => Promise<void>;
}

export function TokenDrawer({ open, onClose, brokerName, fields, instructions, onSubmit }: TokenDrawerProps) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await onSubmit(values);
      onClose();
    } catch (err: any) {
      setError(err.message ?? "Failed to connect");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Drawer open={open} onClose={onClose}>
      <DrawerContent className="bg-background border-border text-white max-w-md mx-auto">
        <DrawerHeader>
          <DrawerTitle>Connect {brokerName}</DrawerTitle>
          <DrawerDescription className="text-white/40 text-sm whitespace-pre-line">
            {instructions}
          </DrawerDescription>
        </DrawerHeader>
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          {fields.map((field) => (
            <div key={field.key} className="space-y-1">
              <Label htmlFor={field.key} className="text-white/70">{field.label}</Label>
              <Input
                id={field.key}
                type={field.type ?? "text"}
                placeholder={field.placeholder}
                className="bg-surface border-border text-white"
                value={values[field.key] ?? ""}
                onChange={(e) => setValues((v) => ({ ...v, [field.key]: e.target.value }))}
                required
              />
            </div>
          ))}
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <div className="flex gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose} className="flex-1 border-border">
              Cancel
            </Button>
            <Button type="submit" disabled={loading} className="flex-1 bg-accent hover:bg-accent/90">
              {loading ? "Connecting…" : "Save"}
            </Button>
          </div>
        </form>
      </DrawerContent>
    </Drawer>
  );
}
```

- [ ] **Step 3: Create `frontend/app/connect/page.tsx`**

```typescript
"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { BrokerCard } from "@/components/connect/BrokerCard";
import { TokenDrawer } from "@/components/connect/TokenDrawer";
import { apiFetch } from "@/lib/api";

const API_URL = process.env.NEXT_PUBLIC_API_URL!;

interface Connection {
  id: string;
  broker: string;
  status: string;
  last_synced_at: string | null;
}

export default function ConnectPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [connections, setConnections] = useState<Connection[]>([]);
  const [drawerBroker, setDrawerBroker] = useState<"moomoo" | "ibkr" | null>(null);
  const [loading, setLoading] = useState<string | null>(null);

  const token = (session as any)?.backendToken ?? "";

  useEffect(() => {
    if (!session) return;
    apiFetch<Connection[]>("/brokerages", {}, token).then(setConnections);
  }, [session]);

  useEffect(() => {
    const connected = searchParams.get("connected");
    if (connected) {
      apiFetch<Connection[]>("/brokerages", {}, token).then(setConnections);
    }
  }, [searchParams]);

  function isConnected(broker: string) {
    return connections.some((c) => c.broker === broker && c.status === "active");
  }

  function getLastSynced(broker: string) {
    const conn = connections.find((c) => c.broker === broker);
    if (!conn?.last_synced_at) return null;
    return new Date(conn.last_synced_at).toLocaleString();
  }

  async function handleDisconnect(broker: string) {
    const conn = connections.find((c) => c.broker === broker);
    if (!conn) return;
    await apiFetch(`/brokerages/${conn.id}`, { method: "DELETE" }, token);
    setConnections((cs) => cs.filter((c) => c.id !== conn.id));
  }

  async function handleTokenConnect(values: Record<string, string>) {
    await apiFetch<Connection>(
      "/brokerages/connect",
      { method: "POST", body: JSON.stringify({ broker: drawerBroker, credentials: values }) },
      token
    );
    const updated = await apiFetch<Connection[]>("/brokerages", {}, token);
    setConnections(updated);
  }

  function handleLongbridgeConnect() {
    window.location.href = `${API_URL}/brokerages/longbridge/oauth/start`;
  }

  return (
    <main className="max-w-2xl mx-auto py-16 px-4 space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Connect Brokerages</h1>
        <p className="text-white/40 mt-1">Your data syncs automatically 3× daily.</p>
      </div>

      <div className="grid gap-4">
        <BrokerCard
          name="Longbridge"
          logo="🌉"
          description="OAuth — sign in directly to authorise"
          connected={isConnected("longbridge")}
          lastSynced={getLastSynced("longbridge")}
          onConnect={handleLongbridgeConnect}
          onDisconnect={() => handleDisconnect("longbridge")}
        />
        <BrokerCard
          name="Moomoo"
          logo="🐄"
          description="Paste your OpenD access token"
          connected={isConnected("moomoo")}
          lastSynced={getLastSynced("moomoo")}
          onConnect={() => setDrawerBroker("moomoo")}
          onDisconnect={() => handleDisconnect("moomoo")}
        />
        <BrokerCard
          name="Interactive Brokers"
          logo="📊"
          description="Paste your Client Portal API token"
          connected={isConnected("ibkr")}
          lastSynced={getLastSynced("ibkr")}
          onConnect={() => setDrawerBroker("ibkr")}
          onDisconnect={() => handleDisconnect("ibkr")}
        />
      </div>

      <TokenDrawer
        open={drawerBroker === "moomoo"}
        onClose={() => setDrawerBroker(null)}
        brokerName="Moomoo"
        instructions={`1. Open the Moomoo app → Me → Settings → About → OpenD\n2. Start OpenD on your machine or cloud VM\n3. Copy the IP, port, and account ID from OpenD settings`}
        fields={[
          { key: "host", label: "OpenD Host", placeholder: "127.0.0.1" },
          { key: "port", label: "OpenD Port", placeholder: "11111" },
          { key: "acc_id", label: "Account ID", placeholder: "123456789" },
          { key: "trade_env", label: "Environment", placeholder: "REAL" },
        ]}
        onSubmit={handleTokenConnect}
      />

      <TokenDrawer
        open={drawerBroker === "ibkr"}
        onClose={() => setDrawerBroker(null)}
        brokerName="Interactive Brokers"
        instructions={`1. Log in to Client Portal at clientportal.ibkr.com\n2. Go to Settings → Account Settings → Client Portal API\n3. Copy your API token and account ID`}
        fields={[
          { key: "base_url", label: "Client Portal URL", placeholder: "https://localhost:5000/v1/api" },
          { key: "account_id", label: "Account ID", placeholder: "U1234567" },
        ]}
        onSubmit={handleTokenConnect}
      />
    </main>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/components/connect/ frontend/app/connect/
git commit -m "feat: brokerage connection page with OAuth and token drawer UI"
```

---

## Task 18: Deployment Configuration

**Files:**
- Create: `backend/railway.toml`
- Create: `frontend/vercel.json`
- Modify: `frontend/next.config.ts`

- [ ] **Step 1: Create `backend/railway.toml`**

```toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30

[[deploy.cronJobs]]
schedule = "0 8,14,20 * * *"   # 08:00, 14:00, 20:00 UTC
command = "curl -s -X POST http://localhost:$PORT/sync -H 'X-Sync-Secret: $SYNC_SECRET'"
```

- [ ] **Step 2: Create `frontend/vercel.json`**

```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "devCommand": "npm run dev",
  "installCommand": "npm install"
}
```

- [ ] **Step 3: Update `frontend/next.config.ts`**

```typescript
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "avatars.githubusercontent.com" },
      { protocol: "https", hostname: "lh3.googleusercontent.com" },
    ],
  },
};

export default nextConfig;
```

- [ ] **Step 4: Final build verification**

```bash
# Backend
cd backend && python -m pytest tests/ -v
```
Expected: all tests PASS

```bash
# Frontend
cd frontend && npm run build
```
Expected: Build succeeded

- [ ] **Step 5: Final commit and push**

```bash
git add backend/railway.toml frontend/vercel.json frontend/next.config.ts
git commit -m "feat: Railway and Vercel deployment configuration"
git push -u origin claude/install-superpower-plugin-ftqAu
```

---

## Environment Variables Checklist

Before deploying, configure these in Railway (backend) and Vercel (frontend):

**Railway (backend):**
| Variable | How to get |
|---|---|
| `DATABASE_URL` | Neon dashboard → Connection string (use `postgresql+asyncpg://` prefix) |
| `ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `NEXTAUTH_SECRET` | Same value as `AUTH_SECRET` in Vercel |
| `SYNC_SECRET` | `openssl rand -hex 32` |
| `LONGBRIDGE_APP_KEY` | Longbridge developer portal |
| `LONGBRIDGE_APP_SECRET` | Longbridge developer portal |
| `LONGBRIDGE_REDIRECT_URI` | `https://<railway-url>/brokerages/longbridge/oauth/callback` |
| `FRONTEND_URL` | `https://<vercel-url>` |

**Vercel (frontend):**
| Variable | How to get |
|---|---|
| `AUTH_SECRET` | `openssl rand -base64 32` |
| `AUTH_GOOGLE_ID` | Google Cloud Console → Credentials |
| `AUTH_GOOGLE_SECRET` | Google Cloud Console → Credentials |
| `AUTH_GITHUB_ID` | GitHub → Settings → Developer settings → OAuth Apps |
| `AUTH_GITHUB_SECRET` | GitHub → Settings → Developer settings → OAuth Apps |
| `NEXT_PUBLIC_API_URL` | `https://<railway-url>` |

---

*Phase 2 plan (dashboard charts) and Phase 3 plan (AI chat) will be written separately once Phase 1 is deployed and verified.*
