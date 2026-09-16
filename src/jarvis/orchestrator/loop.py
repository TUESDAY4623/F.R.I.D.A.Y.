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
from jarvis.types import ApprovalDecision, PolicyDecision, TaskLifecycle, VerificationStatus
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
            return
        if self.state_manager.is_deadline_exceeded(ctx.task_id):
            ctx.status = LoopStatus.FAILED
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

            request = ApprovalRequest(
                action=ctx.action.get("tool_name", "") if ctx.action else "",
                target="desktop",
                consequences="Action requires confirmation",
                reversible=False,
                reason="Policy CONFIRM trigger",
            )
            ctx.approval_decision = self.approval_manager.request_approval(request)
        else:
            ctx.approval_decision = ApprovalDecision.APPROVE

    # --- Step 6: Dispatch action ---
    def _step_6_dispatch_action(self, ctx: LoopContext) -> None:
        step_name = LoopStep.STEP_6_DISPATCH_ACTION.value
        self.logger.log_step(step_name=step_name, task_id=ctx.task_id)
        ctx.executed_steps.append(step_name)

        # Delegate execution to Tool Manager
        tool_name = ctx.action.get("tool_name", "noop_tool") if ctx.action else "noop_tool"
        arguments = ctx.action.get("arguments", {}) if ctx.action else {}
        ctx.tool_result = self.tool_manager.dispatch(tool_name=tool_name, arguments=arguments)

    # --- Step 7: Observe resulting state ---
    def _step_7_observe_resulting_state(self, ctx: LoopContext) -> None:
        step_name = LoopStep.STEP_7_OBSERVE_RESULTING_STATE.value
        self.logger.log_step(step_name=step_name, task_id=ctx.task_id)
        ctx.executed_steps.append(step_name)

        # Delegate observation to Observation Manager
        ctx.observation_after = self.observation_manager.observe(target="post_action_state")

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

    # --- Step 10: Log event ---
    def _step_10_log_event(self, ctx: LoopContext) -> None:
        step_name = LoopStep.STEP_10_LOG_EVENT.value
        self.logger.log_step(step_name=step_name, task_id=ctx.task_id)
        ctx.executed_steps.append(step_name)

        # Delegate to Event Logger (first real component)
        self.logger.log_event(
            event_type=EventType.TASK_STATUS_CHANGED,
            source="orchestrator",
            message=f"Task {ctx.task_id} completed loop iteration",
            task_id=ctx.task_id,
            payload={"verified": True},
        )

    # --- Step 11: Continue -> retry -> recover -> replan -> complete ---
    def _step_11_evaluate_transition(self, ctx: LoopContext) -> None:
        step_name = LoopStep.STEP_11_EVALUATE_TRANSITION.value
        self.logger.log_step(step_name=step_name, task_id=ctx.task_id)
        ctx.executed_steps.append(step_name)

        # Determine transition: for Phase 0 stub, we complete successfully
        ctx.status = LoopStatus.LOOP_COMPLETED

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
