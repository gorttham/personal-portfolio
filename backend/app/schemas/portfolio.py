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
    broker: str
    credentials: dict


class LongbridgeOAuthCallbackRequest(BaseModel):
    code: str
    state: str
