"""FinalPlan entity — Leslie's consolidated architectural recommendation."""
from pydantic import BaseModel, field_validator, model_validator


class FinalPlan(BaseModel):
    """The integrated final architecture plan produced by Leslie after consolidation."""

    summary: str
    services: list[str]
    justification_by_service: dict[str, str]
    diagram_hint: str

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
