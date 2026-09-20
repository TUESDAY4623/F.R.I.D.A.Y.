"""Event schema and event types for Event Logger.

Per Section 13 (Logging Architecture):
Records task lifecycle, intent, task profile, plan, model routing decision,
model execution, tool requests/results, observations, verification, policy decisions,
approvals, retries, recovery, replanning, errors, completion — each tagged with a correlation/task ID.
Never logs passwords, API keys, tokens, or raw credentials.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventType(str, Enum):
    # Orchestrator canonical loop
    ORCHESTRATOR_STEP = "orchestrator.step"
    ORCHESTRATOR_LOOP_START = "orchestrator.loop_start"
    ORCHESTRATOR_LOOP_END = "orchestrator.loop_end"

    # Task lifecycle
    TASK_CREATED = "task.created"
    TASK_STATUS_CHANGED = "task.status_changed"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    TASK_PAUSED = "task.paused"
    TASK_TIMEOUT = "task.timeout"

    # Intent and Planning
    INTENT_DETECTED = "intent.detected"
    TASK_PROFILED = "task.profiled"
    PLAN_GENERATED = "plan.generated"
    PLAN_REVISED = "plan.revised"

    # Model & Routing
    MODEL_ROUTED = "model.routed"
    MODEL_INVOKED = "model.invoked"
    MODEL_RESPONSE = "model.response"

    # Policy & Approval
    POLICY_DECISION = "policy.decision"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_DECISION = "approval.decision"
    TASK_APPROVAL_PENDING = "task.approval_pending"
    TASK_APPROVAL_APPROVED = "task.approval_approved"
    TASK_APPROVAL_DENIED = "task.approval_denied"

    # Tool Execution
    TOOL_REQUESTED = "tool.requested"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"

    # Observation & Verification
    OBSERVATION_CAPTURED = "observation.captured"
    VERIFICATION_RESULT = "verification.result"

    # Recovery & Errors
    RETRY_TRIGGERED = "recovery.retry"
    RECOVERY_ATTEMPTED = "recovery.attempted"
    TASK_RETRY = "task.retry"
    TASK_RECOVERY_STARTED = "task.recovery_started"
    TASK_RECOVERY_COMPLETED = "task.recovery_completed"
    TASK_REPLAN = "task.replan"
    ERROR_OCCURRED = "error.occurred"

    # Credential Vault
    CREDENTIAL_ACCESSED = "vault.credential_accessed"


class EventSensitivity(str, Enum):
    """Sensitivity classification for log events."""

    NORMAL = "normal"
    UNTRUSTED_CONTENT = "untrusted_content"
    SECURITY_RELEVANT = "security_relevant"


class LogEvent(BaseModel):
    """Structured, sanitized event recorded by Event Logger."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    task_id: Optional[str] = None
    step_name: Optional[str] = None
    event_type: EventType
    level: LogLevel = LogLevel.INFO
    source: str
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    sensitivity: EventSensitivity = EventSensitivity.NORMAL
    redacted: bool = False

    def to_log_line(self) -> str:
        """Formatted human-readable log line."""
        task_str = f"[{self.task_id}] " if self.task_id else ""
        step_str = f"({self.step_name}) " if self.step_name else ""
        return (
            f"{self.timestamp.isoformat()} | {self.level.value:<5} | "
            f"{self.source} | {task_str}{step_str}{self.event_type.value}: {self.message}"
        )
