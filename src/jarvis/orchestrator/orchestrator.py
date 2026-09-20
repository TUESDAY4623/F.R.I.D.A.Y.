"""Agent Orchestrator driving task execution through the canonical loop.

Per Section 2 & Section 4:
- Agent Orchestrator owns: Driving the loop, deciding "what next," retry/replan control flow.
- Agent Orchestrator does NOT own: Observation, verification, policy logic, tool execution
  (delegates all of these to owning components).
- Receives: User input text / intent.
- Returns: Agent execution result.
- Called by: UI shell / Application entry point.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

from jarvis.intent import IntentManager, get_intent_manager
from jarvis.logger import EventLogger, EventType, get_logger
from jarvis.orchestrator.loop import CanonicalLoopStateMachine, LoopContext, LoopStatus
from jarvis.planner import Planner, get_planner
from jarvis.response import ResponseManager, get_response_manager
from jarvis.state import StateManager, get_state_manager
from jarvis.types import TaskLifecycle


class TaskMetricsCollector:
    """Tracks latency, task success rate, and first-attempt pass per Section 15 & Phase 1 requirements."""

    def __init__(self) -> None:
        self.total_tasks: int = 0
        self.successful_tasks: int = 0
        self.first_attempt_successes: int = 0
        self.latencies_ms: List[float] = []

    def record_task(self, success: bool, latency_ms: float, retries: int = 0) -> None:
        self.total_tasks += 1
        if success:
            self.successful_tasks += 1
            if retries == 0:
                self.first_attempt_successes += 1
        self.latencies_ms.append(latency_ms)

    def get_summary(self) -> Dict[str, Any]:
        avg_latency = (
            sum(self.latencies_ms) / len(self.latencies_ms) if self.latencies_ms else 0.0
        )
        success_rate = (
            (self.successful_tasks / self.total_tasks * 100.0) if self.total_tasks > 0 else 0.0
        )
        first_attempt_rate = (
            (self.first_attempt_successes / self.total_tasks * 100.0)
            if self.total_tasks > 0
            else 0.0
        )
        return {
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "task_success_rate": success_rate,
            "first_attempt_success_rate": first_attempt_rate,
            "avg_latency_ms": round(avg_latency, 2),
        }


class AgentOrchestrator:
    """The central orchestrator driving the 11-step canonical execution loop for Phase 1 Core Brain."""

    def __init__(
        self,
        loop_state_machine: Optional[CanonicalLoopStateMachine] = None,
        logger: Optional[EventLogger] = None,
        state_manager: Optional[StateManager] = None,
        intent_manager: Optional[IntentManager] = None,
        planner: Optional[Planner] = None,
        response_manager: Optional[ResponseManager] = None,
    ) -> None:
        self.logger = logger or get_logger()
        self.state_manager = state_manager or get_state_manager()
        self.intent_manager = intent_manager or get_intent_manager()
        self.planner = planner or get_planner()
        self.response_manager = response_manager or get_response_manager()
        self.state_machine = loop_state_machine or CanonicalLoopStateMachine(
            logger=self.logger,
            state_manager=self.state_manager,
            planner=self.planner,
        )
        self.metrics = TaskMetricsCollector()

    def execute_task(self, intent: str, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a task from user intent by driving the canonical loop."""
        start_time = time.perf_counter()
        tid = task_id or f"task_{uuid4().hex[:8]}"

        # 1. Parse structured intent via IntentManager
        intent_result = self.intent_manager.detect_intent(intent)

        # 2. Plan task graph via Planner
        task_graph = self.planner.plan(intent=intent_result, task_id=tid)

        # 3. Initialize task in State Manager and Event Logger
        task_state = self.state_manager.create_task(
            task_id=tid,
            metadata={"action_type": intent_result.action_type, "raw_intent": intent},
        )
        self.state_manager.set_active_plan(tid, task_graph.model_dump())
        self.state_manager.set_plan_version(tid, task_graph.version)
        self.state_manager.update_lifecycle(tid, TaskLifecycle.CREATED)

        self.logger.log_event(
            event_type=EventType.TASK_CREATED,
            source="orchestrator",
            message=f"Created task {tid} with intent: '{intent}'",
            task_id=tid,
            payload={"intent": intent, "action_type": intent_result.action_type},
        )

        self.logger.log_event(
            event_type=EventType.ORCHESTRATOR_LOOP_START,
            source="orchestrator",
            message=f"Starting 11-step canonical execution loop for task {tid}",
            task_id=tid,
        )

        self.state_manager.update_lifecycle(tid, TaskLifecycle.EXECUTING)

        # 4. Run canonical loop cycles until terminal state
        context = LoopContext(task_id=tid, intent=intent, task_graph=task_graph)
        result_context = context
        max_loop_iterations = 25
        iteration = 0

        while iteration < max_loop_iterations:
            iteration += 1
            result_context = self.state_machine.run_cycle(context)

            if result_context.status in (
                LoopStatus.LOOP_COMPLETED,
                LoopStatus.CANCELLED,
                LoopStatus.FAILED,
            ):
                break

        if result_context.status not in (
            LoopStatus.LOOP_COMPLETED,
            LoopStatus.CANCELLED,
            LoopStatus.FAILED,
        ):
            result_context.status = LoopStatus.FAILED

        # 5. Finalize status and update State Manager
        task_state = self.state_manager.get_state(tid)
        if result_context.status == LoopStatus.LOOP_COMPLETED:
            self.state_manager.update_lifecycle(tid, TaskLifecycle.COMPLETED)
            if task_state and task_state.recovery_attempts > 0:
                self.logger.log_event(
                    event_type=EventType.TASK_RECOVERY_COMPLETED,
                    source="orchestrator",
                    message=f"Task {tid} recovered and completed successfully",
                    task_id=tid,
                )
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

        latency_ms = (time.perf_counter() - start_time) * 1000.0
        retries = task_state.retry_count if task_state else 0
        self.metrics.record_task(success=success, latency_ms=latency_ms, retries=retries)

        # Format human-readable response via Response Manager
        res_payload: Dict[str, Any] = {
            "task_id": tid,
            "success": success,
            "status": result_context.status.value,
            "executed_steps": result_context.executed_steps,
            "steps_count": len(result_context.executed_steps),
            "tool_result": (
                result_context.tool_result.model_dump()
                if result_context.tool_result
                else None
            ),
            "plan_version": (
                task_state.plan_version
                if task_state
                else (result_context.task_graph.version if result_context.task_graph else 1)
            ),
            "latency_ms": round(latency_ms, 2),
        }
        response_text = self.response_manager.format_response(res_payload)
        res_payload["response"] = response_text

        return res_payload
