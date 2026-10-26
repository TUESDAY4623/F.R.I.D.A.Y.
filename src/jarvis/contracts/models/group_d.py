"""
Group D contracts: Execution boundary layer.

Models:
- ValidationError: A single parameter-validation failure (ADR 04).
- ValidationResult: Outcome of validating tool parameters or inputs (ADR 04).
- ProposedAction: The action proposed for execution, as submitted to the
  Policy Engine (ADR 09). Referred to as "ActionRequest" in some Phase 1
  planning documents; the canonical documented name is ProposedAction.
- PolicyResult: The Policy Engine's verdict on a proposed action (ADR 04, ADR 09).

Observation is reused from group_c — no duplicate is defined here.
ErrorRecord is reused from group_c for the error paths in these contracts.

Scope notes:
- This module defines contracts only. It contains no Policy Engine logic,
  no Tool Manager logic, and no action execution.
- PolicyResult.approval_token is a plain string token; ApprovalToken (the
  richer token model) is a separate contract owned by a later group.
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import Field, model_validator

from jarvis.contracts.models.base import JarvisBaseModel
from jarvis.contracts.models.group_c import AgentState, ErrorRecord


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def utc_now() -> datetime:
    """Current UTC timestamp."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# ValidationError (ADR 04)
# ---------------------------------------------------------------------------


class ValidationError_(JarvisBaseModel):
    """A single parameter-validation failure.

    Named ``ValidationError_`` because ``ValidationError`` is already taken
    by Pydantic. The canonical contract name documented in ADR 04 is
    ``ValidationError``; the trailing underscore is the Python-side
    identifier only — the JSON schema and external contract name remain
    ``ValidationError``.
    """

    field: str = Field(
        ...,
        min_length=1,
        description="The field that failed validation.",
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Human-readable description of the failure.",
    )
    code: str = Field(
        ...,
        min_length=1,
        description="Machine-readable error code.",
    )


# Register the canonical external name on the model so schema titles
# and JSON output use "ValidationError" rather than "ValidationError_".
# Model config is frozen after class creation, so this must be done here.
ValidationError_.model_config["title"] = "ValidationError"


# ---------------------------------------------------------------------------
# ValidationResult (ADR 04)
# ---------------------------------------------------------------------------


class ValidationResult(JarvisBaseModel):
    """Outcome of validating tool parameters or inputs.

    Returned by the Tool Manager's ``validate_params()`` method and by
    individual tool ``validate_params()`` implementations.
    """

    valid: bool = Field(
        ...,
        description="Whether the input passed validation.",
    )
    errors: list[ValidationError_] = Field(
        default_factory=list,
        description="Validation errors. Must be empty when valid is True.",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Non-blocking warnings.",
    )

    @model_validator(mode="after")
    def check_errors_consistent_with_valid(self) -> "ValidationResult":
        """ADR 04: errors is empty if valid. Enforce the reverse direction too:
        non-empty errors implies valid must be False.
        """
        if self.valid and self.errors:
            raise ValueError(
                "errors must be empty when valid is True."
            )
        if not self.valid and not self.errors:
            raise ValueError(
                "errors must be non-empty when valid is False."
            )
        return self


# ---------------------------------------------------------------------------
# ProposedAction (ADR 09) — also referred to as "ActionRequest" in Phase 1
# planning documents.
# ---------------------------------------------------------------------------


class ProposedAction(JarvisBaseModel):
    """The action proposed for execution.

    Submitted to the Policy Engine's ``validate()`` method before the
    corresponding tool is invoked. Carries the agent state at the time of
    the proposal so the Policy Engine can evaluate context-dependent rules.

    Named ``ProposedAction`` per ADR 09. Some Phase 1 planning documents
    use the name "ActionRequest" for this same contract.
    """

    action_type: str = Field(
        ...,
        min_length=1,
        description='Type of action (e.g., "tool_call", "file_read", "browser_navigate").',
    )
    tool_name: str = Field(
        ...,
        min_length=1,
        description="Which tool would be invoked.",
    )
    parameters: dict[str, Any] = Field(
        default_factory=dict,
        description="The proposed parameters.",
    )
    agent_state: AgentState = Field(
        ...,
        description="Current state at time of proposal (read-only reference).",
    )
    task_graph_node_id: str = Field(
        ...,
        min_length=1,
        description="Which Task Graph node this serves.",
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="When the action was proposed (ADR 09).",
    )


# ---------------------------------------------------------------------------
# PolicyResult (ADR 04, ADR 09)
# ---------------------------------------------------------------------------


class PolicyResult(JarvisBaseModel):
    """The Policy Engine's verdict on a proposed action.

    Returned by ``IPolicyEngine.validate()``. ``approval_token`` carries the
    token string for approved actions. The richer ``ApprovalToken`` model
    (with expiry and conditions) is a separate contract; PolicyResult carries
    the flat string form documented in ADR 04.
    """

    approved: bool = Field(
        ...,
        description="Whether the action is approved.",
    )
    reason: str = Field(
        ...,
        min_length=1,
        description="Explanation, especially for denials.",
    )
    conditions: list[str] = Field(
        default_factory=list,
        description='Conditions attached to the approval (e.g., "read-only").',
    )
    rule_triggers: list[str] = Field(
        default_factory=list,
        description="Which policy rules were evaluated.",
    )
    approval_token: str | None = Field(
        default=None,
        min_length=1,
        description="Token for approved actions (present when approved).",
    )

    @model_validator(mode="after")
    def check_approval_token_consistent(self) -> "PolicyResult":
        """ADR 04: approval_token is present when approved.

        Enforce the bidirectional invariant:
        - approved=True  → approval_token must be non-None
        - approved=False → approval_token must be None
        """
        if self.approved and self.approval_token is None:
            raise ValueError(
                "approval_token is required when approved is True."
            )
        if not self.approved and self.approval_token is not None:
            raise ValueError(
                "approval_token must be None when approved is False."
            )
        return self


# ---------------------------------------------------------------------------
# ToolResult (ADR 07)
# ---------------------------------------------------------------------------


class ToolResult(JarvisBaseModel):
    """The result of executing a tool through the Tool Manager (ADR 07).

    Every tool execution returns a ToolResult. On failure the ``error``
    field carries an ErrorRecord; the Tool Manager then hands the result to
    the Orchestrator, which records it and routes it to Error Recovery
    (ADR 11) when unsuccessful.

    Failure/error consistency follows the Observation convention (ADR 04):
    a result that did not succeed must carry an ErrorRecord. This is a
    one-directional invariant — ``success=False`` requires ``error`` to be
    present. A successful result is not required to have ``error`` absent,
    matching Observation, which enforces only the failure direction.

    ``data`` and ``metadata`` have no required-content rule: both default
    to an empty object so that a result may omit them (e.g. a failure with
    no payload). No condition-specific keys are invented for them.
    """

    success: bool = Field(
        ...,
        description="Whether the execution succeeded.",
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Result data (if successful).",
    )
    error: ErrorRecord | None = Field(
        default=None,
        description="Error details (if failed) — see ADR 04 ErrorRecord.",
    )
    duration_ms: int = Field(
        ...,
        ge=0,
        description="Execution duration in milliseconds.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional result metadata.",
    )

    @model_validator(mode="after")
    def check_error_present_when_failed(self) -> "ToolResult":
        """ADR 07 / Observation convention: a failed result must carry an
        ErrorRecord. One-directional — a successful result may omit it.
        """
        if not self.success and self.error is None:
            raise ValueError(
                "error is required when success is False."
            )
        return self


__all__ = [
    "ValidationError_",
    "ValidationResult",
    "ProposedAction",
    "PolicyResult",
    "ToolResult",
]
