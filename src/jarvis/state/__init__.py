"""State Manager module (Phase 0 stub).

Per Section 4 & Section 8:
- State Manager owns: Runtime truth (task ID, lifecycle status, plan version, current step,
  retry/replan counts, approval status, cancellation status, timestamps, deadlines).
- State Manager does NOT own: Long-term facts (that's Memory).
- Receives: Updates from every loop step.
- Returns: Current task state.
- Called by: Orchestrator, all components.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from jarvis.types import TaskLifecycle


class TaskState(BaseModel):
    """Runtime task state maintained by State Manager."""

    task_id: str
    lifecycle: TaskLifecycle = TaskLifecycle.CREATED
    plan_version: int = 1
    current_step_index: int = 0
    current_step_name: Optional[str] = None
    is_cancelled: bool = False
    deadline: Optional[datetime] = None
    retry_count: int = 0
    replan_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    last_verified_state: Optional[Dict[str, Any]] = None


class StateManager:
    """State Manager stub managing in-memory task states."""

    def __init__(self) -> None:
        self._tasks: Dict[str, TaskState] = {}

    def create_task(self, task_id: str, deadline: Optional[datetime] = None) -> TaskState:
        if task_id in self._tasks:
            return self._tasks[task_id]
        state = TaskState(task_id=task_id, deadline=deadline)
        self._tasks[task_id] = state
        return state

    def get_state(self, task_id: str) -> Optional[TaskState]:
        return self._tasks.get(task_id)

    def is_cancelled(self, task_id: str) -> bool:
        task = self.get_state(task_id)
        return task.is_cancelled if task else False

    def is_deadline_exceeded(self, task_id: str) -> bool:
        task = self.get_state(task_id)
        if task and task.deadline:
            return datetime.now(timezone.utc) > task.deadline
        return False

    def update_lifecycle(self, task_id: str, lifecycle: TaskLifecycle) -> None:
        task = self.get_state(task_id)
        if task:
            task.lifecycle = lifecycle

    def update_step(self, task_id: str, step_index: int, step_name: str) -> None:
        task = self.get_state(task_id)
        if task:
            task.current_step_index = step_index
            task.current_step_name = step_name

    def set_last_verified_state(self, task_id: str, verified_state: Dict[str, Any]) -> None:
        task = self.get_state(task_id)
        if task:
            task.last_verified_state = verified_state


_default_state_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    global _default_state_manager
    if _default_state_manager is None:
        _default_state_manager = StateManager()
    return _default_state_manager
