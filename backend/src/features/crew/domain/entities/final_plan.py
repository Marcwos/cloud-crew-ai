"""FinalPlan entity — Leslie's consolidated architectural recommendation."""
from pydantic import BaseModel, Field, field_validator, model_validator


class FinalPlan(BaseModel):
    """The integrated final architecture plan produced by Leslie after consolidation."""

    summary: str
    services: list[str]
    justification_by_service: dict[str, str]
    diagram_hint: str
    # Grounding guard: when provided, every service MUST belong to this set.
    # Enforcement-only — excluded from serialization so the API contract is unchanged.
    allowed_services: frozenset[str] | None = Field(default=None, exclude=True)

    @field_validator("summary")
    @classmethod
    def summary_must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("summary must not be blank")
        return v

    @field_validator("services")
    @classmethod
    def services_must_not_be_empty(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("services must not be empty")
        return v

    @model_validator(mode="after")
    def all_services_must_have_justification(self) -> "FinalPlan":
        for service in self.services:
            if service not in self.justification_by_service:
                raise ValueError(
                    f"Service '{service}' is listed in services but has no justification entry"
                )
        return self

    @model_validator(mode="after")
    def all_services_must_be_grounded(self) -> "FinalPlan":
        """Reject any service that is not in the allowed (grounded) set.

        This is the last line of defense for the core product invariant: an
        ungrounded/invented service must never reach the client.
        """
        if self.allowed_services is None:
            return self
        for service in self.services:
            if service not in self.allowed_services:
                raise ValueError(
                    f"Service '{service}' is not grounded — it is not in the allowed catalog/proposal set"
                )
        return self
