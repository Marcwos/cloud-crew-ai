"""Vint — Networking specialist agent.

Named in honor of Vint Cerf, co-creator of TCP/IP.
"""
from src.features.crew.domain.agents._base_specialist import BaseSpecialistAgent


class VintAgent(BaseSpecialistAgent):
    """Networking specialist: connectivity, event routing, messaging, and CDN."""

    @property
    def agent_name(self) -> str:
        return "vint"

    @property
    def domain(self) -> str:
        return "networking"

    @property
    def system_prompt(self) -> str:
        return (
            "You are Vint, an AWS networking specialist named in honor of Vint Cerf. "
            "You design network topology, event routing, messaging, and content delivery. "
            "You only recommend networking services that exist in the provided catalog. "
            "Consider decoupling, resilience, latency, and throughput. "
            "Justify every networking decision and explain what coupling or latency risk it solves."
        )
