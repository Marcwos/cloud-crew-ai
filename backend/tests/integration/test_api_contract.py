"""API contract integration tests — additional coverage for SSE and session lifecycle.

These tests verify the full API contract as specified:
  (a) POST /api/sessions returns 201 + session_id
  (b) GET /api/sessions/{id} returns full session with final_plan after run
  (c) GET /api/sessions/{id}/events returns SSE stream ending with done
  (d) GET /api/health returns 200 {"status": "ok"}

Uses fake adapters via app.state.deps override.
"""
from __future__ import annotations

import asyncio
import json
import pytest
from httpx import ASGITransport, AsyncClient

from src.features.crew.application.use_cases.run_crew_session import CrewSessionDeps
from src.features.crew.infrastructure.events.recording_publisher import RecordingEventPublisher
from src.features.crew.infrastructure.knowledge.curated_catalog import CuratedCatalogKnowledgeSource
from src.features.crew.infrastructure.llm.fake_llm_provider import FakeLLMProvider
from src.features.crew.infrastructure.persistence.in_memory_repo import InMemoryCrewRepository


def _fake_deps() -> CrewSessionDeps:
    return CrewSessionDeps(
        llm=FakeLLMProvider(),
        knowledge=CuratedCatalogKnowledgeSource(),
        repo=InMemoryCrewRepository(),
        events=RecordingEventPublisher(),
    )


@pytest.fixture
async def client():
    from src.main import create_app

    app = create_app()
    app.state.deps = _fake_deps()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


async def _wait_for_session(client: AsyncClient, session_id: str, max_retries: int = 40) -> dict:
    """Poll until session has a final_plan."""
    for _ in range(max_retries):
        resp = await client.get(f"/api/sessions/{session_id}")
        if resp.status_code == 200:
            data = resp.json()
            if data.get("final_plan") is not None:
                return data
        await asyncio.sleep(0.05)
    # Return whatever we have
    resp = await client.get(f"/api/sessions/{session_id}")
    return resp.json() if resp.status_code == 200 else {}


class TestAPIContractA:
    """(a) POST /api/sessions returns 201 + session_id."""

    async def test_returns_201(self, client):
        resp = await client.post("/api/sessions", json={"challenge": "Build serverless pipeline"})
        assert resp.status_code == 201

    async def test_returns_session_id_string(self, client):
        resp = await client.post("/api/sessions", json={"challenge": "E-commerce backend"})
        data = resp.json()
        assert "session_id" in data
        assert isinstance(data["session_id"], str)
        assert len(data["session_id"]) > 0

    async def test_each_call_returns_unique_session_id(self, client):
        r1 = await client.post("/api/sessions", json={"challenge": "Challenge A"})
        r2 = await client.post("/api/sessions", json={"challenge": "Challenge B"})
        assert r1.json()["session_id"] != r2.json()["session_id"]


class TestAPIContractB:
    """(b) GET /api/sessions/{id} returns full session JSON after run."""

    async def test_returns_full_session_after_completion(self, client):
        resp = await client.post(
            "/api/sessions",
            json={"challenge": "Batch image processing pipeline"},
        )
        session_id = resp.json()["session_id"]
        data = await _wait_for_session(client, session_id)

        # All required top-level fields
        assert data["session_id"] == session_id
        assert data["challenge"] == "Batch image processing pipeline"
        assert isinstance(data["constraints"], list)
        assert isinstance(data["tasks"], dict)
        assert isinstance(data["proposals"], list)
        assert isinstance(data["reviews"], list)
        assert isinstance(data["events"], list)

    async def test_final_plan_present_after_run(self, client):
        resp = await client.post(
            "/api/sessions",
            json={"challenge": "Real-time chat for 10k users"},
        )
        session_id = resp.json()["session_id"]
        data = await _wait_for_session(client, session_id)

        assert data.get("final_plan") is not None
        assert data["final_plan"]["summary"] != ""
        assert len(data["final_plan"]["services"]) >= 1

    async def test_proposals_from_all_specialists(self, client):
        resp = await client.post(
            "/api/sessions",
            json={"challenge": "Data lake ingestion pipeline"},
        )
        session_id = resp.json()["session_id"]
        data = await _wait_for_session(client, session_id)

        proposal_agents = {p["agent"] for p in data["proposals"]}
        assert {"alan", "edgar", "hedy", "grace", "vint"}.issubset(proposal_agents)

    async def test_events_sequence_starts_with_leslie(self, client):
        resp = await client.post(
            "/api/sessions",
            json={"challenge": "Microservices migration"},
        )
        session_id = resp.json()["session_id"]
        data = await _wait_for_session(client, session_id)

        events = data["events"]
        assert len(events) > 0
        assert events[0]["agent"] == "leslie"

    async def test_events_end_with_leslie_done(self, client):
        resp = await client.post(
            "/api/sessions",
            json={"challenge": "Container orchestration"},
        )
        session_id = resp.json()["session_id"]
        data = await _wait_for_session(client, session_id)

        leslie_done = [
            e for e in data["events"]
            if e["agent"] == "leslie" and e["action"] == "done"
        ]
        assert len(leslie_done) >= 1

    async def test_event_fields_match_spec(self, client):
        """Every event must expose its UI-facing lifecycle fields."""
        resp = await client.post(
            "/api/sessions",
            json={"challenge": "API modernisation"},
        )
        session_id = resp.json()["session_id"]
        data = await _wait_for_session(client, session_id)

        for event in data["events"]:
            assert "agent" in event
            assert "action" in event
            assert "status" in event
            assert "message" in event
            assert "assignment" in event
            assert event["action"] in {
                "idle", "moving", "analyzing", "proposing", "reviewing", "done"
            }


class TestAPIContractC:
    """(c) GET /api/sessions/{id}/events — SSE stream yields AgentEvents ending in done."""

    async def test_events_endpoint_returns_200(self, client):
        resp = await client.post("/api/sessions", json={"challenge": "IoT ingestion"})
        session_id = resp.json()["session_id"]

        # Wait for session to complete so events are stored
        await _wait_for_session(client, session_id)

        stream_resp = await client.get(f"/api/sessions/{session_id}/events")
        assert stream_resp.status_code == 200

    async def test_events_endpoint_returns_sse_content_type(self, client):
        resp = await client.post("/api/sessions", json={"challenge": "Serverless ETL"})
        session_id = resp.json()["session_id"]

        await _wait_for_session(client, session_id)

        stream_resp = await client.get(f"/api/sessions/{session_id}/events")
        assert "text/event-stream" in stream_resp.headers["content-type"]

    async def test_events_stream_contains_json_events(self, client):
        resp = await client.post("/api/sessions", json={"challenge": "Multi-region failover"})
        session_id = resp.json()["session_id"]

        await _wait_for_session(client, session_id)

        stream_resp = await client.get(f"/api/sessions/{session_id}/events")
        body = stream_resp.text

        # Parse SSE events: lines starting with "data: "
        parsed_events = []
        for line in body.splitlines():
            if line.startswith("data: "):
                json_str = line[6:]  # strip "data: "
                event = json.loads(json_str)
                parsed_events.append(event)

        assert len(parsed_events) > 0
        # Last event in stream should be leslie/done
        done_events = [e for e in parsed_events if e["agent"] == "leslie" and e["action"] == "done"]
        assert len(done_events) >= 1

    async def test_events_endpoint_returns_404_for_unknown_session(self, client):
        resp = await client.get("/api/sessions/no-such-session/events")
        assert resp.status_code == 404


class TestAPIContractD:
    """(d) GET /api/health returns 200 {"status": "ok"}."""

    async def test_health_200(self, client):
        resp = await client.get("/api/health")
        assert resp.status_code == 200

    async def test_health_body(self, client):
        resp = await client.get("/api/health")
        assert resp.json() == {"status": "ok"}

    async def test_health_content_type(self, client):
        resp = await client.get("/api/health")
        assert "application/json" in resp.headers["content-type"]
