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
