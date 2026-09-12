"""Main entry point for Jarvis Desktop Agent Phase 0 Hello Loop.

Demonstrates:
1. Modular monolith structure with single process and strict module boundaries.
2. Tool Registry contract verification.
3. Event Logger live stream subscription.
4. Orchestrator's 11-step canonical loop execution with explicit state machine steps.
"""

import sys
from jarvis.logger import EventLogger, LogEvent, get_logger
from jarvis.orchestrator import AgentOrchestrator
from jarvis.tools import BaseTool, ToolContract, ToolResult, get_tool_registry
from jarvis.types import RiskLevel


class HelloProbeTool(BaseTool):
    """A minimal throwaway tool implementing the Section 11 Tool Registry contract."""

    @property
    def contract(self) -> ToolContract:
        return ToolContract(
            name="hello_probe",
            description="Phase 0 probe tool verifying contract compliance",
            input_schema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
            },
            output_schema={
                "type": "object",
                "properties": {"echo": {"type": "string"}},
            },
            risk_level=RiskLevel.LOW,
            reversible=True,
            rollback_strategy="none_needed",
            timeout=5.0,
            idempotency=True,
            required_capabilities=["basic_execution"],
            platform_support=["windows"],
        )

    def execute(self, params: dict) -> ToolResult:
        msg = params.get("message", "hello")
        return ToolResult(success=True, data={"echo": msg})


def main() -> int:
    print("=" * 70)
    print(" Jarvis Desktop Agent — Phase 0 Hello Loop")
    print(" Modular Monolith Initialized (Single Process, Strict Boundaries)")
    print("=" * 70)

    # 1. Wire Event Logger (First real component per Section 13 & Phase 0)
    logger = get_logger()

    # Demonstrate live subscriber (how Tanmay's raw log pane will stream events)
    streamed_events = []

    def ui_stream_subscriber(event: LogEvent) -> None:
        streamed_events.append(event)

    logger.add_subscriber(ui_stream_subscriber)

    # 2. Register sample tool verifying Tool Registry contract (Section 11)
    registry = get_tool_registry()
    probe_tool = HelloProbeTool()
    contract = registry.register(probe_tool)
    print(f"\n[Tool Registry] Successfully registered tool: '{contract.name}'")
    print(f"  - Risk Level: {contract.risk_level.value}")
    print(f"  - Reversible: {contract.reversible} (strategy: {contract.rollback_strategy})")
    print(f"  - Timeout: {contract.timeout}s | Idempotency: {contract.idempotency}")
    print(f"  - Platform: {contract.platform_support}")

    # 3. Execute Orchestrator's 11-step canonical execution loop
    print("\n[Orchestrator] Starting 11-step canonical loop execution...")
    orchestrator = AgentOrchestrator(logger=logger)
    result = orchestrator.execute_task("Phase 0 verification: Run hello loop")

    print(f"\n[Result] Status: {result['status']}, Steps Executed: {result['steps_count']}")
    print("-" * 70)
    print("Executed steps in sequence:")
    for idx, step_name in enumerate(result["executed_steps"], start=1):
        print(f"  {step_name}")
    print("-" * 70)

    # 4. Verify Event Logger captured all events
    logged_steps = [
        e for e in streamed_events if e.event_type.value == "orchestrator.step"
    ]
    print(f"\n[Event Logger] Total streamed events captured: {len(streamed_events)}")
    print(f"[Event Logger] Step events recorded: {len(logged_steps)}/11")

    assert result["steps_count"] == 11, f"Expected 11 steps, got {result['steps_count']}"
    assert len(logged_steps) == 11, f"Expected 11 logged steps, got {len(logged_steps)}"

    print("\n[SUCCESS] Phase 0 Hello Loop completed cleanly across all 11 steps!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
