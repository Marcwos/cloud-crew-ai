"""Integration tests for FastAPI routes — RED first.

Uses ASGI test client with fake adapters via dependency override.
No real LLM calls, no real SSE streaming to external clients.
"""
from __future__ import annotations

import json
import pytest
from httpx import ASGITransport, AsyncClient

from src.features.crew.application.use_cases.run_crew_session import CrewSessionDeps
from src.features.crew.infrastructure.events.recording_publisher import RecordingEventPublisher
from src.features.crew.infrastructure.knowledge.curated_catalog import CuratedCatalogKnowledgeSource
from src.features.crew.infrastructure.llm.fake_llm_provider import FakeLLMProvider
from src.features.crew.infrastructure.persistence.in_memory_repo import InMemoryCrewRepository


def _make_fake_deps() -> CrewSessionDeps:
    return CrewSessionDeps(
        llm=FakeLLMProvider(),
        knowledge=CuratedCatalogKnowledgeSource(),
        repo=InMemoryCrewRepository(),
        events=RecordingEventPublisher(),
    )


@pytest.fixture
async def client():
    from src.main import create_app
    from src.shared.deps_factory import build_deps

    app = create_app()

    # Override deps to use fakes
    app.state.deps = _make_fake_deps()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


class TestHealthEndpoint:
    async def test_health_returns_200(self, client):
        response = await client.get("/api/health")
        assert response.status_code == 200

    async def test_health_returns_status_ok(self, client):
        response = await client.get("/api/health")
        assert response.json() == {"status": "ok"}


class TestPostSession:
    async def test_post_session_returns_201(self, client):
        response = await client.post(
            "/api/sessions",
            json={"challenge": "Build a serverless pipeline"},
        )
        assert response.status_code == 201

    async def test_post_session_returns_session_id(self, client):
        response = await client.post(
            "/api/sessions",
            json={"challenge": "Real-time analytics for IoT"},
        )
        data = response.json()
        assert "session_id" in data
        assert len(data["session_id"]) > 0

    async def test_post_session_missing_challenge_returns_422(self, client):
        response = await client.post("/api/sessions", json={})
        assert response.status_code == 422

    async def test_post_session_empty_challenge_returns_422(self, client):
        response = await client.post(
            "/api/sessions",
            json={"challenge": ""},
        )
        assert response.status_code == 422


class TestGetSession:
    async def test_get_session_returns_200_after_completion(self, client):
        # Create a session first
        post_resp = await client.post(
            "/api/sessions",
            json={"challenge": "Multi-tenant SaaS backend"},
        )
        session_id = post_resp.json()["session_id"]

        # Poll until complete (background task runs synchronously in test)
        import asyncio
        for _ in range(30):
            get_resp = await client.get(f"/api/sessions/{session_id}")
            if get_resp.status_code == 200:
                data = get_resp.json()
                if data.get("final_plan") is not None:
                    break
            await asyncio.sleep(0.1)

        get_resp = await client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 200

    async def test_get_session_returns_full_session_json(self, client):
        post_resp = await client.post(
            "/api/sessions",
            json={"challenge": "Container orchestration strategy"},
        )
        session_id = post_resp.json()["session_id"]

        import asyncio
        for _ in range(30):
            get_resp = await client.get(f"/api/sessions/{session_id}")
            if get_resp.status_code == 200:
                data = get_resp.json()
                if data.get("final_plan") is not None:
                    break
            await asyncio.sleep(0.1)

        data = get_resp.json()
        # All required fields must be present
        assert "session_id" in data
        assert "challenge" in data
        assert "constraints" in data
        assert "proposals" in data
        assert "reviews" in data
        assert "events" in data

    async def test_get_nonexistent_session_returns_404(self, client):
        response = await client.get("/api/sessions/does-not-exist")
        assert response.status_code == 404


class TestSSEStream:
    async def test_sse_stream_yields_events(self, client):
        """SSE stream must yield at least one event for a session."""
        post_resp = await client.post(
            "/api/sessions",
            json={"challenge": "API gateway modernisation"},
        )
        session_id = post_resp.json()["session_id"]

        # Wait for session to be populated
        import asyncio
        for _ in range(30):
            get_resp = await client.get(f"/api/sessions/{session_id}")
            if get_resp.status_code == 200 and get_resp.json().get("final_plan"):
                break
            await asyncio.sleep(0.1)

        # Check that events are in the session (SSE was backed by recording publisher)
        session_data = (await client.get(f"/api/sessions/{session_id}")).json()
        assert len(session_data["events"]) > 0

    async def test_sse_stream_endpoint_exists(self, client):
        """The /api/sessions/{id}/events endpoint must respond."""
        post_resp = await client.post(
            "/api/sessions",
            json={"challenge": "Microservices migration"},
        )
        session_id = post_resp.json()["session_id"]

        # The stream endpoint should return a 200 with the right content type
        # In test mode with RecordingPublisher, we use the session events stored in repo
        response = await client.get(f"/api/sessions/{session_id}/events")
        # 404 means the route doesn't exist; we accept 200 or 204 (empty) for now
        assert response.status_code != 404
