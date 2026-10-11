"""Error / Recovery Manager module (Phase 2).

Per Section 4 & Section 14:
- Error/Recovery Manager owns: Classifying failures, selecting
  retry/re-observe/replan/alternate-tool/stop strategy, retry & replan budgets, backoff.
- Error/Recovery Manager does NOT own: Verification (consumes its output),
  and does NOT directly invoke tools or mutate state.
- Receives: Failure + context.
- Returns: RecoveryAction (containing strategy, classification, and optional recovery steps).
- Called by: Orchestrator / Canonical Loop Step 11.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from jarvis.planner import PlanStep
from jarvis.types import FailureClassification, RecoveryStrategy


class RecoveryAction(BaseModel):
    """Recovery strategy decision produced by Recovery Manager."""

    strategy: RecoveryStrategy
    classification: FailureClassification
    reason: str
    context: Dict[str, Any] = Field(default_factory=dict)
    recovery_steps: List[PlanStep] = Field(default_factory=list)


class RecoveryManager:
    """Error / Recovery Manager implementing Phase 2 recovery logic."""

    def __init__(
        self,
        max_retries: int = 3,
        max_replans: int = 2,
        max_recovery_attempts: int = 2,
    ) -> None:
        self.max_retries = max_retries
        self.max_replans = max_replans
        self.max_recovery_attempts = max_recovery_attempts

    def classify_failure(
        self,
        error: str,
        action_name: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> FailureClassification:
        """Classify a failure into one of the 5 canonical failure categories."""
        err_lower = (error or "").lower()
        args = arguments or {}

        # 1. Check for USER_ACTION_REQUIRED
        if (
            "approval" in err_lower
            or "denied" in err_lower
            or "permission denied" in err_lower
            or "user action" in err_lower
        ):
            return FailureClassification.USER_ACTION_REQUIRED

        # 2. Check for missing tool or contract validation errors -> FATAL
        if (
            "not found in registry" in err_lower
            or "missing required argument" in err_lower
            or "must be a" in err_lower
        ):
            return FailureClassification.FATAL

        # 3. Check for non-existent source file on read/list -> FATAL
        if action_name in ("read_file", "list_directory"):
            if "not found" in err_lower or "does not exist" in err_lower or "no such file" in err_lower:
                return FailureClassification.FATAL

        # 4. Check for move_file where source does not exist -> FATAL
        if action_name == "move_file":
            src = args.get("source") or args.get("source_path", "")
            if src and not os.path.exists(src):
                return FailureClassification.FATAL

        # 5. Check for RECOVERABLE missing parent directory (move_file, write_file)
        if action_name == "move_file":
            dest = args.get("destination") or args.get("destination_path", "")
            if dest:
                parent = os.path.dirname(dest)
                if parent and not os.path.exists(parent):
                    return FailureClassification.RECOVERABLE

        if action_name == "write_file":
            path = args.get("path", "")
            if path:
                parent = os.path.dirname(path)
                if parent and not os.path.exists(parent):
                    return FailureClassification.RECOVERABLE

        if "parent directory does not exist" in err_lower or "destination directory does not exist" in err_lower:
            return FailureClassification.RECOVERABLE

        # 6. Check for RETRYABLE transient failures
        retryable_keywords = (
            "timeout",
            "timed out",
            "temporary",
            "temporarily unavailable",
            "locked",
            "busy",
            "connection reset",
            "eagain",
            "try again",
        )
        if any(kw in err_lower for kw in retryable_keywords):
            return FailureClassification.RETRYABLE

        # 7. Check for verification failure or discrepancy -> REPLAN_REQUIRED
        if "verification failed" in err_lower or "discrepancy" in err_lower:
            return FailureClassification.REPLAN_REQUIRED

        # Default fallback: if action could not be verified, replan; otherwise fatal
        if context and context.get("verification_failure"):
            return FailureClassification.REPLAN_REQUIRED

        return FailureClassification.FATAL

    def create_recovery_plan(
        self,
        action_name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[PlanStep]:
        """Generate compensatory / recovery steps to fix a failed precondition."""
        recovery_steps: List[PlanStep] = []

        if action_name == "move_file":
            dest = arguments.get("destination") or arguments.get("destination_path", "")
            if dest:
                parent = os.path.dirname(dest)
                if parent and not os.path.exists(parent):
                    recovery_steps.append(
                        PlanStep(
                            step_id=f"recovery-mkdir-{uuid4().hex[:4]}",
                            tool_name="create_directory",
                            arguments={"path": parent},
                            expected_outcome={
                                "status": "completed",
                                "action": "create_directory",
                                "path": parent,
                            },
                            description=f"Auto-recovery: create missing destination folder '{parent}'",
                            status="pending",
                        )
                    )

        elif action_name == "write_file":
            path = arguments.get("path", "")
            if path:
                parent = os.path.dirname(path)
                if parent and not os.path.exists(parent):
                    recovery_steps.append(
                        PlanStep(
                            step_id=f"recovery-mkdir-{uuid4().hex[:4]}",
                            tool_name="create_directory",
                            arguments={"path": parent},
                            expected_outcome={
                                "status": "completed",
                                "action": "create_directory",
                                "path": parent,
                            },
                            description=f"Auto-recovery: create missing parent folder '{parent}'",
                            status="pending",
                        )
                    )

        return recovery_steps

    def handle_failure(
        self,
        failure_type: str,
        task_id: str,
        action_name: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> RecoveryAction:
        """Evaluate failure, classify it, and determine recovery strategy respecting budgets."""
        ctx = context or {}
        classification = self.classify_failure(
            error=failure_type,
            action_name=action_name,
            arguments=arguments,
            context=ctx,
        )

        retries = ctx.get("retry_count", 0)
        replans = ctx.get("replan_count", 0)
        recovery_attempts = ctx.get("recovery_attempts", 0)

        # RETRYABLE logic
        if classification == FailureClassification.RETRYABLE:
            if retries < self.max_retries:
                return RecoveryAction(
                    strategy=RecoveryStrategy.RETRY,
                    classification=classification,
                    reason=f"Transient failure detected ({failure_type}). Retrying ({retries + 1}/{self.max_retries}).",
                    context=ctx,
                )
            return RecoveryAction(
                strategy=RecoveryStrategy.STOP,
                classification=FailureClassification.FATAL,
                reason=f"Retry budget exhausted ({retries}/{self.max_retries}).",
                context=ctx,
            )

        # RECOVERABLE logic
        if classification == FailureClassification.RECOVERABLE:
            if recovery_attempts < self.max_recovery_attempts:
                rec_steps = self.create_recovery_plan(
                    action_name=action_name or "",
                    arguments=arguments or {},
                    context=ctx,
                )
                if rec_steps:
                    return RecoveryAction(
                        strategy=RecoveryStrategy.RECOVER,
                        classification=classification,
                        reason=f"Precondition failed ({failure_type}). Injecting recovery steps.",
                        context=ctx,
                        recovery_steps=rec_steps,
                    )
                # Fallback to replan if no specific recovery steps
                if replans < self.max_replans:
                    return RecoveryAction(
                        strategy=RecoveryStrategy.REPLAN,
                        classification=FailureClassification.REPLAN_REQUIRED,
                        reason=f"Recoverable failure has no direct action. Requesting replan.",
                        context=ctx,
                    )

            return RecoveryAction(
                strategy=RecoveryStrategy.STOP,
                classification=FailureClassification.FATAL,
                reason=f"Recovery attempts budget exhausted ({recovery_attempts}/{self.max_recovery_attempts}).",
                context=ctx,
            )

        # REPLAN_REQUIRED logic
        if classification == FailureClassification.REPLAN_REQUIRED:
            if replans < self.max_replans:
                return RecoveryAction(
                    strategy=RecoveryStrategy.REPLAN,
                    classification=classification,
                    reason=f"Discrepancy or approach failure ({failure_type}). Replanning ({replans + 1}/{self.max_replans}).",
                    context=ctx,
                )
            return RecoveryAction(
                strategy=RecoveryStrategy.STOP,
                classification=FailureClassification.FATAL,
                reason=f"Replan budget exhausted ({replans}/{self.max_replans}).",
                context=ctx,
            )

        # USER_ACTION_REQUIRED or FATAL
        return RecoveryAction(
            strategy=RecoveryStrategy.STOP,
            classification=classification,
            reason=f"Unrecoverable or user intervention required: {failure_type}",
            context=ctx,
        )


_default_recovery_manager: Optional[RecoveryManager] = None


def get_recovery_manager() -> RecoveryManager:
    global _default_recovery_manager
    if _default_recovery_manager is None:
        _default_recovery_manager = RecoveryManager()
    return _default_recovery_manager
