"""
FastAPI application entry point.
Sets up CORS, routes, lifespan events, and exception handlers.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.database.session import init_db
from app.api.research import router as research_router
from app.api.websocket import router as ws_router
from app.api.export import router as export_router
from app.logging.logger import setup_logging
from app.errors.base import ResearchException
from app.config.settings import settings


# ─── Lifespan ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    setup_logging()
    await init_db()
    yield
    # Cleanup on shutdown (if needed)


# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Multi-Agent AI Research Platform",
    description=(
        "Autonomous AI research analyst — enter a query, receive a professional report "
        "with charts, citations, and PDF export."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Routes ───────────────────────────────────────────────────────────────────
app.include_router(research_router)
app.include_router(ws_router)
app.include_router(export_router)


# ─── Exception handlers ───────────────────────────────────────────────────────
@app.exception_handler(ResearchException)
async def research_exception_handler(request: Request, exc: ResearchException):
    return JSONResponse(
        status_code=500,
        content=exc.to_dict(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "InternalServerError", "message": str(exc)},
    )


# ─── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health_check():
    return {
        "status": "healthy",
        "version": "1.0.0",
        "model": settings.GEMINI_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
    }


@app.get("/", tags=["system"])
async def root():
    return {
        "name": "Multi-Agent AI Research Platform",
        "docs": "/docs",
        "health": "/health",
        "version": "1.0.0",
    }
