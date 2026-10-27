"""
Group E contracts: User Interaction layer.

Models:
- UserResponse: The user's answer to an ASK_USER decision (ADR 04).
- WaitCondition: The external condition a WAIT decision monitors (ADR 04).
- Enums: WaitConditionType.

Scope notes:
- These are declarative data contracts only. They carry no waiting logic,
  no user prompting, no timeout enforcement, and no runtime orchestration.
- UserResponse is distinct from AskUserParams (Group C) — AskUserParams
  carries the question shape; UserResponse is the user's reply.
- WaitCondition is the full condition descriptor; WaitParams (Group C)
  carries the decision-level summary (condition + timeout_ms only).
"""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import Field

from jarvis.contracts.models.base import JarvisBaseModel


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class WaitConditionType(StrEnum):
    """The kind of external condition a WAIT decision monitors (ADR 04)."""

    FILE_PRESENCE = "file_presence"
    PROCESS_START = "process_start"
    TIME_DELAY = "time_delay"
    EXTERNAL_EVENT = "external_event"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def utc_now() -> datetime:
    """Current UTC timestamp."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# UserResponse (ADR 04)
# ---------------------------------------------------------------------------


class UserResponse(JarvisBaseModel):
    """The user's reply to an ASK_USER decision.

    Carried in Agent State as an observation after the user responds.
    ``response_id`` links back to the originating ASK_USER decision.
    """

    response_id: str = Field(
        ...,
        min_length=1,
        description="Links to the ASK_USER prompt.",
    )
    task_id: str = Field(
        ...,
        min_length=1,
        description="The task this response belongs to.",
    )
    answer: str = Field(
        ...,
        min_length=1,
        description="The user's answer text.",
    )
    selected_option: str | None = Field(
        default=None,
        description="Selected option, if predefined options were offered.",
    )
    confirmed: bool = Field(
        ...,
        description="Whether the user confirmed or declined.",
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="When the response was received.",
    )


# ---------------------------------------------------------------------------
# WaitCondition (ADR 04)
# ---------------------------------------------------------------------------


class WaitCondition(JarvisBaseModel):
    """Describes the external condition a WAIT decision monitors (ADR 04).

    Carried as part of the WAIT decision's execution context. This is a
    data contract only — the polling and timeout enforcement are owned by
    the Agent Orchestrator at runtime.
    """

    description: str = Field(
        ...,
        min_length=1,
        description="Human-readable description of the condition.",
    )
    condition_type: WaitConditionType = Field(
        ...,
        description='Type of condition: "file_presence", "process_start", "time_delay", or "external_event".',
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="Condition-specific parameters.",
    )
    timeout_ms: int = Field(
        ...,
        gt=0,
        description="Maximum wait duration in milliseconds.",
    )
    poll_interval_ms: int = Field(
        ...,
        gt=0,
        description="How often to check the condition, in milliseconds.",
    )


__all__ = [
    "WaitConditionType",
    "UserResponse",
    "WaitCondition",
]
