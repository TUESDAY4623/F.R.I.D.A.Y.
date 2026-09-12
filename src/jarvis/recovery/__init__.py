"""Error / Recovery Manager module (Phase 0 stub).

Per Section 4 & Section 14:
- Error/Recovery Manager owns: Classifying failures, selecting
  retry/re-observe/replan/alternate-tool/stop strategy, retry & replan budgets, backoff.
- Error/Recovery Manager does NOT own: Verification (consumes its output).
- Receives: Failure + context.
- Returns: Recovery action.
- Called by: Orchestrator.
(To be fully implemented by Sujeet in Phase 2).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel


class RecoveryStrategy(str, Enum):
    RETRY = "retry"
    REOBSERVE = "reobserve"
    REPLAN = "replan"
    ALTERNATE_TOOL = "alternate_tool"
    STOP = "stop"


class RecoveryAction(BaseModel):
    strategy: RecoveryStrategy
    reason: str
    context: Dict[str, Any] = {}


class RecoveryManager:
    """Error / Recovery Manager stub."""

    def __init__(self, max_retries: int = 3, max_replans: int = 2) -> None:
        self.max_retries = max_retries
        self.max_replans = max_replans

    def handle_failure(
        self,
        failure_type: str,
        task_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> RecoveryAction:
        """Evaluate failure and determine recovery strategy."""
        return RecoveryAction(
            strategy=RecoveryStrategy.STOP,
            reason=f"Phase 0 stub stopping on failure: {failure_type}",
            context=context or {},
        )


_default_recovery_manager: Optional[RecoveryManager] = None


def get_recovery_manager() -> RecoveryManager:
    global _default_recovery_manager
    if _default_recovery_manager is None:
        _default_recovery_manager = RecoveryManager()
    return _default_recovery_manager
