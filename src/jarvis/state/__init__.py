"""State Manager module (Phase 1).

Per Section 4 & Section 8:
- State Manager owns: Runtime truth (task ID, lifecycle status, plan version, current step,
  retry/replan counts, approval status, cancellation status, timestamps, deadlines, last verified state).
- State Manager does NOT own: Long-term facts or conversation history (that's Memory).
- Receives: Updates from every loop step.
- Returns: Current task state.
- Called by: Orchestrator, all components.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from jarvis.types import ApprovalStatus, FailureClassification, TaskLifecycle


class TaskState(BaseModel):
    """Runtime task state maintained by State Manager."""

    task_id: str
    lifecycle: TaskLifecycle = TaskLifecycle.CREATED
    plan_version: int = 1
    current_step_index: int = 0
    current_step_name: Optional[str] = None
    is_cancelled: bool = False
    deadline: Optional[datetime] = None
    attempt_count: int = 1
    retry_count: int = 0
    replan_count: int = 0
    recovery_attempts: int = 0
    last_error: Optional[str] = None
    failure_classification: Optional[FailureClassification] = None
    approval_status: ApprovalStatus = ApprovalStatus.NOT_REQUIRED
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_verified_state: Optional[Dict[str, Any]] = None
    step_results: Dict[str, Any] = Field(default_factory=dict)
    active_plan: Optional[Dict[str, Any]] = None
    previous_plans: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StateManager:
    """In-memory State Manager maintaining single-task runtime truth."""

    def __init__(self) -> None:
        self._tasks: Dict[str, TaskState] = {}

    def create_task(
        self,
        task_id: str,
        deadline: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskState:
        """Create and register a new task state."""
        if task_id in self._tasks:
            return self._tasks[task_id]
        state = TaskState(
            task_id=task_id,
            deadline=deadline,
            metadata=metadata or {},
        )
        self._tasks[task_id] = state
        return state

    def get_state(self, task_id: str) -> Optional[TaskState]:
        """Retrieve current state for a given task."""
        return self._tasks.get(task_id)

    def is_cancelled(self, task_id: str) -> bool:
        """Check whether task has been requested to cancel."""
        task = self.get_state(task_id)
        return task.is_cancelled if task else False

    def cancel_task(self, task_id: str) -> None:
        """Flag a task as cancelled."""
        task = self.get_state(task_id)
        if task:
            task.is_cancelled = True
            task.lifecycle = TaskLifecycle.CANCELLED
            task.updated_at = datetime.now(timezone.utc)

    def is_deadline_exceeded(self, task_id: str) -> bool:
        """Check whether the task deadline has expired."""
        task = self.get_state(task_id)
        if task and task.deadline:
            return datetime.now(timezone.utc) > task.deadline
        return False

    def update_lifecycle(self, task_id: str, lifecycle: TaskLifecycle) -> None:
        """Update high-level task lifecycle."""
        task = self.get_state(task_id)
        if task:
            task.lifecycle = lifecycle
            task.updated_at = datetime.now(timezone.utc)

    def update_step(self, task_id: str, step_index: int, step_name: str) -> None:
        """Record current active execution step."""
        task = self.get_state(task_id)
        if task:
            task.current_step_index = step_index
            task.current_step_name = step_name
            task.updated_at = datetime.now(timezone.utc)

    def set_plan_version(self, task_id: str, plan_version: int) -> None:
        """Update plan version number."""
        task = self.get_state(task_id)
        if task:
            task.plan_version = plan_version
            task.updated_at = datetime.now(timezone.utc)

    def set_active_plan(self, task_id: str, plan_data: Dict[str, Any]) -> None:
        """Store the active TaskGraph in task state."""
        task = self.get_state(task_id)
        if task:
            task.active_plan = plan_data
            task.updated_at = datetime.now(timezone.utc)

    def record_step_result(self, task_id: str, step_id: str, result: Dict[str, Any]) -> None:
        """Record execution output for a specific planned step."""
        task = self.get_state(task_id)
        if task:
            task.step_results[step_id] = result
            task.updated_at = datetime.now(timezone.utc)

    def set_last_verified_state(self, task_id: str, verified_state: Dict[str, Any]) -> None:
        """Record last verified state produced by Verification Engine."""
        task = self.get_state(task_id)
        if task:
            task.last_verified_state = verified_state
            task.updated_at = datetime.now(timezone.utc)

    def increment_retry(self, task_id: str) -> int:
        """Increment and return retry count."""
        task = self.get_state(task_id)
        if task:
            task.retry_count += 1
            task.updated_at = datetime.now(timezone.utc)
            return task.retry_count
        return 0

    def increment_replan(self, task_id: str) -> int:
        """Increment and return replan count."""
        task = self.get_state(task_id)
        if task:
            task.replan_count += 1
            task.updated_at = datetime.now(timezone.utc)
            return task.replan_count
        return 0

    def increment_recovery_attempts(self, task_id: str) -> int:
        """Increment and return recovery attempts count."""
        task = self.get_state(task_id)
        if task:
            task.recovery_attempts += 1
            task.updated_at = datetime.now(timezone.utc)
            return task.recovery_attempts
        return 0

    def increment_attempt(self, task_id: str) -> int:
        """Increment and return overall attempt count."""
        task = self.get_state(task_id)
        if task:
            task.attempt_count += 1
            task.updated_at = datetime.now(timezone.utc)
            return task.attempt_count
        return 0

    def record_failure(
        self,
        task_id: str,
        error: str,
        classification: Optional[FailureClassification] = None,
    ) -> None:
        """Record error details and failure classification in task state."""
        task = self.get_state(task_id)
        if task:
            task.last_error = error
            if classification is not None:
                task.failure_classification = classification
            task.updated_at = datetime.now(timezone.utc)

    def set_approval_status(self, task_id: str, status: ApprovalStatus) -> None:
        """Update approval lifecycle status in task state."""
        task = self.get_state(task_id)
        if task:
            task.approval_status = status
            task.updated_at = datetime.now(timezone.utc)

    def archive_plan(self, task_id: str, plan_data: Dict[str, Any]) -> None:
        """Archive a previous plan version when replanning."""
        task = self.get_state(task_id)
        if task:
            task.previous_plans.append(plan_data)
            task.updated_at = datetime.now(timezone.utc)

    def clear(self) -> None:
        """Reset all in-memory tasks (primarily for testing)."""
        self._tasks.clear()


_default_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Return the shared singleton StateManager."""
    global _default_state_manager
    if _default_state_manager is None:
        _default_state_manager = StateManager()
    return _default_state_manager
