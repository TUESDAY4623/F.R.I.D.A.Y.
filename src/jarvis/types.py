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
