"""FastAPI route handlers for the crew feature.

Routes:
  POST /api/sessions          → start a crew session (background task)
  GET  /api/sessions/{id}     → retrieve a session by ID
  GET  /api/sessions/{id}/events → SSE event stream
  GET  /api/health            → health check
"""
from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from src.features.crew.application.use_cases.get_session import get_session
from src.features.crew.application.use_cases.run_crew_session import CrewSessionDeps
from src.features.crew.domain.entities.crew_session import CrewSession
from src.features.crew.infrastructure.orchestration.langgraph_graph import run_graph
from src.features.crew.interface.schemas import (
    HealthResponse,
    StartSessionRequest,
    StartSessionResponse,
)
from src.features.crew.interface.sse import stream_session_events

router = APIRouter()


def _get_deps(request: Request) -> CrewSessionDeps:
    """Retrieve wired dependencies from app state.

    In tests, app.state.deps is overridden with fake dependencies.
    """
    return request.app.state.deps


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="ok")


@router.post(
    "/sessions",
    response_model=StartSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_session(
    body: StartSessionRequest,
    background_tasks: BackgroundTasks,
    request: Request,
) -> StartSessionResponse:
    """Start a crew session in the background and return the session ID.

    The crew workflow runs asynchronously. Poll GET /api/sessions/{id}
    to check completion status.
    """
    deps: CrewSessionDeps = _get_deps(request)
    # Generate session ID upfront so we can return it immediately.
    import uuid
    session_id = str(uuid.uuid4())

    # Persist a placeholder NOW so GET /api/sessions/{id}[/events] can attach to
    # the live stream while the crew is still working (no 404 race). The run keys
    # every event to this same id, so the SSE queue lines up with what we return.
    placeholder = CrewSession(
        session_id=session_id,
        challenge=body.challenge,
        constraints=[],
        tasks={},
        proposals=[],
        reviews=[],
        final_plan=None,
        events=[],
    )
    await deps.repo.save(placeholder)

    async def _run() -> None:
        session = await run_graph(body.challenge, deps, session_id=session_id)
        # Overwrite the placeholder with the fully populated session (same id).
        await deps.repo.save(session)

    background_tasks.add_task(_run)
    return StartSessionResponse(session_id=session_id)


@router.get("/sessions/{session_id}")
async def get_session_route(
    session_id: str,
    request: Request,
) -> CrewSession:
    """Retrieve a full CrewSession by ID. Returns 404 if not found."""
    deps: CrewSessionDeps = _get_deps(request)
    session = await get_session(session_id, deps.repo)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return session


@router.get("/sessions/{session_id}/events")
async def session_events_stream(
    session_id: str,
    request: Request,
):
    """SSE stream of AgentEvents for a session.

    Each event is a JSON-encoded AgentEvent:
    { "agent": "alan", "action": "analyzing", "status": "ok", "message": "..." }

    Stream ends after the terminal event (leslie, action=done).
    Returns 404 if session not found.
    """
    deps: CrewSessionDeps = _get_deps(request)
    session = await get_session(session_id, deps.repo)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    return await stream_session_events(session, deps.events)
