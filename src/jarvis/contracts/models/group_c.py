"""
Group C contracts: Agent Runtime layer.

Models:
- AgentState: Runtime state of a single task execution (ADR 04, ADR 05).
- Decision + eight type-specific Decision models (ADR 04 discriminated union, ADR 06).
- Nested contracts required by AgentState: ExecutionStep, Observation,
  VerificationResult, ErrorRecord.
- Enums: DecisionType, TaskStatus.

Scope notes:
- This module defines contracts only. It contains no Decision Engine,
  no Agent Orchestrator, and no runtime execution logic.
- AgentState.retry_count and AgentState.replan_count are the authoritative
  runtime counters. RuntimeConfig owns the limits they are compared against.
"""

from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Any, Literal, Union

from pydantic import Field, TypeAdapter, model_validator

from jarvis.contracts.models.base import JarvisBaseModel
from jarvis.contracts.models.group_a import (
    Intent,
    LayaClassification,
    Request,
)
from jarvis.contracts.models.group_b import (
    TaskGraph,
    TaskProfile,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DecisionType(StrEnum):
    """The eight decision types the Decision Engine may produce."""

    EXECUTE = "EXECUTE"
    OBSERVE = "OBSERVE"
    REPLAN = "REPLAN"
    RETRY = "RETRY"
    ASK_USER = "ASK_USER"
    WAIT = "WAIT"
    COMPLETE = "COMPLETE"
    FAIL = "FAIL"


class TaskStatus(StrEnum):
    """Overall status of the task tracked by AgentState."""

    PENDING = "PENDING"
    OBSERVING = "OBSERVING"
    DECIDING = "DECIDING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    REPLANNING = "REPLANNING"
    AWAITING = "AWAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def utc_now() -> datetime:
    """Current UTC timestamp."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Nested contracts required by AgentState (ADR 04)
# ---------------------------------------------------------------------------


class ErrorRecord(JarvisBaseModel):
    """A single recorded error. Stored in AgentState.errors (append-only)."""

    code: str = Field(
        ...,
        min_length=1,
        description="Error code.",
    )
    message: str = Field(
        ...,
        min_length=1,
        description="Human-readable description of the error.",
    )
    recoverable: bool = Field(
        ...,
        description="Whether retry/recovery is possible.",
    )
    context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional error context.",
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="When the error occurred.",
    )


class Observation(JarvisBaseModel):
    """A result returned after executing an action or gathering information."""

    source: str = Field(
        ...,
        min_length=1,
        description="What produced this observation (tool, user, system).",
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="The observed data.",
    )
    success: bool = Field(
        ...,
        description="Whether the action succeeded.",
    )
    error: ErrorRecord | None = Field(
        default=None,
        description="Error details if the observation was not successful.",
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="When the observation was recorded.",
    )

    @model_validator(mode="after")
    def check_error_present_when_failed(self) -> "Observation":
        """A failed observation must carry an ErrorRecord."""
        if not self.success and self.error is None:
            raise ValueError(
                "error is required when success is False."
            )
        return self


class VerificationResult(JarvisBaseModel):
    """Outcome of verifying an observation against an expected result."""

    passed: bool = Field(
        ...,
        description="Whether verification succeeded.",
    )
    expected: dict[str, Any] = Field(
        default_factory=dict,
        description="What was expected.",
    )
    actual: dict[str, Any] = Field(
        default_factory=dict,
        description="What was observed.",
    )
    discrepancy: str | None = Field(
        default=None,
        description="Human-readable description of the discrepancy if failed.",
    )
    severity: Literal["none", "warning", "error"] = Field(
        default="none",
        description="Severity of the verification outcome.",
    )


class ExecutionStep(JarvisBaseModel):
    """A single recorded step of the execution history (append-only).

    Note: `decision` is typed as the Decision union to satisfy the ADR 04
    contract. It is declared after the Decision models are defined below.
    """

    step_number: int = Field(
        ...,
        ge=1,
        description="Sequential step number (1-indexed).",
    )
    node_id: str = Field(
        ...,
        min_length=1,
        description="Task Graph node that was executed.",
    )
    decision: "AnyDecisionUnion" = Field(
        ...,
        description="The Decision that triggered this step.",
    )
    action: str = Field(
        ...,
        min_length=1,
        description="What was done.",
    )
    observation: Observation = Field(
        ...,
        description="Result of the action.",
    )
    verification: VerificationResult = Field(
        ...,
        description="Outcome of verification.",
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="When this step occurred.",
    )
    duration_ms: int = Field(
        ...,
        ge=0,
        description="How long the step took, in milliseconds.",
    )


# ---------------------------------------------------------------------------
# Decision parameter models (ADR 04 discriminated union)
# ---------------------------------------------------------------------------


class ExecuteParams(JarvisBaseModel):
    """Parameters for an EXECUTE decision."""

    target_node_id: str = Field(
        ...,
        min_length=1,
        description="The Task Graph node to execute.",
    )
    tool_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters to pass to the tool.",
    )


class ObserveParams(JarvisBaseModel):
    """Parameters for an OBSERVE decision."""

    observation_target: str | None = Field(
        default=None,
        description="What to observe.",
    )
    observation_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the observation.",
    )


class ReplanParams(JarvisBaseModel):
    """Parameters for a REPLAN decision."""

    replan_reason: str = Field(
        ...,
        min_length=1,
        description="Why replanning is needed.",
    )
    preserve_completed: bool = Field(
        default=True,
        description="Whether to keep completed nodes.",
    )


class RetryParams(JarvisBaseModel):
    """Parameters for a RETRY decision."""

    target_node_id: str = Field(
        ...,
        min_length=1,
        description="The node to retry.",
    )
    adjusted_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Modified parameters for the retry.",
    )
    retry_count: int = Field(
        ...,
        ge=1,
        description=(
            "Current retry attempt number (1-indexed) — the Decision Engine's "
            "reasoning about the attempt. AgentState.retry_count is authoritative "
            "for enforcement."
        ),
    )


class AskUserParams(JarvisBaseModel):
    """Parameters for an ASK_USER decision."""

    question: str = Field(
        ...,
        min_length=1,
        description="The question or prompt for the user.",
    )
    options: list[str] = Field(
        default_factory=list,
        description="Predefined response options.",
    )
    required: bool = Field(
        default=True,
        description="Whether a response is mandatory.",
    )


class WaitParams(JarvisBaseModel):
    """Parameters for a WAIT decision."""

    condition: str = Field(
        ...,
        min_length=1,
        description="Description of the condition to wait for.",
    )
    timeout_ms: int = Field(
        ...,
        gt=0,
        description="Maximum wait duration in milliseconds.",
    )


class CompleteParams(JarvisBaseModel):
    """Parameters for a COMPLETE decision."""

    summary: str | None = Field(
        default=None,
        description="Description of the completed task.",
    )
    result: dict[str, Any] = Field(
        default_factory=dict,
        description="Final result data.",
    )


class FailParams(JarvisBaseModel):
    """Parameters for a FAIL decision."""

    reason: str = Field(
        ...,
        min_length=1,
        description="Why the task failed.",
    )
    error: ErrorRecord | None = Field(
        default=None,
        description="ErrorRecord describing the failure.",
    )


# ---------------------------------------------------------------------------
# Decision models (ADR 04 discriminated union, discriminated on `type`)
# ---------------------------------------------------------------------------


class _DecisionBase(JarvisBaseModel):
    """Fields shared by all eight Decision variants."""

    id: str = Field(
        ...,
        min_length=1,
        description="Unique decision identifier.",
    )
    reasoning: str = Field(
        ...,
        min_length=1,
        description="LLM's reasoning for this decision.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Decision confidence (0.0–1.0).",
    )
    target_node_id: str | None = Field(
        default=None,
        description=(
            "Denormalized convenience copy per ADR 04; the corresponding decision "
            "parameter model's `target_node_id` is authoritative and must not be "
            "overridden by this field. No schema-level cross-field consistency rule "
            "is enforced."
        ),
    )
    retry_count: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Decision Engine's reasoning about the current retry attempt "
            "(1-indexed). AgentState.retry_count is authoritative — the "
            "Orchestrator must not trust this field over AgentState.retry_count."
        ),
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="When this decision was produced.",
    )


class ExecuteDecision(_DecisionBase):
    """Decision: execute the next planned action in the Task Graph."""

    type: Literal[DecisionType.EXECUTE] = DecisionType.EXECUTE
    parameters: ExecuteParams


class ObserveDecision(_DecisionBase):
    """Decision: gather additional information without executing a tool action."""

    type: Literal[DecisionType.OBSERVE] = DecisionType.OBSERVE
    parameters: ObserveParams


class ReplanDecision(_DecisionBase):
    """Decision: revise the Task Graph in response to changed circumstances."""

    type: Literal[DecisionType.REPLAN] = DecisionType.REPLAN
    parameters: ReplanParams


class RetryDecision(_DecisionBase):
    """Decision: repeat the last failed action."""

    type: Literal[DecisionType.RETRY] = DecisionType.RETRY
    parameters: RetryParams


class AskUserDecision(_DecisionBase):
    """Decision: request additional input or confirmation from the user."""

    type: Literal[DecisionType.ASK_USER] = DecisionType.ASK_USER
    parameters: AskUserParams


class WaitDecision(_DecisionBase):
    """Decision: pause execution for an external condition."""

    type: Literal[DecisionType.WAIT] = DecisionType.WAIT
    parameters: WaitParams


class CompleteDecision(_DecisionBase):
    """Decision: signal successful task completion."""

    type: Literal[DecisionType.COMPLETE] = DecisionType.COMPLETE
    parameters: CompleteParams


class FailDecision(_DecisionBase):
    """Decision: signal that the task cannot be completed."""

    type: Literal[DecisionType.FAIL] = DecisionType.FAIL
    parameters: FailParams


# The discriminated union. Selection is driven by the `type` field.
AnyDecisionUnion = Union[
    ExecuteDecision,
    ObserveDecision,
    ReplanDecision,
    RetryDecision,
    AskUserDecision,
    WaitDecision,
    CompleteDecision,
    FailDecision,
]


# Alias carrying the discriminator, for use as a field/parameter annotation.
AnyDecision = Annotated[AnyDecisionUnion, Field(discriminator="type")]


# ---------------------------------------------------------------------------
# RuntimeConfig (ADR 04)
# ---------------------------------------------------------------------------


class RuntimeConfig(JarvisBaseModel):
    """Runtime limits enforced by the Agent Orchestrator.

    These are not task-specific — they apply to every task execution.
    The Orchestrator owns enforcement of these limits; no other component
    enforces them.
    """

    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of RETRY decisions for a single node.",
    )
    max_replans: int = Field(
        default=3,
        ge=0,
        description="Maximum number of REPLAN decisions for a single task.",
    )
    global_timeout_ms: int | None = Field(
        default=None,
        gt=0,
        description=(
            "Maximum task execution duration in milliseconds. Per-task limit, "
            "distinct from the per-decision timeout_ms used by WAIT decisions. "
            "Enforcement is deferred to a future implementation phase."
        ),
    )


# ---------------------------------------------------------------------------
# AgentState (ADR 04, ADR 05)
# ---------------------------------------------------------------------------


class AgentState(JarvisBaseModel):
    """Runtime state of a single task execution.

    AgentState is transient — it exists only for the duration of a single task
    execution and is never persisted. It is distinct from persistent memory.

    This contract carries no runtime behavior: it does not execute tools,
    make decisions, or enforce limits. The Agent Orchestrator owns all
    mutation and all limit enforcement.
    """

    request: Request = Field(
        ...,
        description="The original request.",
    )
    intent: Intent = Field(
        ...,
        description="The classified intent.",
    )
    laya_classification: LayaClassification = Field(
        ...,
        description="Laya's classification.",
    )
    task_profile: TaskProfile = Field(
        ...,
        description="Profiled task characteristics.",
    )
    task_graph: TaskGraph = Field(
        ...,
        description="Current (possibly revised) task graph.",
    )
    execution_history: list[ExecutionStep] = Field(
        default_factory=list,
        description="Record of all steps taken. Append-only (ADR 05).",
    )
    current_step_id: str | None = Field(
        default=None,
        description="ID of the currently active node.",
    )
    status: TaskStatus = Field(
        default=TaskStatus.PENDING,
        description="Overall task status.",
    )
    observations: list[Observation] = Field(
        default_factory=list,
        description="Collected observations.",
    )
    errors: list[ErrorRecord] = Field(
        default_factory=list,
        description="Error history. Append-only (ADR 05, ADR 11).",
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        description=(
            "Authoritative runtime retry counter for the current node. "
            "Incremented by the Agent Orchestrator only."
        ),
    )
    replan_count: int = Field(
        default=0,
        ge=0,
        description="Number of REPLAN decisions issued for this task.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional runtime data.",
    )


# Resolve the forward reference declared on ExecutionStep.decision.
ExecutionStep.model_rebuild()
# TypeAdapter for validating/serializing any Decision variant.
DECISION_ADAPTER: TypeAdapter[Any] = TypeAdapter(AnyDecision)

__all__ = [
    # Enums
    "DecisionType",
    "TaskStatus",
    # Nested contracts
    "ErrorRecord",
    "Observation",
    "VerificationResult",
    "ExecutionStep",
    # Decision parameters
    "ExecuteParams",
    "ObserveParams",
    "ReplanParams",
    "RetryParams",
    "AskUserParams",
    "WaitParams",
    "CompleteParams",
    "FailParams",
    # Decision variants
    "ExecuteDecision",
    "ObserveDecision",
    "ReplanDecision",
    "RetryDecision",
    "AskUserDecision",
    "WaitDecision",
    "CompleteDecision",
    "FailDecision",
    # Union + adapter
    "AnyDecision",
    "DECISION_ADAPTER",
    # Runtime
    "RuntimeConfig",
    "AgentState",
]
