"""Grace — Monitoring and Cost specialist agent.

Named in honor of Grace Hopper.
"""
from src.features.crew.domain.agents._base_specialist import BaseSpecialistAgent


class GraceAgent(BaseSpecialistAgent):
    """Monitoring and cost specialist: observability, budgets, and financial optimization."""

    @property
    def agent_name(self) -> str:
        return "grace"

    @property
    def domain(self) -> str:
        return "monitoring_cost"

    @property
    def system_prompt(self) -> str:
        return (
            "You are Grace, an AWS monitoring and cost specialist named in honor of Grace Hopper. "
            "You evaluate observability needs, budget constraints, and cost optimization. "
            "You only recommend monitoring/cost services that exist in the provided catalog. "
            "You are the voice that questions spending — always challenge assumptions about cost. "
            "Justify every tool chosen and what cost or visibility risk it addresses."
        )
