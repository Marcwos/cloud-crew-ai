"""Live SSE integration tests — exercise the REAL SSEEventPublisher path.

The other contract tests (test_api_contract.py) use RecordingEventPublisher,
which falls back to replaying stored events AFTER the run completes. That path
hides two bugs that only appear with the real live-streaming adapter:

  Bug 1 — session_id mismatch: run_graph minted its own id, so events were
          published to a queue keyed by an id the client never received.
  Bug 2 — live-stream 404 race: the session was only persisted AFTER the run
          finished, so GET /events 404'd while the crew was working.

These tests wire a real SSEEventPublisher via dependency override and assert
the client can attach to the live stream using the returned id and receive a
non-empty event sequence ending in leslie/done.
"""
from __future__ import annotations

import asyncio
import json

import pytest
from httpx import ASGITransport, AsyncClient

from src.features.crew.application.use_cases.run_crew_session import CrewSessionDeps
from src.features.crew.infrastructure.events.sse_event_publisher import SSEEventPublisher
from src.features.crew.infrastructure.knowledge.curated_catalog import (
    CuratedCatalogKnowledgeSource,
)
from src.features.crew.infrastructure.llm.fake_llm_provider import FakeLLMProvider
from src.features.crew.infrastructure.persistence.in_memory_repo import (
    InMemoryCrewRepository,
)


def _live_deps() -> CrewSessionDeps:
    """Deps wired with the REAL SSE publisher (fake LLM/knowledge/repo)."""
    return CrewSessionDeps(
        llm=FakeLLMProvider(),
        knowledge=CuratedCatalogKnowledgeSource(),
        repo=InMemoryCrewRepository(),
        events=SSEEventPublisher(),
    )


@pytest.fixture
async def live_client():
    from src.main import create_app

    app = create_app()
    app.state.deps = _live_deps()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


def _parse_sse(body: str) -> list[dict]:
    events: list[dict] = []
    for line in body.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


class TestLiveSSEStream:
    """(a) The live stream keyed to the returned id yields events ending in done."""

    async def test_live_stream_yields_events_ending_in_leslie_done(self, live_client):
        resp = await live_client.post(
            "/api/sessions", json={"challenge": "Serverless image pipeline"}
        )
        assert resp.status_code == 201
        session_id = resp.json()["session_id"]

        # Attach to the LIVE stream using the id the client received.
        # The background run publishes events into the same queue.
        stream_resp = await live_client.get(f"/api/sessions/{session_id}/events")
        assert stream_resp.status_code == 200
        assert "text/event-stream" in stream_resp.headers["content-type"]

        parsed = _parse_sse(stream_resp.text)
        assert len(parsed) > 0, "Live stream was empty — events keyed to wrong id"

        last = parsed[-1]
        assert last["agent"] == "leslie"
        assert last["action"] == "done"

    async def test_live_stream_covers_all_agents(self, live_client):
        resp = await live_client.post(
            "/api/sessions", json={"challenge": "Multi-region data platform"}
        )
        session_id = resp.json()["session_id"]

        stream_resp = await live_client.get(f"/api/sessions/{session_id}/events")
        parsed = _parse_sse(stream_resp.text)

        agents = {e["agent"] for e in parsed}
        assert {"leslie", "alan", "edgar", "hedy", "grace", "vint"}.issubset(agents)


class TestPlaceholderPersistence:
    """(b) The session must exist immediately after POST (no 404 race)."""

    async def test_get_session_does_not_404_immediately_after_post(self, live_client):
        resp = await live_client.post(
            "/api/sessions", json={"challenge": "Event-driven order system"}
        )
        session_id = resp.json()["session_id"]

        # Without yielding to the event loop, the background run may not have
        # touched the repo yet — the placeholder must already be there.
        get_resp = await live_client.get(f"/api/sessions/{session_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["session_id"] == session_id

    async def test_events_endpoint_does_not_404_immediately_after_post(self, live_client):
        resp = await live_client.post(
            "/api/sessions", json={"challenge": "Streaming analytics"}
        )
        session_id = resp.json()["session_id"]

        stream_resp = await live_client.get(f"/api/sessions/{session_id}/events")
        assert stream_resp.status_code == 200

    async def test_final_plan_present_after_run_completes(self, live_client):
        resp = await live_client.post(
            "/api/sessions", json={"challenge": "Realtime chat backend"}
        )
        session_id = resp.json()["session_id"]

        # Draining the live stream guarantees the run reached leslie/done.
        await live_client.get(f"/api/sessions/{session_id}/events")

        data = None
        for _ in range(40):
            get_resp = await live_client.get(f"/api/sessions/{session_id}")
            if get_resp.status_code == 200 and get_resp.json().get("final_plan"):
                data = get_resp.json()
                break
            await asyncio.sleep(0.05)

        assert data is not None, "final_plan never populated"
        assert data["final_plan"]["summary"] != ""
        assert len(data["final_plan"]["services"]) >= 1
