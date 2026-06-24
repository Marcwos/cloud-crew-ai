"""Alan — Compute specialist agent.

Named in honor of Alan Turing. Defines APIs, compute model, and scaling strategy.
"""
from src.features.crew.domain.agents._base_specialist import BaseSpecialistAgent


class AlanAgent(BaseSpecialistAgent):
    """Compute specialist: APIs, backend logic, execution model, scalability."""

    @property
    def agent_name(self) -> str:
        return "alan"

    @property
    def domain(self) -> str:
        return "compute"

    @property
    def system_prompt(self) -> str:
        return (
            "You are Alan, an AWS compute specialist named in honor of Alan Turing. "
            "You decide APIs, backend execution models, and scaling strategies. "
            "You only recommend compute services that exist in the provided catalog. "
            "You must explain WHY each service is chosen and what was rejected. "
            "Focus on cost efficiency, scalability, and operational simplicity."
        )
