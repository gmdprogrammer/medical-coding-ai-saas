"""
Medical Coding AI — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from loguru import logger
from sqlalchemy.exc import OperationalError, DBAPIError

from app.config import get_settings
from app.models.database import create_tables
from app.services.vector_store import get_vector_store
from app.middleware.phi_middleware import PHIGuardMiddleware
from app.api.routes import auth_router, coding_router, admin_router

settings = get_settings()

# Track DB availability for health endpoint
_db_available = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize heavyweight singletons once at startup.
    DB and vector store failures are non-fatal in dev mode — the server
    starts so other services / health checks remain reachable.
    """
    global _db_available
    logger.info("Starting Medical Coding AI backend...")

    # ── Database ──────────────────────────────────────────────────────────────
    try:
        await create_tables()
        _db_available = True
        logger.info("Database tables created/verified")
    except Exception as exc:
        _db_available = False
        if settings.is_production:
            raise RuntimeError(f"Database unavailable in production: {exc}") from exc
        logger.warning(
            f"Database unavailable — running in limited mode: {exc}\n"
            "Start PostgreSQL or set DATABASE_URL to a local instance."
        )

    # ── Vector Store ──────────────────────────────────────────────────────────
    try:
        vs = get_vector_store()
        logger.info(f"Vector store ready — {vs.total_documents} documents indexed")
    except Exception as exc:
        logger.warning(f"Vector store init failed (non-fatal): {exc}")

    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Medical Coding AI",
    description="HIPAA-aligned ICD-10 & CPT coding assistant powered by Groq LLM + RAG",
    version=settings.app_version,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── Middleware (order matters — applied bottom-up) ─────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(PHIGuardMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global exception handlers ─────────────────────────────────────────────────

@app.exception_handler(OperationalError)
@app.exception_handler(DBAPIError)
async def db_unavailable_handler(request: Request, exc: Exception):
    logger.error(f"Database error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Database unavailable. Please ensure PostgreSQL is running.",
            "hint": "Run: docker-compose up postgres  OR set DATABASE_URL in .env",
        },
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """
    Catch-all handler that turns DB connection errors (socket.gaierror,
    asyncpg ConnectionFailureError, etc.) into clean 503 responses.
    """
    exc_str = str(exc).lower()
    db_keywords = ("getaddrinfo", "connection refused", "connect call failed",
                   "could not connect", "database", "asyncpg", "postgresql")
    if any(kw in exc_str for kw in db_keywords) or isinstance(exc, OSError):
        logger.error(f"DB connection failure on {request.url.path}: {exc}")
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Database unavailable. Please ensure PostgreSQL is running.",
                "hint": "Run: docker-compose up postgres  OR set DATABASE_URL in .env",
            },
        )
    # Re-raise truly unexpected errors as 500
    logger.exception(f"Unhandled error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check server logs."},
    )


# ── Prometheus metrics ─────────────────────────────────────────────────────────
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# ── Routers ────────────────────────────────────────────────────────────────────
API_V1 = "/api/v1"
app.include_router(auth_router, prefix=API_V1)
app.include_router(coding_router, prefix=API_V1)
app.include_router(admin_router, prefix=API_V1)


@app.get("/health", tags=["Health"])
async def health_check():
    vs = get_vector_store()
    return {
        "status": "healthy",
        "version": settings.app_version,
        "database_available": _db_available,
        "vector_store_documents": vs.total_documents,
    }
