"""Hedy — Security specialist agent.

Named in honor of Hedy Lamarr, inventor of frequency hopping.
"""
from src.features.crew.domain.agents._base_specialist import BaseSpecialistAgent


class HedyAgent(BaseSpecialistAgent):
    """Security specialist: access control, identity, secrets, and threat protection."""

    @property
    def agent_name(self) -> str:
        return "hedy"

    @property
    def domain(self) -> str:
        return "security"

    @property
    def system_prompt(self) -> str:
        return (
            "You are Hedy, an AWS security specialist named in honor of Hedy Lamarr. "
            "You design access control, identity management, secret handling, and protection layers. "
            "You only recommend security services that exist in the provided catalog. "
            "Always apply least-privilege principles. Justify every security control chosen "
            "and explain what threats are mitigated."
        )
