from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, audit, hospitals, knowledge, protocols, users, ehr, campaigns, scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    # Future: warm connections, initialise RAG index, etc.
    yield
    # Cleanup if needed


def create_app() -> FastAPI:
    app = FastAPI(
        title="Multi-Hospital Post-Discharge Outreach Platform",
        description=(
            "Phase 1 — Foundation: multi-tenant hospital management, "
            "JWT authentication, protocol management, tenant isolation, and audit logging."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------ #
    # CORS                                                                 #
    # ------------------------------------------------------------------ #
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Tighten in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------ #
    # Routers                                                              #
    # ------------------------------------------------------------------ #
    PREFIX = "/api/v1"

    app.include_router(auth.router, prefix=PREFIX)
    app.include_router(hospitals.router, prefix=PREFIX)
    app.include_router(users.router, prefix=PREFIX)
    app.include_router(protocols.router, prefix=PREFIX)
    app.include_router(knowledge.router, prefix=PREFIX)
    app.include_router(audit.router, prefix=PREFIX)
    app.include_router(ehr.router, prefix=PREFIX)
    app.include_router(campaigns.router, prefix=PREFIX)
    app.include_router(scheduler.router, prefix=PREFIX)

    # ------------------------------------------------------------------ #
    # Health check                                                         #
    # ------------------------------------------------------------------ #
    @app.get("/health", tags=["System"])
    async def health_check() -> dict:
        return {"status": "ok", "version": "1.0.0"}

    return app


app = create_app()
