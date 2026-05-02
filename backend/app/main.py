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
