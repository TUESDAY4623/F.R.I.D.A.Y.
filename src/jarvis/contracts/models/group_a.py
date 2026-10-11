"""
Group A contracts: Input & Intent layer.

Models:
- Request: Structured output of the Input Processor.
- LayaClassification: Laya's raw semantic classification.
- Intent: Normalized, canonical intent from the Intent Manager.
- ExtractedEntity: An entity extracted from the user's request.
- Enums: EntityType, RequestCharacteristic, LayaCategory.
"""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from jarvis.contracts.models.base import JarvisBaseModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EntityType(StrEnum):
    """Types of entities that can be extracted from user requests."""

    FILE_PATH = "file_path"
    APP_NAME = "app_name"
    URL = "url"
    PERSON = "person"
    EMAIL = "email"
    DATE = "date"
    TIME = "time"
    LOCATION = "location"
    NUMBER = "number"
    ORGANIZATION = "organization"
    PRODUCT = "product"
    COMMAND = "command"


class RequestCharacteristic(StrEnum):
    """Characteristics of a user request identified by Laya."""

    MULTI_STEP = "multi-step"
    EXTERNAL_DATA = "external-data"
    REQUIRES_CONFIRMATION = "requires-confirmation"
    READ_ONLY = "read-only"
    DESTRUCTIVE = "destructive"
    TIME_SENSITIVE = "time-sensitive"
    AMBIGUOUS = "ambiguous"


class LayaCategory(StrEnum):
    """Semantic intent categories identified by Laya."""

    INFORMATIONAL = "informational"
    ACTIONABLE = "actionable"
    QUERY = "query"
    COMMAND = "command"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Request(JarvisBaseModel):
    """Structured output of the Input Processor.

    This is the first structured representation of the user's request
    in the Jarvis pipeline. It is passed to Laya for classification.
    """

    id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for this request.",
    )
    raw_input: str = Field(
        ...,
        min_length=1,
        description="Original user input text, unmodified.",
    )
    normalized_input: str = Field(
        ...,
        min_length=1,
        description="Cleaned/normalized version of the raw input.",
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="When the request was created.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata for future extensibility.",
    )

    @field_validator("raw_input", "normalized_input")
    @classmethod
    def non_empty(cls, v: str) -> str:
        """Validate that text fields are non-empty after stripping."""
        if not v.strip():
            raise ValueError("Field must be a non-empty string.")
        return v


class ExtractedEntity(JarvisBaseModel):
    """An entity extracted from the user's request by Laya."""

    type: EntityType = Field(
        ...,
        description="The type of entity (e.g., file_path, app_name, url).",
    )
    value: str = Field(
        ...,
        min_length=1,
        description="The extracted entity value.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for this extraction (0.0–1.0).",
    )
    context: str = Field(
        ...,
        min_length=1,
        description="Surrounding context from the request where the entity was found.",
    )


class LayaClassification(JarvisBaseModel):
    """Raw semantic classification produced by Laya.

    Laya classifies the user's request semantically: intent category,
    entity extraction, confidence, and ambiguity detection.
    Task complexity is NOT assessed here — that belongs to TaskProfile.
    """

    request_id: str = Field(
        ...,
        min_length=1,
        description="Links back to the originating Request.",
    )
    category: LayaCategory = Field(
        ...,
        description="Semantic intent category (e.g., informational, actionable, query, command).",
    )
    entities: list[ExtractedEntity] = Field(
        default_factory=list,
        description="Entities extracted from the request.",
    )
    characteristics: list[RequestCharacteristic] = Field(
        default_factory=list,
        description="Identified request characteristics (e.g., multi-step, external-data).",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Classification confidence score (0.0–1.0).",
    )
    ambiguous: bool = Field(
        ...,
        description="Whether the request is ambiguous.",
    )
    ambiguity_reason: str | None = Field(
        default=None,
        description="Why the request is ambiguous. Null if not ambiguous.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional classification details.",
    )

    @model_validator(mode="after")
    def check_ambiguity_consistency(self) -> "LayaClassification":
        """If ambiguous is True, ambiguity_reason must be provided."""
        if self.ambiguous and not self.ambiguity_reason:
            raise ValueError(
                "ambiguity_reason is required when ambiguous is True."
            )
        return self


class Intent(JarvisBaseModel):
    """Validated, canonical intent produced by the Intent Manager.

    The Intent Manager takes Laya's raw classification and produces a
    validated, canonical intent representation. The Intent does NOT
    independently classify the request — it normalizes and enriches
    Laya's classification.
    """

    request_id: str = Field(
        ...,
        min_length=1,
        description="Links back to the originating Request.",
    )
    laya_category: LayaCategory = Field(
        ...,
        description="Laya's raw category (preserved from LayaClassification).",
    )
    normalized_form: str = Field(
        ...,
        min_length=1,
        description="Canonical representation of the intent.",
    )
    entities: list[ExtractedEntity] = Field(
        default_factory=list,
        description="Validated and enriched entities (from LayaClassification).",
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Identified constraints (refined from LayaClassification.characteristics).",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Intent Manager's confidence in the normalized form (0.0–1.0).",
    )
    ambiguous: bool = Field(
        ...,
        description="Whether the intent remains ambiguous after normalization.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context from Intent Manager.",
    )
