"""Agent Orchestrator driving task execution through the canonical loop.

Per Section 2 & Section 4:
- Agent Orchestrator owns: Driving the loop, deciding "what next," retry/replan control flow.
- Agent Orchestrator does NOT own: Observation, verification, policy logic, tool execution
  (delegates all of these).
- Receives: Task graph / Intent.
- Returns: Task result.
- Called by: Intent Manager / Application shell.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import uuid4

from jarvis.logger import EventLogger, EventType, get_logger
from jarvis.orchestrator.loop import CanonicalLoopStateMachine, LoopContext, LoopStatus
from jarvis.state import StateManager, get_state_manager
from jarvis.types import TaskLifecycle


class AgentOrchestrator:
    """The central orchestrator driving the 11-step execution loop."""

    def __init__(
        self,
        loop_state_machine: Optional[CanonicalLoopStateMachine] = None,
        logger: Optional[EventLogger] = None,
        state_manager: Optional[StateManager] = None,
    ) -> None:
        self.logger = logger or get_logger()
        self.state_manager = state_manager or get_state_manager()
        self.state_machine = loop_state_machine or CanonicalLoopStateMachine(
            logger=self.logger,
            state_manager=self.state_manager,
        )

    def execute_task(self, intent: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a task from user intent by driving the canonical loop."""
        tid = task_id or f"task_{uuid4().hex[:8]}"

        # Initialize task in State Manager and Event Logger
        self.state_manager.create_task(tid)
        self.state_manager.update_lifecycle(tid, TaskLifecycle.CREATED)

        self.logger.log_event(
            event_type=EventType.TASK_CREATED,
            source="orchestrator",
            message=f"Created task {tid} with intent: '{intent}'",
            task_id=tid,
            payload={"intent": intent},
        )

        self.logger.log_event(
            event_type=EventType.ORCHESTRATOR_LOOP_START,
            source="orchestrator",
            message=f"Starting 11-step canonical execution loop for task {tid}",
            task_id=tid,
        )

        self.state_manager.update_lifecycle(tid, TaskLifecycle.EXECUTING)

        # Run canonical loop
        context = LoopContext(task_id=tid, intent=intent)
        result_context = self.state_machine.run_cycle(context)

        # Finalize status
        if result_context.status == LoopStatus.LOOP_COMPLETED:
            self.state_manager.update_lifecycle(tid, TaskLifecycle.COMPLETED)
            self.logger.log_event(
                event_type=EventType.TASK_COMPLETED,
                source="orchestrator",
                message=f"Task {tid} completed successfully",
                task_id=tid,
            )
            success = True
        elif result_context.status == LoopStatus.CANCELLED:
            self.state_manager.update_lifecycle(tid, TaskLifecycle.CANCELLED)
            self.logger.log_event(
                event_type=EventType.TASK_CANCELLED,
                source="orchestrator",
                message=f"Task {tid} was cancelled",
                task_id=tid,
            )
            success = False
        else:
            self.state_manager.update_lifecycle(tid, TaskLifecycle.FAILED)
            self.logger.log_event(
                event_type=EventType.TASK_FAILED,
                source="orchestrator",
                message=f"Task {tid} failed",
                task_id=tid,
            )
            success = False

        self.logger.log_event(
            event_type=EventType.ORCHESTRATOR_LOOP_END,
            source="orchestrator",
            message=f"Ended 11-step canonical loop for task {tid}",
            task_id=tid,
            payload={"success": success, "executed_steps": result_context.executed_steps},
        )

        return {
            "task_id": tid,
            "success": success,
            "status": result_context.status.value,
            "executed_steps": result_context.executed_steps,
            "steps_count": len(result_context.executed_steps),
        }
