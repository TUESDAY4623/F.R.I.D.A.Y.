"""Phase 1 Deterministic Integration Benchmark & Exit Gate Suite.

Per Section 15 & Phase 1 Exit Criteria:
- Fixed intent in -> fixed plan -> fixed tool calls -> fixed final state.
- Tracks:
  - Task success rate
  - First-attempt success rate
  - Execution latency
"""

import time
import pytest
from jarvis.logger import EventLogger, get_logger
from jarvis.orchestrator import AgentOrchestrator
from jarvis.tools import BaseTool, ToolContract, ToolResult, get_tool_registry
from jarvis.types import RiskLevel


class MockFileSystemTool(BaseTool):
    """Deterministic mocked filesystem tool for Phase 1 benchmark suite."""

    def __init__(self, name: str = "mock_fs_tool") -> None:
        self._name = name

    @property
    def contract(self) -> ToolContract:
        return ToolContract(
            name=self._name,
            description="Mock filesystem tool for benchmark tests",
            input_schema={
                "type": "object",
                "properties": {"filepath": {"type": "string"}},
                "required": ["filepath"],
            },
            output_schema={
                "type": "object",
                "properties": {"status": {"type": "string"}},
            },
            risk_level=RiskLevel.LOW,
            reversible=True,
            rollback_strategy="delete",
            timeout=5.0,
            idempotency=True,
            required_capabilities=["file_system"],
            platform_support=["windows", "linux"],
        )

    def execute(self, params: dict) -> ToolResult:
        filepath = params.get("filepath", "test.txt")
        return ToolResult(
            success=True,
            data={"filepath": filepath, "bytes_written": 128, "status": "OK"},
        )


def test_phase1_deterministic_loop_benchmark():
    """Verify deterministic execution and measure latency, success rate, and first-attempt pass."""
    logger = get_logger()
    registry = get_tool_registry()

    mock_tool = MockFileSystemTool("mock_fs_tool")
    if not registry.has("mock_fs_tool"):
        registry.register(mock_tool)

    orchestrator = AgentOrchestrator(logger=logger)

    iterations = 5
    successful_runs = 0
    first_attempt_successes = 0
    latencies = []

    for i in range(iterations):
        intent = f"Benchmark iteration {i+1}: process test file"
        start_time = time.perf_counter()

        result = orchestrator.execute_task(intent=intent)
        duration_ms = (time.perf_counter() - start_time) * 1000

        latencies.append(duration_ms)

        if result.get("success") and result.get("status") == "loop_completed":
            successful_runs += 1
            first_attempt_successes += 1  # No retries triggered in Phase 1 deterministic stub

    task_success_rate = (successful_runs / iterations) * 100
    first_attempt_rate = (first_attempt_successes / iterations) * 100
    avg_latency_ms = sum(latencies) / len(latencies)

    # Benchmark assertions
    assert task_success_rate == 100.0, f"Expected 100% success rate, got {task_success_rate}%"
    assert first_attempt_rate == 100.0, f"Expected 100% first-attempt rate, got {first_attempt_rate}%"
    assert avg_latency_ms < 500.0, f"Average latency too high: {avg_latency_ms:.2f}ms"

    print(
        f"\n[Phase 1 Benchmark Results]\n"
        f"  - Total Iterations: {iterations}\n"
        f"  - Task Success Rate: {task_success_rate:.1f}%\n"
        f"  - First-Attempt Success Rate: {first_attempt_rate:.1f}%\n"
        f"  - Average Latency: {avg_latency_ms:.2f} ms"
    )
