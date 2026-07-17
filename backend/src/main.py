"""Composition root — creates the FastAPI app, wires dependencies, mounts routes.

Usage:
    uvicorn src.main:app --reload --port 8000

Environment variables:
    LLM_PROVIDER   - 'fake' (default), 'anthropic', 'openai', 'deepseek', 'bedrock'
    ANTHROPIC_API_KEY / OPENAI_API_KEY / DEEPSEEK_API_KEY  — provider credentials
    AWS_DEFAULT_REGION — for Bedrock adapter
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Load backend/.env (LLM_PROVIDER, *_API_KEY, ...) into the environment before
# config is read. Without this, dropping a .env in place is a silent no-op and
# the app quietly stays in fake mode. Real env vars already set win over .env.
load_dotenv()

from src.features.crew.interface.routes import router
from src.shared.deps_factory import build_deps


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build and store dependencies at startup."""
    app.state.deps = build_deps()
    yield
    # Cleanup (none required for in-memory adapters)


def create_app() -> FastAPI:
    """App factory — creates and configures the FastAPI instance."""
    app = FastAPI(
        title="Cloud Crew AI",
        description="Multiagent AWS architecture advisor",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Permissive CORS for local Vite dev server
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api")

    return app


# Module-level app instance consumed by uvicorn
app = create_app()
