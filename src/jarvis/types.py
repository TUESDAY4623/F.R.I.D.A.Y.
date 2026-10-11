"""Shared core types and enums for the Jarvis Desktop Agent.

Per Section 1 (Design Principles), Section 7 (Policy / Approval Flow),
Section 8 (State / Conversation / Memory), and Section 11 (Tool Registry Contract).
"""

from enum import Enum


class RiskLevel(str, Enum):
    """Tool risk tier declared in Tool Registry and consumed by Policy Engine.

    Per Section 7:
    - LOW: Read files, screenshot, web search, open app. Auto-executed.
    - MEDIUM: Move/rename/download. Auto-executed only if tool declares reversible: true
      with a rollback strategy.
    - HIGH: Anything declared reversible: false (permanent delete, send message, install software, etc.).
      Always requires human-in-the-loop approval.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskLifecycle(str, Enum):
    """Lifecycle states of a task owned by State Manager.

    Per Section 8:
    CREATED -> UNDERSTANDING -> PLANNING -> WAITING_FOR_APPROVAL -> EXECUTING
       -> VERIFYING -> (REPLANNING -> EXECUTING)* -> COMPLETED
                                                -> FAILED
       -> PAUSED -> CANCELLED
    """

    CREATED = "created"
    UNDERSTANDING = "understanding"
    PLANNING = "planning"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class PolicyDecision(str, Enum):
    """Decision produced by Policy Engine.

    Per Section 2 & 4:
    ALLOW: Execute action.
    CONFIRM: Route to Approval Manager for user approval.
    DENY: Reject execution.
    """

    ALLOW = "allow"
    CONFIRM = "confirm"
    DENY = "deny"


class ApprovalDecision(str, Enum):
    """Decision returned by Approval Manager.

    Per Section 4 & 7:
    APPROVE: User confirmed execution.
    DENY: User rejected execution.
    CANCEL: User cancelled the entire task.
    """

    APPROVE = "approve"
    DENY = "deny"
    CANCEL = "cancel"


class VerificationStatus(str, Enum):
    """Outcome of Verification Engine comparing observation with expected outcome.

    Per Section 4 & 6:
    PASS: Observed state satisfies expected outcome.
    FAIL: Observed state does not satisfy expected outcome.
    """

    PASS = "pass"
    FAIL = "fail"


class ApprovalStatus(str, Enum):
    """Approval lifecycle states.

    Per Section 7 & Phase 2:
    NOT_REQUIRED: Tool/action is low risk or auto-executable.
    PENDING: Awaiting user confirmation.
    APPROVED: User confirmed execution.
    DENIED: User rejected execution.
    CANCELLED: User cancelled the entire task.
    EXPIRED: Request timed out without user decision.
    """

    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class FailureClassification(str, Enum):
    """Failure classification for recovery and retry decisions.

    Per Section 14 & Phase 2:
    RETRYABLE: Transient failure (network/timeout, locked file). Retry with backoff.
    RECOVERABLE: Precondition failed that can be fixed automatically (missing parent dir).
    REPLAN_REQUIRED: Goal cannot be achieved with current approach, alternate path needed.
    USER_ACTION_REQUIRED: Requires user input, credentials, or manual intervention.
    FATAL: Unrecoverable error (non-existent source file, invalid syntax, budget exhausted).
    """

    RETRYABLE = "retryable"
    RECOVERABLE = "recoverable"
    REPLAN_REQUIRED = "replan_required"
    USER_ACTION_REQUIRED = "user_action_required"
    FATAL = "fatal"


class RecoveryStrategy(str, Enum):
    """Recovery strategy chosen by Recovery Manager.

    Per Section 14 & Phase 2:
    RETRY: Re-execute same action after backoff.
    RECOVER: Inject recovery action to satisfy failed precondition.
    REOBSERVE: Capture fresh observation before deciding.
    REPLAN: Request new task graph from Planner.
    ALTERNATE_TOOL: Substitute alternative tool.
    USER_INTERVENTION: Escalate to user.
    STOP: Terminate task as failed.
    """

    RETRY = "retry"
    RECOVER = "recover"
    REOBSERVE = "reobserve"
    REPLAN = "replan"
    ALTERNATE_TOOL = "alternate_tool"
    USER_INTERVENTION = "user_intervention"
    STOP = "stop"
