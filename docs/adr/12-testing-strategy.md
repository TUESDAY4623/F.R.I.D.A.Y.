# Testing Strategy

## Overview

Every major component must have tests. The agentic core must be testable without real external applications. This document defines the test categories, structure, and approach.

## Test Categories

### Unit Tests

**Purpose:** Verify that a single component behaves correctly in isolation.

**Scope:** Each component (Input Processor, Intent Manager, Laya, Task Profiler, Planner, Agent State, Decision Engine, Agent Orchestrator).

**Approach:**
- Components are tested with mocked dependencies.
- Each public method/function has at least one test.
- Edge cases and error paths are tested.
- LLM-dependent components (Laya, Task Profiler, Decision Engine) are tested with deterministic mock LLM responses.

### Contract Tests

**Purpose:** Verify that data contracts (schemas) are correctly defined and that components validate against them.

**Scope:** All data contracts defined in ADR 04.

**Approach:**
- Each schema has a test that validates known-good and known-bad instances.
- Schema validation is tested at each component boundary.
- Schema evolution (adding optional fields) is tested for backward compatibility.

### Integration Tests

**Purpose:** Verify that components work correctly together.

**Scope:** Adjacent component pairs (e.g., Input Processor → Intent Manager, Intent Manager → Laya, Planner → Agent State).

**Approach:**
- Components are wired together with minimal mocking (real implementations with mock external dependencies like LLM).
- Data flows are tested end-to-end within the pipeline.
- Error propagation between components is tested.

### Agent-Loop Tests

**Purpose:** Verify the full agentic control loop with mock tools.

**Scope:** The Orchestrator driving a complete task execution from start to terminal state.

**Approach:**
- The Orchestrator runs with all upstream components (Input Processor through Decision Engine) using real implementations with mock LLM.
- Downstream tools are deterministic mocks.
- The full loop (OBSERVE → DECIDE → ACT → OBSERVE RESULT → VERIFY → UPDATE STATE) is tested.
- Multiple scenarios: simple success, retry, replan, ASK_USER, FAIL.

### Failure/Recovery Tests

**Purpose:** Verify that the system handles failures and recovers correctly.

**Scope:** All error recovery paths defined in ADR 11.

**Approach:**
- Mock tools are configured to simulate failures.
- Retry logic is tested (success on retry, retry exhaustion).
- Replan logic is tested (successful replan, replan exhaustion).
- ASK_USER scenarios are tested (user provides input, user declines, timeout).
- WAIT scenarios are tested (condition met, timeout).
- Policy denials are tested.
- Loop detection is tested.

## Test Structure

```
tests/
├── unit/
│   ├── input_processor/
│   │   └── test_input_processor.py
│   ├── intent_manager/
│   │   └── test_intent_manager.py
│   ├── laya/
│   │   └── test_laya.py
│   ├── task_profiler/
│   │   └── test_task_profiler.py
│   ├── planner/
│   │   └── test_planner.py
│   ├── agent_state/
│   │   └── test_agent_state.py
│   ├── decision_engine/
│   │   └── test_decision_engine.py
│   └── agent_orchestrator/
│       └── test_agent_orchestrator.py
├── contract/
│   ├── test_request_schema.py
│   ├── test_intent_schema.py
│   ├── test_laya_classification_schema.py
│   ├── test_task_profile_schema.py
│   ├── test_task_graph_schema.py
│   ├── test_decision_schema.py
│   └── test_agent_state_schema.py
├── integration/
│   ├── test_pipeline.py              # Input Processor → Orchestrator
│   ├── test_intent_to_profile.py     # Laya → Intent Manager → Task Profiler
│   └── test_planner_to_state.py      # Planner → Agent State initialization
├── agent_loop/
│   ├── test_simple_execution.py      # Full loop with simple task
│   ├── test_retry_loop.py            # Retry path through full loop
│   ├── test_replan_loop.py           # Replan path through full loop
│   ├── test_ask_user_loop.py         # ASK_USER path through full loop
│   ├── test_completion.py            # Successful COMPLETE
│   └── test_failure.py               # FAIL path
├── failure_recovery/
│   ├── test_retry_exhaustion.py
│   ├── test_replan_exhaustion.py
│   ├── test_policy_denial.py
│   ├── test_loop_detection.py
│   └── test_wait_timeout.py
├── fixtures/
│   ├── mock_llm.py                   # Deterministic mock LLM
│   ├── mock_tools.py                 # Deterministic mock tools
│   ├── mock_policy_engine.py         # Mock Policy Engine
│   ├── sample_requests.py            # Sample Request objects
│   ├── sample_decisions.py           # Sample Decision objects
│   └── sample_task_graphs.py         # Sample Task Graph objects
└── conftest.py                       # Shared test configuration
```

## Mocking Strategy

### Mock LLM

The Decision Engine depends on an LLM provider. For testing:
- A mock LLM returns pre-configured responses based on the input AgentState.
- Responses are structured as valid Decisions that conform to the Decision schema.
- Different scenarios are configured by setting up the mock LLM's response mapping.

### Mock Tools

All downstream tools are mocked:
- Mock tools return deterministic, configurable results.
- Mock tools record all invocations for test assertions.
- Mock tools can be configured to simulate failures (by error type, frequency, etc.).
- Mock tools have no side effects.

### Mock Policy Engine

The mock Policy Engine:
- Returns configurable approval/denial results.
- Can be configured per test scenario.
- Default behavior approves all actions unless explicitly configured to deny.

## Test Execution

- Unit tests: run on every code change.
- Contract tests: run on every schema change.
- Integration tests: run on every component change.
- Agent-loop tests: run on every Orchestrator change.
- Failure/recovery tests: run on every error-handling change.

All tests must pass before a phase is considered complete.

## Constraints

1. No real external applications (browsers, file systems, OS APIs) are used in tests.
2. LLM calls are always mocked in tests.
3. Tests must be deterministic — no flaky tests.
4. Test fixtures must be independent — no shared mutable state between tests.
5. Every component must have at least one unit test before implementation is considered complete.
