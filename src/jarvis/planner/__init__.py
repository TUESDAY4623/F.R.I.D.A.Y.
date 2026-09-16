"""Planner module (Phase 1).

Per Section 4 & Section 2:
- Planner owns: Generating structured task graphs with expected outcomes per step.
- Planner does NOT own: Execution, tool invocation, policy checks, or mutating Memory.
- Receives: Intent (or IntentResult), task_id, context, read-only Memory.
- Returns: TaskGraph containing planned discrete action steps.
- Called by: Orchestrator.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field

from jarvis.intent import IntentResult, get_intent_manager
from jarvis.memory import MemoryManager, get_memory_manager


class PlanStep(BaseModel):
    """A planned discrete action within a task graph."""

    step_id: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    expected_outcome: Dict[str, Any] = Field(default_factory=dict)
    description: str = ""
    status: str = "pending"  # "pending", "in_progress", "completed", "failed"


class TaskGraph(BaseModel):
    """Structured execution plan produced by the Planner."""

    task_id: str
    intent: str = ""
    steps: List[PlanStep] = Field(default_factory=list)
    version: int = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_next_pending_step(self) -> Optional[PlanStep]:
        """Return the first step with status 'pending'."""
        for step in self.steps:
            if step.status == "pending":
                return step
        return None

    def mark_step_completed(self, step_id: str) -> None:
        """Mark a given step as completed."""
        for step in self.steps:
            if step.step_id == step_id:
                step.status = "completed"

    def mark_step_failed(self, step_id: str) -> None:
        """Mark a given step as failed."""
        for step in self.steps:
            if step.step_id == step_id:
                step.status = "failed"

    def all_completed(self) -> bool:
        """Check if all planned steps are completed."""
        return len(self.steps) > 0 and all(step.status == "completed" for step in self.steps)


class Planner:
    """Task Graph Planner for Phase 1 Core Brain.

    Produces deterministic TaskGraphs for file operations and core loop flows.
    Reads Memory in a read-only manner. Never invokes tools or mutates Memory directly.
    """

    def __init__(self, memory_manager: Optional[MemoryManager] = None) -> None:
        self._memory_manager = memory_manager

    @property
    def memory_manager(self) -> Optional[MemoryManager]:
        return self._memory_manager

    def plan(
        self,
        intent: Union[str, IntentResult],
        task_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskGraph:
        """Produce a structured TaskGraph for the requested intent."""
        # Normalize intent to IntentResult if given as raw string
        if isinstance(intent, str):
            intent_mgr = get_intent_manager()
            intent_res = intent_mgr.detect_intent(intent, extra_context=context)
        else:
            intent_res = intent

        steps: List[PlanStep] = []
        action_type = intent_res.action_type
        entities = intent_res.entities

        # Read-only memory preferences
        metadata: Dict[str, Any] = {"action_type": action_type}
        if self._memory_manager is not None:
            mem_slice = self._memory_manager.get_slice()
            metadata["preferences"] = mem_slice.preferences

        # Generate deterministic plan steps based on action type
        if action_type == "file_read":
            path = entities.get("path", "")
            steps.append(
                PlanStep(
                    step_id="step-1",
                    tool_name="read_file",
                    arguments={"path": path},
                    expected_outcome={"status": "completed", "action": "file_read", "path": path},
                    description=f"Read contents of file: {path}",
                )
            )

        elif action_type == "file_list":
            path = entities.get("path", "")
            steps.append(
                PlanStep(
                    step_id="step-1",
                    tool_name="list_directory",
                    arguments={"path": path},
                    expected_outcome={"status": "completed", "action": "file_list", "path": path},
                    description=f"List entries in directory: {path}",
                )
            )

        elif action_type == "file_write":
            path = entities.get("path", "")
            content = entities.get("content", "")
            steps.append(
                PlanStep(
                    step_id="step-1",
                    tool_name="write_file",
                    arguments={"path": path, "content": content},
                    expected_outcome={"status": "completed", "action": "file_write", "path": path},
                    description=f"Write content to file: {path}",
                )
            )

        elif action_type == "file_move":
            src = entities.get("source_path", "")
            dest = entities.get("destination_path", "")
            steps.append(
                PlanStep(
                    step_id="step-1",
                    tool_name="move_file",
                    arguments={"source_path": src, "destination_path": dest},
                    expected_outcome={"status": "completed", "action": "file_move"},
                    description=f"Move file from {src} to {dest}",
                )
            )

        elif action_type == "file_pipeline":
            # Multi-step file pipeline: read source file, then write summary to target file
            src = entities.get("source_path", "")
            dest = entities.get("target_path", "")
            steps.append(
                PlanStep(
                    step_id="step-1",
                    tool_name="read_file",
                    arguments={"path": src},
                    expected_outcome={"status": "completed", "action": "file_read", "path": src},
                    description=f"Read source report: {src}",
                )
            )
            steps.append(
                PlanStep(
                    step_id="step-2",
                    tool_name="write_file",
                    arguments={"path": dest, "content": f"Summary of {src}: Operations Nominal."},
                    expected_outcome={"status": "completed", "action": "file_write", "path": dest},
                    description=f"Write summary report to: {dest}",
                )
            )

        else:
            # Default / general fallback: Single discrete noop step (guarantees 100% Phase 0 compatibility)
            steps.append(
                PlanStep(
                    step_id="step-1",
                    tool_name="noop_tool",
                    arguments={"intent": intent_res.intent},
                    expected_outcome={"status": "completed"},
                    description=f"Action for intent: {intent_res.intent}",
                )
            )

        return TaskGraph(
            task_id=task_id,
            intent=intent_res.intent,
            steps=steps,
            version=1,
            metadata=metadata,
        )


_default_planner: Optional[Planner] = None


def get_planner() -> Planner:
    """Return the shared singleton Planner."""
    global _default_planner
    if _default_planner is None:
        _default_planner = Planner()
    return _default_planner
