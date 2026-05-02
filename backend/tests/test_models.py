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
    constraint_names = [c.name for c in Position.__table__.constraints]
    assert "ix_positions_account_ticker" in constraint_names
