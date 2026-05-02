# Portfolio Tracker Platform — Design Spec
_Date: 2026-05-02_

## Overview

A multi-user web platform that aggregates trading accounts from multiple brokerages into a single analytics dashboard. Users connect their Moomoo, Longbridge, and IBKR accounts, view unified portfolio performance charts, and interact with their data through an AI chat interface powered by their own Claude or OpenAI API key.

---

## Architecture

### Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript |
| Backend | FastAPI (Python) |
| Database | Neon (serverless PostgreSQL) |
| ORM | SQLAlchemy + Alembic (Python) |
| Auth | NextAuth.js v5 — Google + GitHub OAuth |
| Frontend UI | Tailwind CSS + shadcn/ui, dark mode |
| Charting | Recharts |
| Frontend hosting | Vercel |
| Backend hosting | Railway |
| Credential encryption | Python `cryptography` (Fernet) |

### Request Flow

```
User → Next.js (Vercel) → FastAPI (Railway) → Neon DB
                                    ↕
                         Brokerage Adapter Layer
                         (Moomoo / Longbridge / IBKR)
```

### Data Sync Flow

```
Railway Cron (3x daily)
  → Sync endpoint (FastAPI)
    → For each active brokerage_connection:
        → Fetch positions → upsert positions table
        → Fetch new transactions → insert transactions table
        → Snapshot portfolio value → insert portfolio_snapshots
        → Update last_synced_at
        → Write sync_logs entry (success or error)
```

### Auth Flow

- NextAuth.js handles Google/GitHub OAuth on the frontend
- On first login, a `users` row is created
- NextAuth session token is passed as a Bearer token to FastAPI on every API call
- FastAPI validates the token and resolves the user before handling any request

### Phased Build

- **Phase 1:** Auth + DB schema + brokerage connections + data sync engine
- **Phase 2:** Dashboard — line chart + pie chart
- **Phase 3:** AI chat panel

---

## Database Schema

All tables include `user_id` as a foreign key. Row-level data isolation is enforced at the application layer — every query filters by the authenticated user's ID.

**Currency note:** Portfolio values are stored in each account's native currency. In Phase 1, totals and charts display values as-is with currency labels. Cross-currency aggregation (e.g. summing USD + HKD into one number) is out of scope for the initial build.

### `users`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| email | text unique | |
| name | text | |
| avatar_url | text | |
| created_at | timestamptz | |

### `brokerage_connections`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| broker | enum | moomoo, longbridge, ibkr |
| credentials | text | Fernet-encrypted JSON (tokens, API keys) |
| status | enum | active, expired, error |
| last_synced_at | timestamptz | |
| created_at | timestamptz | |

### `accounts`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| connection_id | UUID FK → brokerage_connections | |
| user_id | UUID FK → users | |
| broker_account_id | text | Broker's own account identifier |
| account_type | text | cash, margin, etc. |
| currency | text | Base currency (USD, HKD, etc.) |
| name | text | Display name |

### `positions`
Upsert key: composite unique on `(account_id, ticker)` — each sync replaces the current position for that ticker in that account.

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| account_id | UUID FK → accounts | |
| user_id | UUID FK → users | |
| ticker | text | |
| name | text | |
| quantity | numeric | |
| avg_cost | numeric | |
| current_price | numeric | |
| current_value | numeric | |
| currency | text | |
| asset_class | text | stock, bond, etf, metal, crypto |
| sector | text | Broker-provided; null if unavailable (no enrichment in Phase 1) |
| country | text | Broker-provided; null if unavailable (no enrichment in Phase 1) |
| updated_at | timestamptz | |

### `portfolio_snapshots`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| account_id | UUID FK → accounts | Per-account snapshot |
| total_value | numeric | |
| currency | text | |
| snapshot_at | timestamptz | |

### `transactions`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| account_id | UUID FK → accounts | |
| user_id | UUID FK → users | |
| ticker | text | |
| type | enum | buy, sell |
| quantity | numeric | |
| price | numeric | |
| total_value | numeric | |
| currency | text | |
| executed_at | timestamptz | |
| broker_transaction_id | text | Dedup key — unique per (user_id, broker_transaction_id) |

### `asset_labels`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| name | text | e.g. "Tech", "Dividend Plays" |
| color | text | Hex color for chart rendering |
| created_at | timestamptz | |

### `asset_label_assignments`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| label_id | UUID FK → asset_labels | |
| ticker | text | |
| created_at | timestamptz | |

### `sync_logs`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | |
| connection_id | UUID FK → brokerage_connections | |
| status | enum | success, error |
| error_message | text | Null on success |
| synced_at | timestamptz | |

### `user_ai_settings`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| user_id | UUID FK → users | unique |
| provider | enum | anthropic, openai |
| api_key | text | Fernet-encrypted |
| model | text | e.g. claude-sonnet-4-6, gpt-4o |
| created_at | timestamptz | |

---

## Brokerage Integration Layer

### Adapter Interface

Each broker is wrapped in a Python class implementing a common interface:

```python
class BrokerageAdapter:
    def get_accounts() -> list[Account]
    def get_positions(account_id: str) -> list[Position]
    def get_transactions(account_id: str, since: datetime) -> list[Transaction]
    def get_account_balance(account_id: str) -> AccountBalance
```

### Moomoo Adapter
- SDK: `futu-api` (official Python SDK)
- Auth: Users paste their access token + account ID from the Moomoo/Futu app
- Requires OpenD gateway — users must run this locally or on a cloud VM
- Token stored encrypted in `brokerage_connections.credentials`

### Longbridge Adapter
- SDK: `longbridge` (official Python SDK)
- Auth: OAuth 2.0 — user clicks "Connect", redirected to Longbridge authorization, token stored encrypted
- Token refresh handled automatically before each sync
- MCP server available at `https://openapi.longbridge.com/mcp` (not used in Phase 1; available for future AI tool use)

### IBKR Adapter
- API: Client Portal REST API
- Auth: Users paste their API token from IBKR account management
- Community MCP implementations available for reference (not used in Phase 1)
- Token stored encrypted in `brokerage_connections.credentials`

### Credential Security
- All tokens and API keys encrypted at rest using Fernet symmetric encryption
- Encryption key stored as `ENCRYPTION_KEY` environment variable on Railway
- Never logged, never returned to the frontend

---

## Frontend & UI Design

### Visual Style
- Dark mode only: deep charcoal background (`#0a0a0f`)
- Glassy cards with subtle borders (`rgba(255,255,255,0.06)`)
- Single accent color: indigo/violet (`#6366f1`)
- Typography: clean, modern sans-serif
- Aesthetic references: Linear, Vercel dashboard, Perplexity

### Pages

#### `/` — Landing
- Hero section with platform description
- "Sign in with Google" and "Sign in with GitHub" buttons
- Feature highlights

#### `/dashboard` — Main View
Three vertical zones:

1. **Summary bar** — total portfolio value, daily change ($ and %), last synced timestamp, sync status badge
2. **Line chart** — center focus, ~60% of vertical space
3. **Bottom row** — pie chart (left ~60%) + AI chat panel (right ~40%)

#### `/connect` — Brokerage Connection
- Cards for Moomoo, Longbridge, IBKR showing connected/disconnected state
- Longbridge: "Connect" button triggers OAuth redirect
- Moomoo/IBKR: "Connect" opens a drawer with step-by-step instructions + token input field
- Connected accounts show last sync time and account count

#### `/settings/labels` — Asset Label Manager
- Table of existing labels with color swatches and assigned ticker count
- "New Label" button → name + color picker
- Per-label view: search and assign tickers
- Labels are used for custom grouping in both charts

#### `/settings/ai` — AI Configuration
- Select provider: Anthropic or OpenAI
- Paste API key (masked after save)
- Select model from dropdown (populated based on provider)
- Test connection button

### Line Chart — Controls & Behaviour
- **Y-axis toggle:** % change from the earliest snapshot in the selected time range vs absolute value ($)
- **Time range:** 1W / 1M / 3M / 6M / 1Y / All
- **Split mode:** Total portfolio / By individual stock / By label group / By broker
- **Trade markers:** Buy (▲) and sell (▼) icons on the line at the executed_at timestamp, shown when transaction data is available
- Hovering a marker shows a tooltip: ticker, type, quantity, price

### Pie Chart — Controls & Behaviour
- **Split dropdown:** By asset class / By country / By sector / By label group / By broker
- Hovering a slice shows: category name, value, % of total portfolio
- Legend below the chart with color swatches

### AI Chat Panel
- Collapsible right drawer on the dashboard
- Header shows: provider logo, model name, green/red status dot
- Standard chat thread UI (user bubbles right, AI bubbles left)
- Streaming responses via SSE — tokens appear as they arrive
- If no AI key configured, shows a prompt to visit `/settings/ai`

---

## AI Chat Integration

### Flow
```
User message
  → POST /api/chat (FastAPI)
  → Load user's portfolio context from DB:
      - Current positions (ticker, value, % of portfolio, gain/loss)
      - Portfolio total and change since last snapshot
      - Transactions in last 30 days
      - Asset label groupings
  → Build system prompt with context
  → Forward to Anthropic or OpenAI API using user's own key
  → Stream response back via SSE
```

### System Prompt Structure
```
You are a portfolio analyst assistant. The user's current portfolio data is below.
Answer questions about their holdings, performance, allocation, and risk.
Do not suggest specific trades or provide financial advice.

[PORTFOLIO CONTEXT]
Total value: $X
Change today: +$Y (+Z%)
Positions: [list]
Recent transactions: [list]
Label groups: [list]
```

### Constraints
- Read-only: the AI cannot place orders or modify any data
- No tool use that touches brokerage APIs
- User's API key is used directly — platform never shares a key across users
- Model selection stored in `user_ai_settings.model`

---

## Error Handling

### Brokerage Sync Failures
- All sync attempts logged in `sync_logs`
- Failed syncs: connection status set to `error`, dashboard shows warning badge with last successful sync time
- Stale data is still displayed — failure never blanks the dashboard
- Expired tokens: connection status set to `expired`, user shown a reconnect banner

### Token Refresh
- Longbridge: OAuth token refreshed automatically before each sync attempt
- Moomoo/IBKR: static tokens — on failure, connection marked `expired` and user notified

### AI Chat Errors
- Invalid/expired API key → clear inline error in chat UI with link to `/settings/ai`
- API timeout or rate limit → user-friendly error message in the chat thread
- No data available → AI responds with a note that no portfolio data is loaded yet

---

## Testing Strategy

### Backend (pytest)
- Unit tests for each brokerage adapter using mocked API responses
- Schema validation on normalized position/transaction data
- Prompt-building logic tested with fixture portfolio data
- Sync job logic tested end-to-end with mocked adapters

### Frontend (Playwright)
- Connect a brokerage (mock OAuth flow)
- Dashboard renders with fixture data
- Chart controls toggle correctly
- AI chat sends and receives a message

### Not tested
- AI response quality (non-deterministic)
- Live brokerage API calls in CI (use sandbox/mock only)
