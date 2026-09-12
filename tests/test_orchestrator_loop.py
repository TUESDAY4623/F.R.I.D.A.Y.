"""Tests for Orchestrator's 11-step canonical loop state machine."""

from jarvis.logger import EventLogger
from jarvis.orchestrator import (
    AgentOrchestrator,
    CanonicalLoopStateMachine,
    LoopContext,
    LoopStatus,
    LoopStep,
)
from jarvis.state import StateManager
from jarvis.types import TaskLifecycle


def test_orchestrator_runs_all_11_steps_in_sequence():
    """Verify that all 11 steps execute and log their own names in exact Section 2 order."""
    logger = EventLogger(console_output=False)
    state_manager = StateManager()
    state_machine = CanonicalLoopStateMachine(logger=logger, state_manager=state_manager)

    context = LoopContext(task_id="test_task_1", intent="Test intent")
    result_context = state_machine.run_cycle(context)

    expected_steps = [
        LoopStep.STEP_1_CHECK_CANCELLATION.value,
        LoopStep.STEP_2_OBSERVE_CURRENT_STATE.value,
        LoopStep.STEP_3_DECIDE_NEXT_ACTION.value,
        LoopStep.STEP_4_POLICY_CHECK.value,
        LoopStep.STEP_5_APPROVAL_IF_REQUIRED.value,
        LoopStep.STEP_6_DISPATCH_ACTION.value,
        LoopStep.STEP_7_OBSERVE_RESULTING_STATE.value,
        LoopStep.STEP_8_VERIFY_EXPECTED_OUTCOME.value,
        LoopStep.STEP_9_UPDATE_STATE.value,
        LoopStep.STEP_10_LOG_EVENT.value,
        LoopStep.STEP_11_EVALUATE_TRANSITION.value,
    ]

    assert result_context.executed_steps == expected_steps
    assert result_context.status == LoopStatus.LOOP_COMPLETED

    # Verify that Event Logger recorded an event for each step
    logged_step_events = [
        e for e in logger.get_events(task_id="test_task_1")
        if e.event_type.value == "orchestrator.step"
    ]
    assert len(logged_step_events) == 11
    for idx, expected in enumerate(expected_steps):
        assert logged_step_events[idx].step_name == expected


def test_orchestrator_full_task_lifecycle():
    """Verify end-to-end task execution and state manager lifecycle transitions."""
    logger = EventLogger(console_output=False)
    state_manager = StateManager()
    orchestrator = AgentOrchestrator(logger=logger, state_manager=state_manager)

    result = orchestrator.execute_task(intent="Open browser and read page", task_id="task_lifecycle_1")

    assert result["success"] is True
    assert result["status"] == LoopStatus.LOOP_COMPLETED.value
    assert result["steps_count"] == 11

    # Verify state manager record
    task_state = state_manager.get_state("task_lifecycle_1")
    assert task_state is not None
    assert task_state.lifecycle == TaskLifecycle.COMPLETED
    assert task_state.last_verified_state is not None


def test_orchestrator_cancellation_halts_loop():
    """Verify cancellation at step 1 stops execution."""
    logger = EventLogger(console_output=False)
    state_manager = StateManager()
    state_manager.create_task("task_cancel")
    task_state = state_manager.get_state("task_cancel")
    task_state.is_cancelled = True

    orchestrator = AgentOrchestrator(logger=logger, state_manager=state_manager)
    result = orchestrator.execute_task(intent="Will be cancelled", task_id="task_cancel")

    assert result["success"] is False
    assert result["status"] == LoopStatus.CANCELLED.value
    assert result["steps_count"] == 1  # halted after step 1
