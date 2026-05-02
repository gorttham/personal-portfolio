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
