"""ServiceFact value object — truth about an AWS service, from KnowledgeSource."""
from pydantic import BaseModel, field_validator


class ServiceFact(BaseModel, frozen=True):
    """An immutable record describing a real AWS service from the curated catalog."""

    name: str
    category: str
    when_to_use: str
    source: str

    @field_validator("name", "category", "when_to_use", "source")
    @classmethod
    def must_not_be_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("field must not be blank")
        return v
