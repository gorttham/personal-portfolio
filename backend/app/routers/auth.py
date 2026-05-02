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
