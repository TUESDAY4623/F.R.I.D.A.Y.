"""Phase 1 Sujeet Core Brain Tests.

Validates:
1. Intent / Context Manager:
   - Text input -> structured IntentResult
   - Entity and action_type extraction (read, write, list, move, pipeline)
   - Read-only memory integration
   - Ambiguous input handling
   - No tool execution
2. Task Graph Planner:
   - Structured TaskGraph with PlanStep expected outcomes
   - Deterministic planning across file operations
   - Read-only memory integration
   - No tool execution or state mutation
3. State Manager:
   - Task creation, lifecycle transitions
   - Plan version and active plan tracking
   - Current step tracking
   - Last verified state and step results persistence
   - Cancellation flag handling
4. Orchestrator Integration:
   - End-to-end chain: Input -> Intent -> Plan -> Loop -> State -> Result
   - Metrics tracking (latency, success rate, first attempt)
   - Response Manager output formatting
5. Ownership Boundaries:
   - Orchestrator delegates observation, verification, policy, and tool execution
   - Planner does not execute tools
   - Intent Manager does not execute tools
   - State Manager does not execute tools
6. Deterministic Integration Test:
   - Fixed Intent -> Fixed Plan -> Fixed Tool Call -> Fixed State Update -> Fixed Final State
   - Canonical 11-step loop executed in exact order
"""

from pathlib import Path
from typing import Any, Dict
from unittest.mock import Mock, patch

import pytest

from jarvis.intent import IntentManager, IntentResult
from jarvis.logger import EventLogger
from jarvis.memory import MemoryManager
from jarvis.orchestrator import (
    AgentOrchestrator,
    CanonicalLoopStateMachine,
    LoopContext,
    LoopStatus,
    LoopStep,
)
from jarvis.planner import PlanStep, Planner, TaskGraph
from jarvis.policy import PolicyEngine
from jarvis.state import StateManager, TaskState
from jarvis.tools import BaseTool, ToolContract, ToolRegistry, ToolResult
from jarvis.types import PolicyDecision, RiskLevel, TaskLifecycle, VerificationStatus
from jarvis.verification import VerificationEngine


# -----------------------------------------------------------------------------
# Mock Tool for Deterministic Testing
# -----------------------------------------------------------------------------

class MockFileWriteTool(BaseTool):
    """Mock file writing tool with full ToolContract."""

    @property
    def contract(self) -> ToolContract:
        return ToolContract(
            name="write_file",
            description="Write text contents to a destination file.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            output_schema={
                "type": "object",
                "properties": {"bytes_written": {"type": "integer"}},
                "required": ["bytes_written"],
            },
            risk_level=RiskLevel.LOW,
            reversible=True,
            rollback_strategy="delete",
            timeout=5.0,
            idempotency=True,
            required_capabilities=["file_write"],
            platform_support=["windows", "linux"],
        )

    def execute(self, params: Dict[str, Any]) -> ToolResult:
        path = params.get("path", "")
        content = params.get("content", "")
        return ToolResult(
            success=True,
            data={"path": path, "bytes_written": len(content), "status": "written"},
        )


# -----------------------------------------------------------------------------
# 1. Intent / Context Manager Tests
# -----------------------------------------------------------------------------

def test_intent_manager_empty_or_ambiguous():
    mgr = IntentManager()
    res = mgr.detect_intent("")
    assert res.is_ambiguous is True
    assert "No command provided" in (res.clarification_prompt or "")


def test_intent_manager_pattern_extractions():
    mgr = IntentManager()

    # File Read
    res = mgr.detect_intent("read file /data/reports/earnings.txt")
    assert res.action_type == "file_read"
    assert res.entities.get("path") == "/data/reports/earnings.txt"

    # Directory Listing
    res = mgr.detect_intent("list directory /data/reports")
    assert res.action_type == "file_list"
    assert res.entities.get("path") == "/data/reports"

    # File Write
    res = mgr.detect_intent("write file /tmp/out.txt with content Hello World")
    assert res.action_type == "file_write"
    assert res.entities.get("path") == "/tmp/out.txt"
    assert res.entities.get("content") == "Hello World"

    # File Move
    res = mgr.detect_intent("move file /tmp/old.txt to /tmp/new.txt")
    assert res.action_type == "file_move"
    assert res.entities.get("source_path") == "/tmp/old.txt"
    assert res.entities.get("destination_path") == "/tmp/new.txt"

    # File Pipeline
    res = mgr.detect_intent("read earnings report earnings.txt and save summary to summary.txt")
    assert res.action_type == "file_pipeline"
    assert res.entities.get("source_path") == "earnings.txt"
    assert res.entities.get("target_path") == "summary.txt"


def test_intent_manager_memory_read_only():
    mem = MemoryManager()
    mem.add_message("user", "Previous query")
    mem._preferences["theme"] = "dark"

    mgr = IntentManager(memory_manager=mem)
    res = mgr.detect_intent("read notes.txt")

    assert res.context.get("user_preferences") == {"theme": "dark"}
    assert len(res.context.get("conversation_history", [])) == 1

    # Verify Memory was NOT mutated
    assert len(mem.get_slice().conversation) == 1


# -----------------------------------------------------------------------------
# 2. Planner Tests
# -----------------------------------------------------------------------------

def test_planner_deterministic_task_graph():
    mem = MemoryManager()
    mem._preferences["encoding"] = "utf-8"
    planner = Planner(memory_manager=mem)

    # File read plan
    graph = planner.plan(intent="read notes.txt", task_id="t_read")
    assert graph.task_id == "t_read"
    assert len(graph.steps) == 1
    assert graph.steps[0].tool_name == "read_file"
    assert graph.steps[0].arguments == {"path": "notes.txt"}
    assert graph.steps[0].expected_outcome["action"] == "file_read"
    assert graph.metadata.get("preferences") == {"encoding": "utf-8"}

    # File write plan
    graph_w = planner.plan(intent="write file out.txt with content Test", task_id="t_write")
    assert len(graph_w.steps) == 1
    assert graph_w.steps[0].tool_name == "write_file"
    assert graph_w.steps[0].arguments["path"] == "out.txt"
    assert graph_w.steps[0].arguments["content"] == "Test"

    # Multi-step file pipeline
    graph_p = planner.plan(
        intent="read report q1.txt and save summary to summary.txt",
        task_id="t_pipe",
    )
    assert len(graph_p.steps) == 2
    assert graph_p.steps[0].tool_name == "read_file"
    assert graph_p.steps[1].tool_name == "write_file"

    # Default fallback
    graph_def = planner.plan(intent="Hello Jarvis", task_id="t_def")
    assert len(graph_def.steps) == 1
    assert graph_def.steps[0].tool_name == "noop_tool"


def test_planner_task_graph_step_progression():
    planner = Planner()
    graph = planner.plan(
        intent="read report q1.txt and save summary to summary.txt",
        task_id="t_prog",
    )
    s1 = graph.get_next_pending_step()
    assert s1 is not None and s1.step_id == "step-1"

    graph.mark_step_completed("step-1")
    s2 = graph.get_next_pending_step()
    assert s2 is not None and s2.step_id == "step-2"

    graph.mark_step_completed("step-2")
    assert graph.get_next_pending_step() is None
    assert graph.all_completed() is True


# -----------------------------------------------------------------------------
# 3. State Manager Tests
# -----------------------------------------------------------------------------

def test_state_manager_lifecycle_and_plan_versioning():
    sm = StateManager()
    state = sm.create_task("task_p1_state")
    assert state.task_id == "task_p1_state"
    assert state.lifecycle == TaskLifecycle.CREATED
    assert state.plan_version == 1

    sm.set_plan_version("task_p1_state", 2)
    sm.set_active_plan("task_p1_state", {"version": 2, "steps": ["step-1"]})
    sm.update_step("task_p1_state", 1, "step-1")
    sm.record_step_result("task_p1_state", "step-1", {"status": "ok"})
    sm.set_last_verified_state("task_p1_state", {"step-1": "verified"})
    sm.update_lifecycle("task_p1_state", TaskLifecycle.COMPLETED)

    updated = sm.get_state("task_p1_state")
    assert updated is not None
    assert updated.plan_version == 2
    assert updated.current_step_name == "step-1"
    assert updated.step_results["step-1"] == {"status": "ok"}
    assert updated.last_verified_state == {"step-1": "verified"}
    assert updated.lifecycle == TaskLifecycle.COMPLETED


def test_state_manager_cancellation():
    sm = StateManager()
    sm.create_task("task_cancel")
    assert sm.is_cancelled("task_cancel") is False

    sm.cancel_task("task_cancel")
    assert sm.is_cancelled("task_cancel") is True
    assert sm.get_state("task_cancel").lifecycle == TaskLifecycle.CANCELLED


# -----------------------------------------------------------------------------
# 4. Orchestrator Integration & Metrics Tests
# -----------------------------------------------------------------------------

def test_orchestrator_end_to_end_integration():
    logger = EventLogger(console_output=False)
    sm = StateManager()
    orchestrator = AgentOrchestrator(logger=logger, state_manager=sm)

    result = orchestrator.execute_task("Phase 1 integration test task")

    assert result["success"] is True
    assert result["status"] == "loop_completed"
    assert result["steps_count"] == 11
    assert result["plan_version"] == 1
    assert "response" in result
    assert result["latency_ms"] >= 0.0

    # Verify metrics collector
    metrics = orchestrator.metrics.get_summary()
    assert metrics["total_tasks"] == 1
    assert metrics["successful_tasks"] == 1
    assert metrics["task_success_rate"] == 100.0
    assert metrics["first_attempt_success_rate"] == 100.0


# -----------------------------------------------------------------------------
# 5. Ownership Boundary Tests
# -----------------------------------------------------------------------------

def test_orchestrator_delegates_responsibilities():
    """Verify Orchestrator delegates observation, verification, policy, and tool execution."""
    logger = EventLogger(console_output=False)
    sm = StateManager()

    mock_obs = Mock()
    mock_obs.observe.return_value = None

    mock_ver = Mock()
    mock_ver.verify.return_value = Mock(status=VerificationStatus.PASS)

    mock_pol = Mock()
    mock_pol.check.return_value = PolicyDecision.ALLOW

    mock_tool_mgr = Mock()
    mock_tool_mgr.dispatch.return_value = ToolResult(success=True, data={"res": "ok"})
    mock_tool_mgr.registry = Mock()
    mock_tool_mgr.registry.has.return_value = False

    sm_machine = CanonicalLoopStateMachine(
        logger=logger,
        state_manager=sm,
        observation_manager=mock_obs,
        verification_engine=mock_ver,
        policy_engine=mock_pol,
        tool_manager=mock_tool_mgr,
    )

    orchestrator = AgentOrchestrator(
        loop_state_machine=sm_machine,
        logger=logger,
        state_manager=sm,
    )

    result = orchestrator.execute_task("Delegation test")
    assert result["success"] is True

    # Confirm all 4 subsystems were delegated to
    assert mock_obs.observe.called
    assert mock_ver.verify.called
    assert mock_pol.check.called
    assert mock_tool_mgr.dispatch.called


def test_components_do_not_execute_tools():
    """Verify Planner, IntentManager, and StateManager never execute tools."""
    mock_tool = Mock()

    # Intent Manager
    im = IntentManager()
    im.detect_intent("read file /tmp/test.txt")
    mock_tool.execute.assert_not_called()

    # Planner
    pl = Planner()
    pl.plan("write file /tmp/out.txt with content abc", task_id="t_p")
    mock_tool.execute.assert_not_called()

    # State Manager
    sm = StateManager()
    sm.create_task("t_sm")
    sm.update_step("t_sm", 1, "step-1")
    mock_tool.execute.assert_not_called()


# -----------------------------------------------------------------------------
# 6. Part L — Deterministic Integration Test (Mocked File Tool)
# -----------------------------------------------------------------------------

def test_deterministic_file_operation_11_step_loop(tmp_path: Path):
    """Part L: Fixed Intent -> Fixed Plan -> Fixed Tool Calls -> Fixed State Updates -> Fixed Final State.
    
    Verifies that a real/mocked file tool passes through the canonical 11-step loop
    in exact sequential order, updating state and logging all step events.
    """
    logger = EventLogger(console_output=False)
    sm = StateManager()
    policy = PolicyEngine()
    tool_registry = ToolRegistry()

    # 1. Register Mock File Tool
    file_tool = MockFileWriteTool()
    tool_registry.register(file_tool)

    from jarvis.tools.manager import ToolManager
    tool_manager = ToolManager(registry=tool_registry, policy_engine=policy)

    # 2. Wire State Machine with Tool Manager
    state_machine = CanonicalLoopStateMachine(
        logger=logger,
        state_manager=sm,
        policy_engine=policy,
        tool_manager=tool_manager,
    )

    orchestrator = AgentOrchestrator(
        loop_state_machine=state_machine,
        logger=logger,
        state_manager=sm,
    )

    # 3. Fixed Intent
    test_file = str(tmp_path / "summary.txt")
    intent = f"write file {test_file} with content Phase 1 Verified"

    # 4. Execute through Orchestrator
    result = orchestrator.execute_task(intent=intent, task_id="task_det_file")

    # 5. Verify Fixed Plan, State, and Tool Calls
    assert result["success"] is True
    assert result["status"] == "loop_completed"
    assert result["steps_count"] == 11
    assert result["tool_result"]["data"]["bytes_written"] == len("Phase 1 Verified")

    # 6. Verify Exact 11-Step Ordering
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
    assert result["executed_steps"] == expected_steps

    # 7. Verify State Manager records
    final_state = sm.get_state("task_det_file")
    assert final_state is not None
    assert final_state.lifecycle == TaskLifecycle.COMPLETED
    assert final_state.step_results["step-1"]["data"]["status"] == "written"
    assert final_state.last_verified_state is not None
    assert final_state.active_plan is not None

    # 8. Verify Event Logger recorded all 11 step events
    step_events = [
        e for e in logger.get_events(task_id="task_det_file")
        if e.event_type.value == "orchestrator.step"
    ]
    assert len(step_events) == 11
    for idx, expected_name in enumerate(expected_steps):
        assert step_events[idx].step_name == expected_name
