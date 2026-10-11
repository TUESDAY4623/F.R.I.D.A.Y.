"""Tests for Jarvis Desktop Agent Phase 2: Verification, Recovery, Retry, Replanning, and Approval."""

from datetime import datetime, timedelta, timezone
import os
import shutil
import tempfile
from typing import Any, Dict, Optional

import pytest

from jarvis.approval import ApprovalManager, ApprovalRequest, get_approval_manager
from jarvis.intent import IntentManager
from jarvis.logger import EventLogger, EventType
from jarvis.observation import Observation, ObservationManager
from jarvis.orchestrator import (
    AgentOrchestrator,
    CanonicalLoopStateMachine,
    LoopContext,
    LoopStatus,
    LoopStep,
)
from jarvis.planner import PlanStep, Planner, TaskGraph
from jarvis.policy import PolicyEngine
from jarvis.recovery import RecoveryAction, RecoveryManager
from jarvis.state import StateManager, TaskState
from jarvis.tools import ToolManager
from jarvis.tools.contract import ToolContract, ToolResult
from jarvis.tools.registry import ToolRegistry
from jarvis.types import (
    ApprovalDecision,
    ApprovalStatus,
    FailureClassification,
    PolicyDecision,
    RecoveryStrategy,
    RiskLevel,
    TaskLifecycle,
    VerificationStatus,
)
from jarvis.verification import VerificationEngine, VerificationResult


from jarvis.tools.contract import BaseTool


class FunctionalTool(BaseTool):
    def __init__(self, contract: ToolContract, fn):
        self._contract = contract
        self._fn = fn

    @property
    def contract(self) -> ToolContract:
        return self._contract

    def execute(self, arguments: Dict[str, Any]) -> ToolResult:
        return self._fn(arguments)


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp(prefix="jarvis_phase2_test_")
    yield d
    shutil.rmtree(d, ignore_errors=True)


# =====================================================================
# 1. Failure Classification Tests
# =====================================================================


def test_failure_classification_categories():
    """Verify that RecoveryManager accurately classifies all 5 canonical failure categories."""
    mgr = RecoveryManager()

    # RETRYABLE
    assert mgr.classify_failure("Request timed out after 5.0 seconds") == FailureClassification.RETRYABLE
    assert mgr.classify_failure("Resource temporarily unavailable (locked)") == FailureClassification.RETRYABLE
    assert mgr.classify_failure("Connection reset by peer; try again") == FailureClassification.RETRYABLE

    # FATAL (missing read file, missing tool, bad args)
    assert mgr.classify_failure("File not found", action_name="read_file") == FailureClassification.FATAL
    assert mgr.classify_failure("Tool 'fake_tool' not found in registry") == FailureClassification.FATAL
    assert mgr.classify_failure("Missing required argument: 'path'") == FailureClassification.FATAL

    # USER_ACTION_REQUIRED
    assert mgr.classify_failure("Action denied by user policy") == FailureClassification.USER_ACTION_REQUIRED
    assert mgr.classify_failure("Tool requires approval before execution") == FailureClassification.USER_ACTION_REQUIRED

    # REPLAN_REQUIRED
    assert mgr.classify_failure("Verification failed: discrepancy between observed and expected") == FailureClassification.REPLAN_REQUIRED


def test_failure_classification_missing_parent_is_recoverable(temp_dir):
    """Verify missing destination directory for move_file is classified as RECOVERABLE when source exists."""
    mgr = RecoveryManager()
    src_file = os.path.join(temp_dir, "source.txt")
    with open(src_file, "w", encoding="utf-8") as f:
        f.write("content")

    missing_dest_dir = os.path.join(temp_dir, "nested_folder")
    dest_file = os.path.join(missing_dest_dir, "dest.txt")

    classification = mgr.classify_failure(
        error="Destination directory does not exist",
        action_name="move_file",
        arguments={"source": src_file, "destination": dest_file},
    )
    assert classification == FailureClassification.RECOVERABLE


def test_failure_classification_missing_source_move_is_fatal(temp_dir):
    """Verify move_file where source does NOT exist is classified as FATAL."""
    mgr = RecoveryManager()
    src_file = os.path.join(temp_dir, "nonexistent_source.txt")
    dest_file = os.path.join(temp_dir, "dest.txt")

    classification = mgr.classify_failure(
        error="Source file does not exist",
        action_name="move_file",
        arguments={"source": src_file, "destination": dest_file},
    )
    assert classification == FailureClassification.FATAL


# =====================================================================
# 2. Retry Handling Tests
# =====================================================================


def test_retry_on_transient_failure_then_success():
    """Verify controlled retry on transient failure: succeeds on attempt 2, logs retry event."""
    logger = EventLogger(console_output=False)
    state_mgr = StateManager()

    # Tool that fails on attempt 1 with timeout, then succeeds on attempt 2
    attempts = {"count": 0}

    def flaky_exec(args: Dict[str, Any]) -> ToolResult:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return ToolResult(success=False, error="Tool 'flaky' timed out after 5.0 seconds")
        return ToolResult(success=True, data={"result": "recovered"})

    registry = ToolRegistry()
    registry.register(
        FunctionalTool(
            ToolContract(
                name="flaky_tool",
                description="Flaky tool for testing retries",
                risk_level=RiskLevel.LOW,
                reversible=True,
                rollback_strategy="none_needed",
                timeout=5.0,
                idempotency=True,
                input_schema={"type": "object", "properties": {"msg": {"type": "string"}}},
                output_schema={"type": "object"},
            ),
            flaky_exec,
        )
    )

    tool_mgr = ToolManager(registry=registry)
    planner = Planner()
    # Build plan using flaky_tool
    graph = TaskGraph(
        task_id="retry_task_1",
        intent="Run flaky tool",
        steps=[
            PlanStep(
                step_id="step-1",
                tool_name="flaky_tool",
                arguments={"msg": "hello"},
                expected_outcome={"status": "completed"},
                description="Call flaky tool",
            )
        ],
    )

    state_machine = CanonicalLoopStateMachine(
        logger=logger,
        state_manager=state_mgr,
        tool_manager=tool_mgr,
        planner=planner,
    )

    orchestrator = AgentOrchestrator(
        loop_state_machine=state_machine,
        logger=logger,
        state_manager=state_mgr,
        planner=planner,
    )

    # Pre-configure planner mock for this test
    planner.plan = lambda intent, task_id, context=None: graph  # type: ignore

    res = orchestrator.execute_task(intent="Run flaky tool", task_id="retry_task_1")

    assert res["success"] is True
    assert res["status"] == LoopStatus.LOOP_COMPLETED.value
    assert attempts["count"] == 2

    # Verify state retry count was incremented
    task_state = state_mgr.get_state("retry_task_1")
    assert task_state.retry_count == 1
    assert task_state.lifecycle == TaskLifecycle.COMPLETED

    # Verify structured retry event was emitted
    retry_events = [
        e for e in logger.get_events(task_id="retry_task_1")
        if e.event_type == EventType.TASK_RETRY
    ]
    assert len(retry_events) == 1
    assert "Retrying task retry_task_1" in retry_events[0].message


def test_retry_budget_exhaustion_terminates_in_failure():
    """Verify that exhausting the retry budget halts execution and transitions to FAILED."""
    logger = EventLogger(console_output=False)
    state_mgr = StateManager()

    # Tool that always times out
    def always_timeout_exec(args: Dict[str, Any]) -> ToolResult:
        return ToolResult(success=False, error="Tool timed out")

    registry = ToolRegistry()
    registry.register(
        FunctionalTool(
            ToolContract(
                name="timeout_tool",
                description="Always times out",
                risk_level=RiskLevel.LOW,
                reversible=True,
                rollback_strategy="none_needed",
                timeout=5.0,
                idempotency=True,
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
            always_timeout_exec,
        )
    )

    tool_mgr = ToolManager(registry=registry)
    recovery_mgr = RecoveryManager(max_retries=2)
    planner = Planner()
    graph = TaskGraph(
        task_id="budget_task",
        intent="Timeout test",
        steps=[
            PlanStep(
                step_id="step-1",
                tool_name="timeout_tool",
                arguments={},
                expected_outcome={"status": "completed"},
                description="Timeout step",
            )
        ],
    )
    planner.plan = lambda intent, task_id, context=None: graph  # type: ignore

    state_machine = CanonicalLoopStateMachine(
        logger=logger,
        state_manager=state_mgr,
        tool_manager=tool_mgr,
        planner=planner,
        recovery_manager=recovery_mgr,
    )

    orchestrator = AgentOrchestrator(
        loop_state_machine=state_machine,
        logger=logger,
        state_manager=state_mgr,
        planner=planner,
    )

    res = orchestrator.execute_task(intent="Timeout test", task_id="budget_task")

    assert res["success"] is False
    assert res["status"] == LoopStatus.FAILED.value

    task_state = state_mgr.get_state("budget_task")
    assert task_state.retry_count == 2
    assert task_state.lifecycle == TaskLifecycle.FAILED

    retry_events = [
        e for e in logger.get_events(task_id="budget_task")
        if e.event_type == EventType.TASK_RETRY
    ]
    assert len(retry_events) == 2


# =====================================================================
# 3. Recovery Handling Tests (Real Filesystem)
# =====================================================================


def test_auto_recovery_missing_destination_folder_move_file(temp_dir):
    """End-to-end real filesystem test: move_file to missing folder auto-recovers by creating directory."""
    from jarvis.bootstrap import register_default_tools

    # Create source file
    src_file = os.path.join(temp_dir, "my_document.txt")
    with open(src_file, "w", encoding="utf-8") as f:
        f.write("Important Report Data")

    # Destination folder does NOT exist yet
    dest_dir = os.path.join(temp_dir, "recovered_archive")
    dest_file = os.path.join(dest_dir, "my_document.txt")
    assert not os.path.exists(dest_dir)

    logger = EventLogger(console_output=False)
    state_mgr = StateManager()
    registry = register_default_tools(ToolRegistry())
    tool_mgr = ToolManager(registry=registry)
    recovery_mgr = RecoveryManager(max_recovery_attempts=2)
    planner = Planner()

    state_machine = CanonicalLoopStateMachine(
        logger=logger,
        state_manager=state_mgr,
        tool_manager=tool_mgr,
        planner=planner,
        recovery_manager=recovery_mgr,
    )

    orchestrator = AgentOrchestrator(
        loop_state_machine=state_machine,
        logger=logger,
        state_manager=state_mgr,
        planner=planner,
    )

    intent = f'move file from "{src_file}" to "{dest_file}"'
    res = orchestrator.execute_task(intent=intent, task_id="recovery_move_1")

    assert res["success"] is True
    assert res["status"] == LoopStatus.LOOP_COMPLETED.value

    # Verify filesystem outcome: directory was created and file was moved!
    assert os.path.exists(dest_dir)
    assert os.path.exists(dest_file)
    assert not os.path.exists(src_file)

    with open(dest_file, "r", encoding="utf-8") as f:
        assert f.read() == "Important Report Data"

    # Verify recovery state and events
    task_state = state_mgr.get_state("recovery_move_1")
    assert task_state.recovery_attempts == 1
    assert task_state.lifecycle == TaskLifecycle.COMPLETED

    rec_started_events = [
        e for e in logger.get_events(task_id="recovery_move_1")
        if e.event_type == EventType.TASK_RECOVERY_STARTED
    ]
    assert len(rec_started_events) == 1
    assert "Recovery started" in rec_started_events[0].message

    rec_completed_events = [
        e for e in logger.get_events(task_id="recovery_move_1")
        if e.event_type == EventType.TASK_RECOVERY_COMPLETED
    ]
    assert len(rec_completed_events) == 1
    assert "recovered and completed successfully" in rec_completed_events[0].message


def test_auto_recovery_missing_parent_folder_write_file(temp_dir):
    """End-to-end real filesystem test: write_file to missing nested directory auto-recovers."""
    from jarvis.bootstrap import register_default_tools

    nested_dir = os.path.join(temp_dir, "nested_docs")
    target_file = os.path.join(nested_dir, "note.txt")
    assert not os.path.exists(nested_dir)

    logger = EventLogger(console_output=False)
    state_mgr = StateManager()
    registry = register_default_tools(ToolRegistry())
    tool_mgr = ToolManager(registry=registry)
    planner = Planner()

    state_machine = CanonicalLoopStateMachine(
        logger=logger,
        state_manager=state_mgr,
        tool_manager=tool_mgr,
        planner=planner,
    )

    orchestrator = AgentOrchestrator(
        loop_state_machine=state_machine,
        logger=logger,
        state_manager=state_mgr,
        planner=planner,
    )

    intent = f'write "hello world" to "{target_file}"'
    res = orchestrator.execute_task(intent=intent, task_id="recovery_write_1")

    assert res["success"] is True
    assert res["status"] == LoopStatus.LOOP_COMPLETED.value
    assert os.path.exists(target_file)
    with open(target_file, "r", encoding="utf-8") as f:
        assert f.read() == "hello world"


# =====================================================================
# 4. Replanning Capabilities Tests
# =====================================================================


def test_replanning_on_verification_failure():
    """Verify Planner generates revised TaskGraph with incremented plan_version and archives previous plan."""
    logger = EventLogger(console_output=False)
    state_mgr = StateManager()

    # Custom verification engine that fails plan v1, but passes plan v2
    class DiscrepancyVerificationEngine(VerificationEngine):
        def verify(self, expected_outcome: Dict[str, Any], observation: Observation) -> VerificationResult:
            if observation.state.get("plan_version", 1) == 1:
                return VerificationResult(
                    status=VerificationStatus.FAIL,
                    reason="Verification discrepancy in plan v1 output",
                )
            return VerificationResult(
                status=VerificationStatus.PASS,
                reason="Verification matches in plan v2",
            )

    call_count = {"count": 0}

    def tracking_exec(args: Dict[str, Any]) -> ToolResult:
        call_count["count"] += 1
        return ToolResult(success=True, data={"attempt": call_count["count"]})

    registry = ToolRegistry()
    registry.register(
        FunctionalTool(
            ToolContract(
                name="test_tool",
                description="Testing replan",
                risk_level=RiskLevel.LOW,
                reversible=True,
                rollback_strategy="none_needed",
                timeout=5.0,
                idempotency=True,
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
            tracking_exec,
        )
    )

    tool_mgr = ToolManager(registry=registry)
    planner = Planner()
    recovery_mgr = RecoveryManager(max_replans=2)
    verif_engine = DiscrepancyVerificationEngine()

    state_machine = CanonicalLoopStateMachine(
        logger=logger,
        state_manager=state_mgr,
        tool_manager=tool_mgr,
        planner=planner,
        verification_engine=verif_engine,
        recovery_manager=recovery_mgr,
    )

    # Attach current plan_version to observation
    orig_observe = state_machine.observation_manager.observe

    def observe_with_version(target="post_action_state", skip_if_cached=False):
        obs = orig_observe(target=target, skip_if_cached=skip_if_cached)
        st = state_mgr.get_state("replan_task_1")
        obs.state["plan_version"] = st.plan_version if st else 1
        return obs

    state_machine.observation_manager.observe = observe_with_version  # type: ignore

    orchestrator = AgentOrchestrator(
        loop_state_machine=state_machine,
        logger=logger,
        state_manager=state_mgr,
        planner=planner,
    )

    # Initial plan v1
    initial_graph = TaskGraph(
        task_id="replan_task_1",
        intent="Replan test",
        steps=[
            PlanStep(
                step_id="step-1",
                tool_name="test_tool",
                arguments={},
                expected_outcome={"status": "completed"},
                description="Step v1",
            )
        ],
        version=1,
    )
    planner.plan = lambda intent, task_id, context=None: initial_graph  # type: ignore

    res = orchestrator.execute_task(intent="Replan test", task_id="replan_task_1")

    assert res["success"] is True
    assert res["status"] == LoopStatus.LOOP_COMPLETED.value
    assert res["plan_version"] == 2

    task_state = state_mgr.get_state("replan_task_1")
    assert task_state.replan_count == 1
    assert task_state.plan_version == 2
    assert len(task_state.previous_plans) == 1
    assert task_state.previous_plans[0]["version"] == 1

    # Verify task.replan event
    replan_events = [
        e for e in logger.get_events(task_id="replan_task_1")
        if e.event_type == EventType.TASK_REPLAN
    ]
    assert len(replan_events) == 1
    assert "Replanning task replan_task_1" in replan_events[0].message


# =====================================================================
# 5. Approval Lifecycle Tests
# =====================================================================


def test_approval_lifecycle_approved():
    """Verify Approval flow: Policy CONFIRM -> Approval APPROVE -> Tool executed successfully."""
    logger = EventLogger(console_output=False)
    state_mgr = StateManager()

    executed = {"flag": False}

    def confirmed_exec(args: Dict[str, Any]) -> ToolResult:
        executed["flag"] = True
        return ToolResult(success=True, data={"done": True})

    registry = ToolRegistry()
    registry.register(
        FunctionalTool(
            ToolContract(
                name="medium_risk_tool",
                description="Action requiring approval",
                risk_level=RiskLevel.MEDIUM,
                reversible=True,
                rollback_strategy="rollback_action",
                timeout=5.0,
                idempotency=False,
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
            confirmed_exec,
        )
    )

    policy_engine = PolicyEngine()
    approval_mgr = ApprovalManager()
    approval_mgr.set_default_decision(ApprovalDecision.APPROVE)

    tool_mgr = ToolManager(registry=registry, policy_engine=policy_engine)
    planner = Planner()
    graph = TaskGraph(
        task_id="approval_approved_task",
        intent="Execute medium risk action",
        steps=[
            PlanStep(
                step_id="step-1",
                tool_name="medium_risk_tool",
                arguments={},
                expected_outcome={"status": "completed"},
                description="Medium risk step",
            )
        ],
    )
    planner.plan = lambda intent, task_id, context=None: graph  # type: ignore

    state_machine = CanonicalLoopStateMachine(
        logger=logger,
        state_manager=state_mgr,
        tool_manager=tool_mgr,
        policy_engine=policy_engine,
        approval_manager=approval_mgr,
        planner=planner,
    )

    orchestrator = AgentOrchestrator(
        loop_state_machine=state_machine,
        logger=logger,
        state_manager=state_mgr,
        planner=planner,
    )

    res = orchestrator.execute_task(intent="Execute high risk action", task_id="approval_approved_task")

    assert res["success"] is True
    assert executed["flag"] is True

    task_state = state_mgr.get_state("approval_approved_task")
    assert task_state.approval_status == ApprovalStatus.APPROVED

    pending_events = [
        e for e in logger.get_events(task_id="approval_approved_task")
        if e.event_type == EventType.TASK_APPROVAL_PENDING
    ]
    assert len(pending_events) == 1

    approved_events = [
        e for e in logger.get_events(task_id="approval_approved_task")
        if e.event_type == EventType.TASK_APPROVAL_APPROVED
    ]
    assert len(approved_events) == 1


def test_approval_lifecycle_denied():
    """Verify Approval flow: Policy CONFIRM -> Approval DENY -> Tool NOT executed, Task FAILED."""
    logger = EventLogger(console_output=False)
    state_mgr = StateManager()

    executed = {"flag": False}

    def confirmed_exec(args: Dict[str, Any]) -> ToolResult:
        executed["flag"] = True
        return ToolResult(success=True, data={"done": True})

    registry = ToolRegistry()
    registry.register(
        FunctionalTool(
            ToolContract(
                name="medium_risk_tool_2",
                description="Action requiring approval",
                risk_level=RiskLevel.MEDIUM,
                reversible=True,
                rollback_strategy="rollback_action",
                timeout=5.0,
                idempotency=False,
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
            confirmed_exec,
        )
    )

    policy_engine = PolicyEngine()
    approval_mgr = ApprovalManager()
    approval_mgr.set_default_decision(ApprovalDecision.DENY)

    tool_mgr = ToolManager(registry=registry, policy_engine=policy_engine)
    planner = Planner()
    graph = TaskGraph(
        task_id="approval_denied_task",
        intent="Execute dangerous action",
        steps=[
            PlanStep(
                step_id="step-1",
                tool_name="medium_risk_tool_2",
                arguments={},
                expected_outcome={"status": "completed"},
                description="Medium risk step",
            )
        ],
    )
    planner.plan = lambda intent, task_id, context=None: graph  # type: ignore

    state_machine = CanonicalLoopStateMachine(
        logger=logger,
        state_manager=state_mgr,
        tool_manager=tool_mgr,
        policy_engine=policy_engine,
        approval_manager=approval_mgr,
        planner=planner,
    )

    orchestrator = AgentOrchestrator(
        loop_state_machine=state_machine,
        logger=logger,
        state_manager=state_mgr,
        planner=planner,
    )

    res = orchestrator.execute_task(intent="Execute dangerous action", task_id="approval_denied_task")

    assert res["success"] is False
    assert executed["flag"] is False
    assert res["status"] == LoopStatus.FAILED.value

    task_state = state_mgr.get_state("approval_denied_task")
    assert task_state.approval_status == ApprovalStatus.DENIED
    assert task_state.lifecycle == TaskLifecycle.FAILED

    denied_events = [
        e for e in logger.get_events(task_id="approval_denied_task")
        if e.event_type == EventType.TASK_APPROVAL_DENIED
    ]
    assert len(denied_events) == 1


def test_approval_lifecycle_cancelled():
    """Verify Approval flow: Policy CONFIRM -> Approval CANCEL -> Task CANCELLED."""
    logger = EventLogger(console_output=False)
    state_mgr = StateManager()

    registry = ToolRegistry()
    registry.register(
        FunctionalTool(
            ToolContract(
                name="medium_risk_tool_3",
                description="Action requiring approval",
                risk_level=RiskLevel.MEDIUM,
                reversible=True,
                rollback_strategy="rollback_action",
                timeout=5.0,
                idempotency=False,
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
            lambda args: ToolResult(success=True, data={}),
        )
    )

    policy_engine = PolicyEngine()
    approval_mgr = ApprovalManager()
    approval_mgr.set_default_decision(ApprovalDecision.CANCEL)

    tool_mgr = ToolManager(registry=registry, policy_engine=policy_engine)
    planner = Planner()
    graph = TaskGraph(
        task_id="approval_cancel_task",
        intent="Action will be cancelled by user",
        steps=[
            PlanStep(
                step_id="step-1",
                tool_name="medium_risk_tool_3",
                arguments={},
                expected_outcome={"status": "completed"},
                description="Medium risk step",
            )
        ],
    )
    planner.plan = lambda intent, task_id, context=None: graph  # type: ignore

    state_machine = CanonicalLoopStateMachine(
        logger=logger,
        state_manager=state_mgr,
        tool_manager=tool_mgr,
        policy_engine=policy_engine,
        approval_manager=approval_mgr,
        planner=planner,
    )

    orchestrator = AgentOrchestrator(
        loop_state_machine=state_machine,
        logger=logger,
        state_manager=state_mgr,
        planner=planner,
    )

    res = orchestrator.execute_task(intent="Cancel test", task_id="approval_cancel_task")

    assert res["success"] is False
    assert res["status"] == LoopStatus.CANCELLED.value

    task_state = state_mgr.get_state("approval_cancel_task")
    assert task_state.approval_status == ApprovalStatus.CANCELLED
    assert task_state.lifecycle == TaskLifecycle.CANCELLED


# =====================================================================
# 6. Cancellation and Deadline at Step 1
# =====================================================================


def test_deadline_expired_halts_at_step_1():
    """Verify that an expired deadline causes step 1 to immediately halt and emit TASK_TIMEOUT."""
    logger = EventLogger(console_output=False)
    state_mgr = StateManager()

    # Create task with a deadline in the past
    past_deadline = datetime.now(timezone.utc) - timedelta(minutes=5)
    state_mgr.create_task("timeout_task_1", deadline=past_deadline)

    orchestrator = AgentOrchestrator(logger=logger, state_manager=state_mgr)
    res = orchestrator.execute_task(intent="Test deadline timeout", task_id="timeout_task_1")

    assert res["success"] is False
    assert res["status"] == LoopStatus.FAILED.value
    assert res["steps_count"] == 1  # Halts immediately at Step 1
    assert res["executed_steps"] == [LoopStep.STEP_1_CHECK_CANCELLATION.value]

    timeout_events = [
        e for e in logger.get_events(task_id="timeout_task_1")
        if e.event_type == EventType.TASK_TIMEOUT
    ]
    assert len(timeout_events) == 1
    assert "timed out / deadline exceeded at Step 1" in timeout_events[0].message
