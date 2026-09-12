"""Planner module (Phase 0 stub).

Per Section 4:
- Planner owns: Task graph, expected outcomes per step.
- Planner does NOT own: Execution, tool invocation.
- Receives: Intent, task profile, read-only Memory.
- Returns: Task graph.
- Called by: Orchestrator.
(To be fully implemented by Sujeet in Phase 1).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """A planned discrete action within a task graph."""

    step_id: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    expected_outcome: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""


class TaskGraph(BaseModel):
    """Structured execution plan produced by Planner."""

    task_id: str
    steps: List[PlanStep] = Field(default_factory=list)
    version: int = 1


class Planner:
    """Planner stub."""

    def plan(self, intent: str, task_id: str) -> TaskGraph:
        """Produce a task graph for the requested intent."""
        return TaskGraph(
            task_id=task_id,
            steps=[
                PlanStep(
                    step_id="step-1",
                    tool_name="noop_tool",
                    arguments={"intent": intent},
                    expected_outcome={"status": "completed"},
                    description=f"Stub action for intent: {intent}",
                )
            ],
        )


_default_planner: Optional[Planner] = None


def get_planner() -> Planner:
    global _default_planner
    if _default_planner is None:
        _default_planner = Planner()
    return _default_planner
