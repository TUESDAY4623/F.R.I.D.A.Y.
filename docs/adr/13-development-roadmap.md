# Development Roadmap

## Phase Overview

Development proceeds through eight sequential phases. Each phase has explicit entry criteria, deliverables, and exit criteria. No phase may be skipped without explicit approval.

## Phase 0: Project Specification and Repository Foundation

**Status: Current phase.**

**Objective:** Establish the project specification, architecture documentation, repository structure, contracts, development rules, and testing strategy before implementing the agentic core.

**Deliverables:**
- CLAUDE.md — project instructions and constraints
- docs/adr/ — 14 populated architecture decision records
- schemas/ — directory structure for JSON Schema definitions
- Repository structure conventions
- Development tooling setup (build system, linter, test runner)

**Exit Criteria:**
- All 14 ADR documents are populated and internally consistent.
- Component responsibilities are clearly defined with no overlap.
- Data contracts are specified.
- The Agent Orchestrator is identified as the current implementation boundary.
- All architectural ambiguities are documented as unresolved decisions.
- Repository structure is agreed upon.

## Phase 1: Core Contracts and Schemas

**Objective:** Implement the data contract schemas and validation infrastructure.

**Entry Criteria:** Phase 0 is complete. All ADR documents are approved.

**Deliverables:**
- JSON Schema definitions for all contracts (Request, Intent, LayaClassification, TaskProfile, TaskGraph, TaskGraphNode, TaskGraphEdge, Decision, AgentState, ExecutionStep, Observation, VerificationResult, ErrorRecord, ToolResult, ProposedAction, PolicyResult).
- Schema validation library integration.
- Validation tests for all schemas (contract tests).
- `schemas/` directory populated with schema files.

**Depends on:** Phase 0.

## Phase 2: Input Processor and Intent Layer

**Objective:** Implement the entry point of the pipeline.

**Entry Criteria:** Phase 1 is complete. Schemas are validated.

**Deliverables:**
- Input Processor implementation.
- Intent Manager implementation.
- Laya classification implementation.
- Unit tests for all three components.
- Integration tests for the pipeline segment (Input Processor → Intent Manager → Laya).
- Mock LLM integration for Laya and Intent Manager.

**Depends on:** Phase 1.

## Phase 3: Task Profiler and Planner

**Objective:** Implement task analysis and planning.

**Entry Criteria:** Phase 2 is complete. Intent layer produces valid outputs.

**Deliverables:**
- Task Profiler implementation.
- Planner implementation.
- Task Graph data structure (constructible, traversable, revisable).
- Unit tests for Task Profiler and Planner.
- Integration tests for the pipeline segment (Task Profiler → Planner → Task Graph).

**Depends on:** Phase 2.

## Phase 4: Agent State

**Objective:** Implement the runtime state container.

**Entry Criteria:** Phase 3 is complete. Task Graphs are constructible.

**Deliverables:**
- AgentState implementation with full lifecycle.
- State initialization from pipeline outputs (Request, Intent, LayaClassification, TaskGraph).
- State mutation operations (add observation, update node status, record error).
- State query operations (get current step, get execution history, get status).
- Unit tests for all state operations.
- Invariant enforcement tests (append-only history, single active node, irreversible terminal transitions).

**Depends on:** Phase 3.

## Phase 5: Decision Engine and Reasoning Provider

**Objective:** Implement LLM-backed decision-making.

**Entry Criteria:** Phase 4 is complete. AgentState is functional.

**Deliverables:**
- Decision Engine implementation.
- LLM provider adapter interface.
- Structured output configuration (prompt engineering for Decision schema).
- Decision Engine structural validation (schema + parameter discriminated union).
- Orchestrator contextual validation (state checks, retry/replan limit enforcement).
- Orchestrator policy validation via Policy Engine interface.
- Confidence scoring and low-confidence handling.
- Unit tests with mock LLM responses.
- Contract tests for Decision schema validation.
- Orchestrator tests for contextual validation and limit enforcement.

**Depends on:** Phase 4.

## Phase 6: Agent Orchestrator

**Objective:** Implement the full agentic control loop.

**Entry Criteria:** Phase 5 is complete. Decision Engine produces valid Decisions.

**Deliverables:**
- Agent Orchestrator implementation.
- Full OBSERVE → DECIDE → ACT → OBSERVE RESULT → VERIFY → UPDATE STATE → DECIDE AGAIN loop.
- Tool invocation through Tool Manager interface.
- Policy check integration.
- Observation and verification logic.
- Terminal state handling (COMPLETE, FAIL).
- Agent-loop tests for all decision types.
- End-to-end tests with mock tools (simple task, retry, replan, ASK_USER, completion, failure).

**Depends on:** Phase 5.

## Phase 7: Deterministic Mock Tools and End-to-End Agent Tests

**Objective:** Complete the mock tool layer and validate the full system.

**Entry Criteria:** Phase 6 is complete. Orchestrator drives the full loop.

**Deliverables:**
- Deterministic mock implementations for all downstream tool interfaces (Policy Engine, Browser Tools, Windows Tools, File System Tools, Vision).
- Mock tool configuration framework for test scenarios.
- Failure simulation framework (configurable error injection).
- Comprehensive agent-loop tests with mock tools.
- Failure/recovery tests (retry exhaustion, replan exhaustion, policy denial, loop detection, wait timeout).
- Performance baseline tests (task completion time, token usage).

**Depends on:** Phase 6.

## Phase 8: Real Tool Integrations

**Objective:** Replace mock tools with real implementations.

**Entry Criteria:** Phase 7 is complete. All tests pass with mock tools.

**Deliverables:**
- Real Policy Engine implementation.
- Real File System Tool implementation.
- Real Windows Tool implementation (if in scope for this phase).
- Real Browser Tool implementation (if in scope for this phase).
- Tool integration tests against real systems.
- Migration from mock tools to real tools in the Orchestrator.

**Depends on:** Phase 7.

**Note:** The scope of Phase 8 may be split into sub-phases depending on the number of tool integrations required. Each tool integration is independently testable and deployable.

## Inter-Phase Dependency Map

```
Phase 0 ──▶ Phase 1 ──▶ Phase 2 ──▶ Phase 3 ──▶ Phase 4 ──▶ Phase 5 ──▶ Phase 6 ──▶ Phase 7 ──▶ Phase 8
  docs       schemas     pipeline    planning     state        decisions    orchestrator  mocks        real tools
```

Each phase depends on the previous phase's deliverables. No phase may begin until the previous phase's exit criteria are met.
