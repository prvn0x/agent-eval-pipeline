from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.session import engine, Base
import app.db.models  # noqa: F401
from app.api.routes import conversations, evaluations, feedback, suggestions, meta_eval

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Evaluation pipeline for AI agents — scores conversations, detects regressions, and generates improvement suggestions.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(conversations.router)
app.include_router(evaluations.router)
app.include_router(feedback.router)
app.include_router(suggestions.router)
app.include_router(meta_eval.router)


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "llm_enabled": settings.llm_enabled,
    }
