"""Phase 1 Issue Resolution Verification Test Suite.

Verifies fixes for:
- Blocker 1: move_file tool registration and execution
- Blocker 2: IntentManager create_directory, move with spaces/quotes, write-to syntax
- Blocker 3: Planner schema harmonization (source/destination, create_directory)
- Blocker 4: Policy/Approval integration in ToolManager (Case A: rejected, Case B: allowed)
- Blocker 5: Honest failure propagation (no false success on error)
- Blocker 6: Default tool registry bootstrap
- Blocker 7: Tool lifecycle events & UI tree status transitions (RUNNING -> SUCCESS/FAILED)
- Full End-to-End: 5-tool filesystem pipeline through the 11-step canonical loop
"""

from pathlib import Path
from unittest.mock import Mock

import pytest

from jarvis.bootstrap import bootstrap_agent, register_default_tools
from jarvis.intent import IntentManager
from jarvis.logger import EventLogger, EventType
from jarvis.orchestrator import AgentOrchestrator
from jarvis.planner import Planner
from jarvis.tools import (
    CreateDirectoryTool,
    ListDirectoryTool,
    MoveFileTool,
    ReadFileTool,
    ToolManager,
    ToolRegistry,
    WriteFileTool,
    get_tool_registry,
)
from jarvis.types import ApprovalDecision, TaskLifecycle


# -----------------------------------------------------------------------------
# Blocker 1: move_file integration
# -----------------------------------------------------------------------------

def test_move_file_integration(tmp_path: Path):
    reg = ToolRegistry()
    reg.register(MoveFileTool())
    mgr = ToolManager(registry=reg)

    src = tmp_path / "origin.txt"
    dest = tmp_path / "relocated.txt"
    src.write_text("content to move", encoding="utf-8")

    # With approval (MEDIUM risk requires approval)
    res = mgr.dispatch(
        "move_file",
        {"source": str(src), "destination": str(dest)},
        approval_decision=ApprovalDecision.APPROVE,
    )
    assert res.success is True
    assert not src.exists()
    assert dest.exists()
    assert dest.read_text(encoding="utf-8") == "content to move"


# -----------------------------------------------------------------------------
# Blocker 2: IntentManager fixes
# -----------------------------------------------------------------------------

def test_intent_manager_create_directory_variations():
    im = IntentManager()

    # Variation 1: "Create a directory called test"
    res1 = im.detect_intent("Create a directory called test")
    assert res1.action_type == "create_directory"
    assert res1.entities.get("path") == "test"

    # Variation 2: "Create directory test"
    res2 = im.detect_intent("Create directory test")
    assert res2.action_type == "create_directory"
    assert res2.entities.get("path") == "test"

    # Variation 3: "Make a new folder called test"
    res3 = im.detect_intent("Make a new folder called test")
    assert res3.action_type == "create_directory"
    assert res3.entities.get("path") == "test"

    # Variation 4: Quoted folder name
    res4 = im.detect_intent('create folder "My Documents"')
    assert res4.action_type == "create_directory"
    assert res4.entities.get("path") == "My Documents"


def test_intent_manager_move_with_spaces_and_quotes():
    im = IntentManager()

    # Move with spaces in destination
    res1 = im.detect_intent("Move file A to directory B")
    assert res1.action_type == "file_move"
    assert res1.entities.get("source") == "A"
    assert res1.entities.get("destination") == "directory B"

    # Move with quotes
    res2 = im.detect_intent('Move file "A.txt" to "My Folder"')
    assert res2.action_type == "file_move"
    assert res2.entities.get("source") == "A.txt"
    assert res2.entities.get("destination") == "My Folder"

    # Simple move
    res3 = im.detect_intent("move file old.txt to new.txt")
    assert res3.action_type == "file_move"
    assert res3.entities.get("source") == "old.txt"
    assert res3.entities.get("destination") == "new.txt"

    # Invalid move without 'to'
    res_inv = im.detect_intent("move file old.txt")
    assert res_inv.action_type != "file_move"


def test_intent_manager_write_to_syntax():
    im = IntentManager()
    res = im.detect_intent('Write "Hello Jarvis" to test.txt')
    assert res.action_type == "file_write"
    assert res.entities.get("content") == "Hello Jarvis"
    assert res.entities.get("path") == "test.txt"


# -----------------------------------------------------------------------------
# Blocker 3: Planner schema harmonization
# -----------------------------------------------------------------------------

def test_planner_harmonized_schemas():
    planner = Planner()

    # create_directory planning
    graph_dir = planner.plan("Create directory new_dir", task_id="t_dir")
    assert len(graph_dir.steps) == 1
    assert graph_dir.steps[0].tool_name == "create_directory"
    assert graph_dir.steps[0].arguments == {"path": "new_dir"}

    # file_move planning (must use source and destination)
    graph_move = planner.plan('Move file "file.txt" to "folder/file.txt"', task_id="t_mv")
    assert len(graph_move.steps) == 1
    assert graph_move.steps[0].tool_name == "move_file"
    assert graph_move.steps[0].arguments == {"source": "file.txt", "destination": "folder/file.txt"}


# -----------------------------------------------------------------------------
# Blocker 4: Policy / Approval / ToolManager integration (Cases A & B)
# -----------------------------------------------------------------------------

def test_tool_manager_policy_approval_case_a_and_b(tmp_path: Path):
    reg = ToolRegistry()
    reg.register(WriteFileTool())
    mgr = ToolManager(registry=reg)
    target = str(tmp_path / "protected.txt")

    # Case A: MEDIUM risk without approval -> rejected
    res_a = mgr.dispatch(
        "write_file",
        {"path": target, "content": "data"},
        approval_decision=None,
    )
    assert res_a.success is False
    assert "requires approval" in res_a.error
    assert not Path(target).exists()

    # Case B: MEDIUM risk with approval -> execution allowed
    res_b = mgr.dispatch(
        "write_file",
        {"path": target, "content": "data"},
        approval_decision=ApprovalDecision.APPROVE,
    )
    assert res_b.success is True
    assert Path(target).read_text(encoding="utf-8") == "data"


# -----------------------------------------------------------------------------
# Blocker 5: Honest failure propagation (No false success)
# -----------------------------------------------------------------------------

def test_orchestrator_failure_propagation_nonexistent_file():
    logger = EventLogger(console_output=False)
    orch = AgentOrchestrator(logger=logger)

    res = orch.execute_task("Read non_existent_file_xyz_9999.txt")

    assert res["success"] is False
    assert res["status"] == "failed"
    assert res["tool_result"]["success"] is False

    # Verify no task.completed event was logged
    completed_events = [
        e for e in logger.get_events(task_id=res["task_id"])
        if e.event_type == EventType.TASK_COMPLETED
    ]
    assert len(completed_events) == 0

    # Verify task.failed event WAS logged
    failed_events = [
        e for e in logger.get_events(task_id=res["task_id"])
        if e.event_type == EventType.TASK_FAILED
    ]
    assert len(failed_events) == 1


def test_orchestrator_failure_propagation_missing_tool():
    empty_reg = ToolRegistry()
    empty_mgr = ToolManager(registry=empty_reg)
    logger = EventLogger(console_output=False)

    from jarvis.orchestrator.loop import CanonicalLoopStateMachine
    sm = CanonicalLoopStateMachine(logger=logger, tool_manager=empty_mgr)
    orch = AgentOrchestrator(loop_state_machine=sm, logger=logger)

    res = orch.execute_task("Read test.txt")
    assert res["success"] is False
    assert res["status"] == "failed"
    assert "not found in registry" in res["tool_result"]["error"]


# -----------------------------------------------------------------------------
# Blocker 6: Default tool registry bootstrap
# -----------------------------------------------------------------------------

def test_default_tool_registry_bootstrap():
    reg = ToolRegistry()
    register_default_tools(reg)

    assert reg.has("read_file")
    assert reg.has("write_file")
    assert reg.has("list_directory")
    assert reg.has("create_directory")
    assert reg.has("move_file")
    assert reg.has("noop_tool")

    # Verify get_tool_registry() singleton also contains them
    global_reg = get_tool_registry()
    assert global_reg.has("read_file")
    assert global_reg.has("write_file")
    assert global_reg.has("list_directory")
    assert global_reg.has("create_directory")
    assert global_reg.has("move_file")


# -----------------------------------------------------------------------------
# Blocker 7: Tool lifecycle events & UI tree status transitions
# -----------------------------------------------------------------------------

def test_ui_tool_lifecycle_events_running_success_failed():
    from jarvis.ui.main_window import MainWindow
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])

    window = MainWindow()

    # 1. Simulate tool.started event
    window._handle_tool_event({
        "type": "tool.started",
        "step_name": "6. Dispatch action",
        "message": "Dispatching write_file",
        "payload": {"tool_name": "write_file", "arguments": {"path": "a.txt"}},
    })

    assert window.tool_call_tree.topLevelItemCount() == 1
    item = window.tool_call_tree.topLevelItem(0)
    assert item.text(1) == "RUNNING"

    # 2. Simulate tool.completed event
    window._handle_tool_event({
        "type": "tool.completed",
        "step_name": "6. Dispatch action",
        "message": "Tool completed",
        "payload": {"tool_name": "write_file", "result": {"bytes_written": 10}},
    })
    assert item.text(1) == "SUCCESS"

    # 3. Simulate failure event for a second tool
    window._handle_tool_event({
        "type": "tool.started",
        "step_name": "6. Dispatch action",
        "message": "Dispatching read_file",
        "payload": {"tool_name": "read_file", "arguments": {"path": "b.txt"}},
    })
    assert window.tool_call_tree.topLevelItemCount() == 2
    item2 = window.tool_call_tree.topLevelItem(1)
    assert item2.text(1) == "RUNNING"

    window._handle_tool_event({
        "type": "tool.failed",
        "step_name": "6. Dispatch action",
        "message": "Tool failed",
        "payload": {"tool_name": "read_file", "error": "File not found"},
    })
    assert item2.text(1) == "FAILED"

    window.close()
    window.deleteLater()
    app.processEvents()


# -----------------------------------------------------------------------------
# Full End-to-End Filesystem Pipeline (All 5 tools through 11-step loop)
# -----------------------------------------------------------------------------

def test_phase1_full_filesystem_end_to_end(tmp_path: Path):
    """Executes all 5 Phase 1 filesystem tools sequentially through the full Orchestrator pipeline."""
    orch = AgentOrchestrator()

    # Step 1: Create directory
    target_dir = tmp_path / "sandbox"
    res_mkdir = orch.execute_task(f"Create a directory called {target_dir}")
    assert res_mkdir["success"] is True
    assert target_dir.is_dir()

    # Step 2: Write file
    file_path = target_dir / "document.txt"
    res_write = orch.execute_task(f'Write "Hello Jarvis Phase 1" to {file_path}')
    assert res_write["success"] is True
    assert file_path.is_file()
    assert file_path.read_text(encoding="utf-8") == "Hello Jarvis Phase 1"

    # Step 3: Read file
    res_read = orch.execute_task(f"Read file {file_path}")
    assert res_read["success"] is True
    assert res_read["tool_result"]["data"]["content"] == "Hello Jarvis Phase 1"

    # Step 4: List directory
    res_list = orch.execute_task(f"List directory {target_dir}")
    assert res_list["success"] is True
    assert "document.txt" in res_list["tool_result"]["data"]["entries"]

    # Step 5: Move file
    moved_path = tmp_path / "archived.txt"
    res_move = orch.execute_task(f"Move file {file_path} to {moved_path}")
    assert res_move["success"] is True
    assert moved_path.is_file()
    assert not file_path.exists()
    assert moved_path.read_text(encoding="utf-8") == "Hello Jarvis Phase 1"
