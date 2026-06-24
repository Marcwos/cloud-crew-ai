"""Edgar — Data specialist agent.

Named in honor of Edgar F. Codd, creator of the relational model.
"""
from src.features.crew.domain.agents._base_specialist import BaseSpecialistAgent


class EdgarAgent(BaseSpecialistAgent):
    """Data specialist: storage, databases, caching, and data modeling."""

    @property
    def agent_name(self) -> str:
        return "edgar"

    @property
    def domain(self) -> str:
        return "data"

    @property
    def system_prompt(self) -> str:
        return (
            "You are Edgar, an AWS data specialist named in honor of Edgar F. Codd. "
            "You design storage, database, and caching strategies. "
            "You only recommend data services that exist in the provided catalog. "
            "You must justify every choice with specific data access patterns and trade-offs. "
            "Consider consistency, latency, cost, and operational complexity."
        )
