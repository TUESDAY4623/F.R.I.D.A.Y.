"""Canonical 11-step execution loop state machine.

Per Section 2:
1. Check cancellation / deadline
2. Observe current state (skip if a prior deterministic tool result already covers it)
3. Decide next action (Orchestrator, using Planner's task graph + current State)
4. Policy check (Policy Engine: ALLOW / CONFIRM / DENY)
5. Approval if required (Approval Manager <-> User)
6. Dispatch action (Tool Manager -> Tool)
7. Observe resulting state
8. Verify expected outcome (Verification Engine)
9. Update State (State Manager)
10. Log event (Event Logger)
11. Continue -> retry -> recover -> replan -> complete

"Orchestrator drives this sequence. It does not implement observation, verification,
policy, or tool execution itself — it calls the owning component for each and acts on the result."
In Phase 0, every step is an explicit state machine step implemented as a no-op stub
that logs its own name through Event Logger.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from jarvis.approval import ApprovalManager, get_approval_manager
from jarvis.logger import EventLogger, EventType, get_logger
from jarvis.observation import Observation, ObservationManager, get_observation_manager
from jarvis.planner import Planner, TaskGraph, get_planner
from jarvis.policy import PolicyEngine, get_policy_engine
from jarvis.recovery import RecoveryManager, get_recovery_manager
from jarvis.state import StateManager, get_state_manager
from jarvis.tools import ToolManager
from jarvis.tools.contract import ToolResult
from jarvis.types import (
    ApprovalDecision,
    ApprovalStatus,
    FailureClassification,
    PolicyDecision,
    RecoveryStrategy,
    TaskLifecycle,
    VerificationStatus,
)
from jarvis.verification import VerificationEngine, VerificationResult, get_verification_engine


class LoopStep(str, Enum):
    """The 11 canonical loop steps defined in Section 2."""

    STEP_1_CHECK_CANCELLATION = "1. Check cancellation / deadline"
    STEP_2_OBSERVE_CURRENT_STATE = "2. Observe current state"
    STEP_3_DECIDE_NEXT_ACTION = "3. Decide next action"
    STEP_4_POLICY_CHECK = "4. Policy check"
    STEP_5_APPROVAL_IF_REQUIRED = "5. Approval if required"
    STEP_6_DISPATCH_ACTION = "6. Dispatch action"
    STEP_7_OBSERVE_RESULTING_STATE = "7. Observe resulting state"
    STEP_8_VERIFY_EXPECTED_OUTCOME = "8. Verify expected outcome"
    STEP_9_UPDATE_STATE = "9. Update State"
    STEP_10_LOG_EVENT = "10. Log event"
    STEP_11_EVALUATE_TRANSITION = "11. Continue -> retry -> recover -> replan -> complete"


class LoopStatus(str, Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    STEP_COMPLETED = "step_completed"
    LOOP_COMPLETED = "loop_completed"
    RETRYING = "retrying"
    RECOVERING = "recovering"
    REPLANNING = "replanning"
    CANCELLED = "cancelled"
    FAILED = "failed"


class LoopContext(BaseModel):
    """Execution context passed through the 11-step state machine."""

    task_id: str
    intent: str
    current_step: LoopStep = LoopStep.STEP_1_CHECK_CANCELLATION
    status: LoopStatus = LoopStatus.INITIALIZED
    executed_steps: List[str] = Field(default_factory=list)

    # Component data carried across steps
    task_graph: Optional[TaskGraph] = None
    action: Optional[Dict[str, Any]] = None
    observation_before: Optional[Observation] = None
    policy_decision: Optional[PolicyDecision] = None
    approval_decision: Optional[ApprovalDecision] = None
    tool_result: Optional[ToolResult] = None
    observation_after: Optional[Observation] = None
    verification_result: Optional[VerificationResult] = None


class CanonicalLoopStateMachine:
    """Explicit state machine implementing Section 2's canonical 11-step loop."""

    def __init__(
        self,
        logger: Optional[EventLogger] = None,
        state_manager: Optional[StateManager] = None,
        observation_manager: Optional[ObservationManager] = None,
        planner: Optional[Planner] = None,
        policy_engine: Optional[PolicyEngine] = None,
        approval_manager: Optional[ApprovalManager] = None,
        tool_manager: Optional[ToolManager] = None,
        verification_engine: Optional[VerificationEngine] = None,
        recovery_manager: Optional[RecoveryManager] = None,
    ) -> None:
        self.logger = logger or get_logger()
        self.state_manager = state_manager or get_state_manager()
        self.observation_manager = observation_manager or get_observation_manager()
        self.planner = planner or get_planner()
        self.policy_engine = policy_engine or get_policy_engine()
        self.approval_manager = approval_manager or get_approval_manager()
        self.tool_manager = tool_manager or ToolManager()
        self.verification_engine = verification_engine or get_verification_engine()
        self.recovery_manager = recovery_manager or get_recovery_manager()

        # Define step order
        self.steps_sequence = [
            (LoopStep.STEP_1_CHECK_CANCELLATION, self._step_1_check_cancellation),
            (LoopStep.STEP_2_OBSERVE_CURRENT_STATE, self._step_2_observe_current_state),
            (LoopStep.STEP_3_DECIDE_NEXT_ACTION, self._step_3_decide_next_action),
            (LoopStep.STEP_4_POLICY_CHECK, self._step_4_policy_check),
            (LoopStep.STEP_5_APPROVAL_IF_REQUIRED, self._step_5_approval_if_required),
            (LoopStep.STEP_6_DISPATCH_ACTION, self._step_6_dispatch_action),
            (LoopStep.STEP_7_OBSERVE_RESULTING_STATE, self._step_7_observe_resulting_state),
            (LoopStep.STEP_8_VERIFY_EXPECTED_OUTCOME, self._step_8_verify_expected_outcome),
            (LoopStep.STEP_9_UPDATE_STATE, self._step_9_update_state),
            (LoopStep.STEP_10_LOG_EVENT, self._step_10_log_event),
            (LoopStep.STEP_11_EVALUATE_TRANSITION, self._step_11_evaluate_transition),
        ]

    # --- Step 1: Check cancellation / deadline ---
    def _step_1_check_cancellation(self, ctx: LoopContext) -> None:
        step_name = LoopStep.STEP_1_CHECK_CANCELLATION.value
        self.logger.log_step(step_name=step_name, task_id=ctx.task_id)
        ctx.executed_steps.append(step_name)

        # Delegate check to State Manager
        if self.state_manager.is_cancelled(ctx.task_id):
            ctx.status = LoopStatus.CANCELLED
            self.logger.log_event(
                event_type=EventType.TASK_CANCELLED,
                source="orchestrator",
                message=f"Task {ctx.task_id} cancelled at Step 1",
                task_id=ctx.task_id,
            )
            return
        if self.state_manager.is_deadline_exceeded(ctx.task_id):
            ctx.status = LoopStatus.FAILED
            self.logger.log_event(
                event_type=EventType.TASK_TIMEOUT,
                source="orchestrator",
                message=f"Task {ctx.task_id} timed out / deadline exceeded at Step 1",
                task_id=ctx.task_id,
            )
            return

    # --- Step 2: Observe current state ---
    def _step_2_observe_current_state(self, ctx: LoopContext) -> None:
        step_name = LoopStep.STEP_2_OBSERVE_CURRENT_STATE.value
        self.logger.log_step(step_name=step_name, task_id=ctx.task_id)
        ctx.executed_steps.append(step_name)

        # Delegate observation to Observation Manager
        ctx.observation_before = self.observation_manager.observe(
            target="current_desktop_state",
            skip_if_cached=True,
        )

    # --- Step 3: Decide next action ---
    def _step_3_decide_next_action(self, ctx: LoopContext) -> None:
        step_name = LoopStep.STEP_3_DECIDE_NEXT_ACTION.value
        self.logger.log_step(step_name=step_name, task_id=ctx.task_id)
        ctx.executed_steps.append(step_name)

        # Orchestrator decides action using Planner task graph + current State
        if not ctx.task_graph:
            ctx.task_graph = self.planner.plan(intent=ctx.intent, task_id=ctx.task_id)

        next_step = (
            ctx.task_graph.get_next_pending_step()
            if hasattr(ctx.task_graph, "get_next_pending_step")
            else None
        )
        if next_step:
            ctx.action = {
                "tool_name": next_step.tool_name,
                "arguments": next_step.arguments,
                "step_id": next_step.step_id,
                "expected_outcome": next_step.expected_outcome,
                "description": next_step.description,
            }
        else:
            ctx.action = {
                "tool_name": "noop_tool",
                "arguments": {"intent": ctx.intent},
                "step_id": "step-1",
                "expected_outcome": {"status": "completed"},
            }

    # --- Step 4: Policy check ---
    def _step_4_policy_check(self, ctx: LoopContext) -> None:
        step_name = LoopStep.STEP_4_POLICY_CHECK.value
        self.logger.log_step(step_name=step_name, task_id=ctx.task_id)
        ctx.executed_steps.append(step_name)

        action_name = ctx.action.get("tool_name", "") if ctx.action else ""
        arguments = ctx.action.get("arguments", {}) if ctx.action else {}

        # Look up tool contract from registry if tool is registered
        contract = None
        if hasattr(self.tool_manager, "registry") and self.tool_manager.registry.has(action_name):
            contract = self.tool_manager.registry.get(action_name).contract

        # Delegate check to Policy Engine
        ctx.policy_decision = self.policy_engine.check(
            action_name=action_name,
            arguments=arguments,
            contract=contract,
        )

    # --- Step 5: Approval if required ---
    def _step_5_approval_if_required(self, ctx: LoopContext) -> None:
        step_name = LoopStep.STEP_5_APPROVAL_IF_REQUIRED.value
        self.logger.log_step(step_name=step_name, task_id=ctx.task_id)
        ctx.executed_steps.append(step_name)

        # If Policy requires approval (CONFIRM), delegate to Approval Manager
        if ctx.policy_decision == PolicyDecision.CONFIRM:
            from jarvis.approval import ApprovalRequest

            tool_name = ctx.action.get("tool_name", "") if ctx.action else ""
            request = ApprovalRequest(
                action=tool_name,
                target="desktop",
                consequences="Action requires confirmation",
                reversible=False,
                reason="Policy CONFIRM trigger",
            )
            self.state_manager.set_approval_status(ctx.task_id, ApprovalStatus.PENDING)
            self.logger.log_event(
                event_type=EventType.TASK_APPROVAL_PENDING,
                source="orchestrator",
                message=f"Approval pending for action '{tool_name}'",
                task_id=ctx.task_id,
                payload={"action": tool_name},
            )
            ctx.approval_decision = self.approval_manager.request_approval(request)

            if ctx.approval_decision == ApprovalDecision.APPROVE:
                self.state_manager.set_approval_status(ctx.task_id, ApprovalStatus.APPROVED)
                self.logger.log_event(
                    event_type=EventType.TASK_APPROVAL_APPROVED,
                    source="orchestrator",
                    message=f"Action '{tool_name}' approved by user",
                    task_id=ctx.task_id,
                    payload={"action": tool_name},
                )
            elif ctx.approval_decision == ApprovalDecision.DENY:
                self.state_manager.set_approval_status(ctx.task_id, ApprovalStatus.DENIED)
                self.logger.log_event(
                    event_type=EventType.TASK_APPROVAL_DENIED,
                    source="orchestrator",
                    message=f"Action '{tool_name}' denied by user",
                    task_id=ctx.task_id,
                    payload={"action": tool_name},
                )
            elif ctx.approval_decision == ApprovalDecision.CANCEL:
                self.state_manager.set_approval_status(ctx.task_id, ApprovalStatus.CANCELLED)
                self.state_manager.cancel_task(ctx.task_id)
                self.logger.log_event(
                    event_type=EventType.TASK_CANCELLED,
                    source="orchestrator",
                    message=f"Task {ctx.task_id} cancelled during approval for '{tool_name}'",
                    task_id=ctx.task_id,
                    payload={"action": tool_name},
                )
        else:
            ctx.approval_decision = ApprovalDecision.APPROVE
            self.state_manager.set_approval_status(ctx.task_id, ApprovalStatus.NOT_REQUIRED)

    # --- Step 6: Dispatch action ---
    def _step_6_dispatch_action(self, ctx: LoopContext) -> None:
        step_name = LoopStep.STEP_6_DISPATCH_ACTION.value
        self.logger.log_step(step_name=step_name, task_id=ctx.task_id)
        ctx.executed_steps.append(step_name)

        tool_name = ctx.action.get("tool_name", "noop_tool") if ctx.action else "noop_tool"
        arguments = ctx.action.get("arguments", {}) if ctx.action else {}

        # Log tool started event for observability (Section 9)
        self.logger.log_event(
            event_type=EventType.TOOL_STARTED,
            source="orchestrator",
            message=f"Dispatching tool '{tool_name}'",
            task_id=ctx.task_id,
            payload={"tool_name": tool_name, "arguments": arguments},
        )

        # Delegate execution to Tool Manager with approval decision
        ctx.tool_result = self.tool_manager.dispatch(
            tool_name=tool_name,
            arguments=arguments,
            approval_decision=ctx.approval_decision,
        )

        # Log tool completed / failed event for observability
        if ctx.tool_result and ctx.tool_result.success:
            self.logger.log_event(
                event_type=EventType.TOOL_COMPLETED,
                source="orchestrator",
                message=f"Tool '{tool_name}' completed successfully",
                task_id=ctx.task_id,
                payload={"tool_name": tool_name, "result": ctx.tool_result.data},
            )
        else:
            err = ctx.tool_result.error if ctx.tool_result else "Execution failed"
            self.logger.log_event(
                event_type=EventType.TOOL_FAILED,
                source="orchestrator",
                message=f"Tool '{tool_name}' failed: {err}",
                task_id=ctx.task_id,
                payload={"tool_name": tool_name, "error": err},
            )

    # --- Step 7: Observe resulting state ---
    def _step_7_observe_resulting_state(self, ctx: LoopContext) -> None:
        step_name = LoopStep.STEP_7_OBSERVE_RESULTING_STATE.value
        self.logger.log_step(step_name=step_name, task_id=ctx.task_id)
        ctx.executed_steps.append(step_name)

        # Delegate observation to Observation Manager
        ctx.observation_after = self.observation_manager.observe(target="post_action_state")
        if ctx.tool_result and ctx.observation_after:
            ctx.observation_after.state["tool_success"] = ctx.tool_result.success
            ctx.observation_after.state["tool_data"] = ctx.tool_result.data
            ctx.observation_after.state["tool_error"] = ctx.tool_result.error

    # --- Step 8: Verify expected outcome ---
    def _step_8_verify_expected_outcome(self, ctx: LoopContext) -> None:
        step_name = LoopStep.STEP_8_VERIFY_EXPECTED_OUTCOME.value
        self.logger.log_step(step_name=step_name, task_id=ctx.task_id)
        ctx.executed_steps.append(step_name)

        # Delegate verification to Verification Engine
        expected = (
            ctx.action.get("expected_outcome", {"status": "completed"})
            if ctx.action
            else {"status": "completed"}
        )
        obs = ctx.observation_after or Observation()
        ctx.verification_result = self.verification_engine.verify(expected, obs)

    # --- Step 9: Update State ---
    def _step_9_update_state(self, ctx: LoopContext) -> None:
        step_name = LoopStep.STEP_9_UPDATE_STATE.value
        self.logger.log_step(step_name=step_name, task_id=ctx.task_id)
        ctx.executed_steps.append(step_name)

        # Delegate state updates to State Manager
        step_id = ctx.action.get("step_id", "step-1") if ctx.action else "step-1"
        self.state_manager.update_step(
            task_id=ctx.task_id,
            step_index=1,
            step_name=step_id,
        )
        if ctx.tool_result and hasattr(self.state_manager, "record_step_result"):
            self.state_manager.record_step_result(
                task_id=ctx.task_id,
                step_id=step_id,
                result={
                    "success": ctx.tool_result.success,
                    "data": ctx.tool_result.data,
                    "error": ctx.tool_result.error,
                },
            )
        if ctx.verification_result and ctx.verification_result.status == VerificationStatus.PASS:
            self.state_manager.set_last_verified_state(
                task_id=ctx.task_id,
                verified_state={
                    step_id: "verified",
                    "data": ctx.tool_result.data if ctx.tool_result else None,
                },
            )
            if ctx.task_graph and hasattr(ctx.task_graph, "mark_step_completed"):
                ctx.task_graph.mark_step_completed(step_id)
        else:
            if ctx.task_graph and hasattr(ctx.task_graph, "mark_step_failed"):
                ctx.task_graph.mark_step_failed(step_id)

    # --- Step 10: Log event ---
    def _step_10_log_event(self, ctx: LoopContext) -> None:
        step_name = LoopStep.STEP_10_LOG_EVENT.value
        self.logger.log_step(step_name=step_name, task_id=ctx.task_id)
        ctx.executed_steps.append(step_name)

        # Delegate to Event Logger (first real component)
        is_verified = bool(
            ctx.verification_result
            and ctx.verification_result.status == VerificationStatus.PASS
        )
        self.logger.log_event(
            event_type=EventType.TASK_STATUS_CHANGED,
            source="orchestrator",
            message=f"Task {ctx.task_id} completed loop iteration",
            task_id=ctx.task_id,
            payload={"verified": is_verified},
        )

    # --- Step 11: Continue -> retry -> recover -> replan -> complete ---
    def _step_11_evaluate_transition(self, ctx: LoopContext) -> None:
        step_name = LoopStep.STEP_11_EVALUATE_TRANSITION.value
        self.logger.log_step(step_name=step_name, task_id=ctx.task_id)
        ctx.executed_steps.append(step_name)

        # Check if task was cancelled during approval or execution
        if self.state_manager.is_cancelled(ctx.task_id) or (
            ctx.approval_decision == ApprovalDecision.CANCEL
        ):
            ctx.status = LoopStatus.CANCELLED
            return

        step_success = bool(
            ctx.tool_result
            and ctx.tool_result.success
            and (not ctx.verification_result or ctx.verification_result.status == VerificationStatus.PASS)
        )

        step_id = ctx.action.get("step_id", "step-1") if ctx.action else "step-1"
        action_name = ctx.action.get("tool_name", "") if ctx.action else ""
        arguments = ctx.action.get("arguments", {}) if ctx.action else {}

        if step_success:
            # Check if there are more pending steps in the task graph
            has_pending = False
            if ctx.task_graph and hasattr(ctx.task_graph, "get_next_pending_step"):
                has_pending = ctx.task_graph.get_next_pending_step() is not None

            if has_pending:
                ctx.status = LoopStatus.STEP_COMPLETED
            else:
                ctx.status = LoopStatus.LOOP_COMPLETED
            return

        # Failure handling (tool error, verification failure, policy/approval denial)
        task_state = self.state_manager.get_state(ctx.task_id)
        retry_count = task_state.retry_count if task_state else 0
        replan_count = task_state.replan_count if task_state else 0
        recovery_attempts = task_state.recovery_attempts if task_state else 0

        err_msg = ""
        if ctx.tool_result and not ctx.tool_result.success:
            err_msg = ctx.tool_result.error or "Tool dispatch failed"
        elif ctx.verification_result and ctx.verification_result.status == VerificationStatus.FAIL:
            err_msg = ctx.verification_result.reason or "Verification failed"
        else:
            err_msg = "Unknown step execution failure"

        rec_context = {
            "retry_count": retry_count,
            "replan_count": replan_count,
            "recovery_attempts": recovery_attempts,
            "verification_failure": bool(
                ctx.verification_result and ctx.verification_result.status == VerificationStatus.FAIL
            ),
            "step_id": step_id,
        }

        recovery_action = self.recovery_manager.handle_failure(
            failure_type=err_msg,
            task_id=ctx.task_id,
            action_name=action_name,
            arguments=arguments,
            context=rec_context,
        )

        self.state_manager.record_failure(
            task_id=ctx.task_id,
            error=err_msg,
            classification=recovery_action.classification,
        )

        if recovery_action.strategy == RecoveryStrategy.RETRY:
            self.state_manager.increment_retry(ctx.task_id)
            self.logger.log_event(
                event_type=EventType.TASK_RETRY,
                source="orchestrator",
                message=f"Retrying task {ctx.task_id}: {recovery_action.reason}",
                task_id=ctx.task_id,
                payload={"step_id": step_id, "retry_count": retry_count + 1},
            )
            # Reset current step to pending for retry
            if ctx.task_graph:
                for s in ctx.task_graph.steps:
                    if s.step_id == step_id:
                        s.status = "pending"
            ctx.status = LoopStatus.RETRYING

        elif recovery_action.strategy == RecoveryStrategy.RECOVER:
            self.state_manager.increment_recovery_attempts(ctx.task_id)
            self.logger.log_event(
                event_type=EventType.TASK_RECOVERY_STARTED,
                source="orchestrator",
                message=f"Recovery started for task {ctx.task_id}: {recovery_action.reason}",
                task_id=ctx.task_id,
                payload={
                    "step_id": step_id,
                    "recovery_steps": [s.model_dump() for s in recovery_action.recovery_steps],
                },
            )
            if ctx.task_graph:
                new_steps = []
                for s in ctx.task_graph.steps:
                    if s.step_id == step_id:
                        new_steps.extend(recovery_action.recovery_steps)
                        s.status = "pending"
                        new_steps.append(s)
                    else:
                        new_steps.append(s)
                ctx.task_graph.steps = new_steps
                self.state_manager.set_active_plan(ctx.task_id, ctx.task_graph.model_dump())
            ctx.status = LoopStatus.RECOVERING

        elif recovery_action.strategy == RecoveryStrategy.REPLAN:
            self.state_manager.increment_replan(ctx.task_id)
            self.logger.log_event(
                event_type=EventType.TASK_REPLAN,
                source="orchestrator",
                message=f"Replanning task {ctx.task_id}: {recovery_action.reason}",
                task_id=ctx.task_id,
                payload={"step_id": step_id, "replan_count": replan_count + 1},
            )
            if ctx.task_graph:
                self.state_manager.archive_plan(ctx.task_id, ctx.task_graph.model_dump())
                new_graph = self.planner.replan(
                    task_id=ctx.task_id,
                    original_plan=ctx.task_graph,
                    failure_reason=err_msg,
                    context=rec_context,
                )
                ctx.task_graph = new_graph
                self.state_manager.set_active_plan(ctx.task_id, new_graph.model_dump())
                self.state_manager.set_plan_version(ctx.task_id, new_graph.version)
            ctx.status = LoopStatus.REPLANNING

        else:
            ctx.status = LoopStatus.FAILED

    def run_cycle(self, context: LoopContext) -> LoopContext:
        """Run a single iteration across all 11 steps of the canonical loop."""
        context.status = LoopStatus.RUNNING
        for step_enum, step_func in self.steps_sequence:
            if context.status in (LoopStatus.CANCELLED, LoopStatus.FAILED):
                break
            context.current_step = step_enum
            step_func(context)
            if context.status in (LoopStatus.CANCELLED, LoopStatus.FAILED):
                break

        return context
