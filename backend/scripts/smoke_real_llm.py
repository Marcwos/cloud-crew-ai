"""Smoke test against a REAL LLM provider — run before a live demo.

The unit suite mocks every adapter, so the one thing it never exercises is a
real API call whose free-text answer must match the `SERVICES:/RATIONALE:/...`
format the domain parsers expect. This script closes that gap: it runs one full
crew session against the configured provider and reports whether the real model
produced parseable, grounded output — or quietly fell back to defaults.

Usage (from backend/):
    uv run --extra llm-openai python scripts/smoke_real_llm.py
    uv run --extra llm-openai python scripts/smoke_real_llm.py "your own challenge"

Requires a real provider configured via .env or the environment:
    LLM_PROVIDER=openai
    OPENAI_API_KEY=sk-...
    LLM_ORCHESTRATOR_MODEL=... / LLM_SPECIALIST_MODEL=...   (exact model ids)
"""
from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv

# Load backend/.env before reading any config.
load_dotenv()

from src.features.crew.application.use_cases.run_crew_session import CrewSessionDeps
from src.features.crew.infrastructure.events.recording_publisher import RecordingEventPublisher
from src.features.crew.infrastructure.knowledge.curated_catalog import CuratedCatalogKnowledgeSource
from src.features.crew.infrastructure.llm.llm_factory import make_llm_provider
from src.features.crew.infrastructure.orchestration.langgraph_graph import run_graph
from src.features.crew.infrastructure.persistence.in_memory_repo import InMemoryCrewRepository
from src.shared.config import get_llm_provider_name
from src.shared.deps_factory import _api_key_for_provider

DEFAULT_CHALLENGE = (
    "Users upload documents, we process them with AI, and traffic spikes hard "
    "during business hours. Keep costs sane."
)


def _fail(message: str) -> None:
    print(f"\n❌  {message}")
    sys.exit(1)


async def main() -> None:
    challenge = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CHALLENGE
    provider = get_llm_provider_name()

    print(f"Provider : {provider}")
    if provider == "fake":
        _fail(
            "LLM_PROVIDER is 'fake' (or unset) — nothing real to smoke-test.\n"
            "   Set LLM_PROVIDER + the matching *_API_KEY in backend/.env first."
        )

    api_key = _api_key_for_provider(provider, os.environ)
    if provider != "bedrock" and not api_key:
        _fail(f"No API key found for provider '{provider}'. Set its *_API_KEY in .env.")

    print(f"Model(s) : specialist={os.getenv('LLM_SPECIALIST_MODEL') or os.getenv('LLM_MODEL', '(default)')} "
          f"orchestrator={os.getenv('LLM_ORCHESTRATOR_MODEL') or os.getenv('LLM_MODEL', '(default)')}")
    print(f"Challenge: {challenge}\n")

    llm = make_llm_provider(provider, {"api_key": api_key, "region_name": os.getenv("AWS_DEFAULT_REGION")})
    deps = CrewSessionDeps(
        llm=llm,
        knowledge=CuratedCatalogKnowledgeSource(),
        repo=InMemoryCrewRepository(),
        events=RecordingEventPublisher(),
    )

    print("Calling the real model... (this makes billed API calls)\n")
    try:
        session = await run_graph(challenge, deps)
    except Exception as exc:  # noqa: BLE001 — smoke test wants the raw failure
        _fail(f"run_graph raised {type(exc).__name__}: {exc}")

    # --- Report -----------------------------------------------------------
    warnings: list[str] = []

    print("PROPOSALS")
    for p in session.proposals:
        print(f"  [{p.agent}] {', '.join(p.services) or '(none)'}")
        print(f"      rationale: {p.rationale[:90] or '(EMPTY)'}")
        if not p.services:
            warnings.append(f"{p.agent} produced no services")
        if not p.rationale.strip():
            warnings.append(f"{p.agent} produced an empty rationale (parse likely failed)")

    print("\nDEBATE (reviews)")
    if not session.reviews:
        warnings.append("no reviews were produced — the cross-review step yielded nothing")
        print("  (none)")
    for r in session.reviews:
        print(f"  {r.reviewer} -> {r.target_agent}: {r.challenge[:80]}")

    print("\nFINAL PLAN")
    fp = session.final_plan
    if fp is None:
        _fail("final_plan is None — consolidation failed.")
    print(f"  summary : {fp.summary[:100]}")
    print(f"  services: {fp.services}")
    if len(fp.services) < 3:
        warnings.append(
            f"final_plan has only {len(fp.services)} service(s) — likely the grounding "
            "fallback, meaning the model's SERVICES: line didn't parse"
        )

    # --- Verdict ----------------------------------------------------------
    print()
    if warnings:
        print("⚠️  SMOKE PASSED WITH WARNINGS — the model answered but output looks degraded:")
        for w in warnings:
            print(f"   - {w}")
        print("\n   Check the model id and the prompt format before the demo.")
        sys.exit(2)

    print("✅  SMOKE OK — real provider produced parseable, grounded, debated output.")


if __name__ == "__main__":
    asyncio.run(main())
