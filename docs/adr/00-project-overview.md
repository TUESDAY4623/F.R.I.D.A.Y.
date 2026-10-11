# Project Overview

## Purpose

Jarvis is an agentic desktop AI system designed to understand natural-language requests, plan tasks, reason over current state, and execute actions through controlled tools.

The system accepts a natural-language request from a user, classifies the intent, profiles the task, plans a sequence of actions, and executes those actions through an agentic control loop that observes results, verifies outcomes, and adapts to new information.

## Current Implementation Boundary

The current implementation target is:

```
User Input → Input Processor → Laya → Intent Manager → Task Profiler → Planner → Agent State → Decision Engine → Agent Orchestrator
```

The current development milestone ends at the **Agent Orchestrator**.

Downstream systems — Policy Engine, Tool Manager, Browser Tools, Windows Tools, File System Tools, Vision, and real-world execution — are initially represented using **interfaces and deterministic mocks**. Real tool execution is not implemented in the current milestone.

## Scope

### In Scope (Current Milestone)

- Natural-language input processing and normalization
- Intent classification and normalization
- Task profiling and requirements analysis
- Task planning and initial strategy generation
- Runtime agent state management
- Decision engine with LLM-backed structured reasoning
- Agent orchestration with full agentic control loop
- Interface contracts for downstream systems
- Deterministic mock tools for testing

### Out of Scope (Future Phases)

- Voice wake word
- Graphical user interface
- Windows desktop automation
- Browser automation
- Vision capabilities
- Persistent memory and vector database
- Multi-agent architecture
- Complex RAG pipelines
- Creative tool integrations (Blender, Figma)
- Background autonomous operation

These are explicitly deferred. They belong to later phases and must not be implemented during the current milestone.

## Core Principles

1. **Laya** classifies user requests semantically, extracts entities, and detects ambiguity.
2. **Intent Manager** normalizes Laya's raw classification into a validated, canonical Intent.
3. **Task Profiler** determines task characteristics, requirements, and complexity.
4. **Planner** proposes an initial execution strategy.
5. **Task Graph** represents the initial strategy.
6. **Task Graph** is revisable and must not be treated as a rigid workflow.
7. **Agent State** represents the current runtime state of a task.
8. **Decision Engine** determines what should happen next.
9. **Agent Orchestrator** controls the agentic execution loop.
10. LLMs propose structured decisions; they do not directly execute tools.
11. All LLM outputs must be schema validated.
12. Real tool execution must occur behind explicit interfaces.
13. **Agent State** is different from persistent memory.
14. The Orchestrator must react to observations rather than blindly following the original plan.
15. The system must support retry, replan, ask-user, completion, and failure paths.
16. Architecture changes must be documented.

## Agentic Control Loop

The fundamental execution loop:

```
OBSERVE → DECIDE → ACT → OBSERVE RESULT → VERIFY → UPDATE STATE → DECIDE AGAIN
```

Possible decisions at the DECIDE step:

- **EXECUTE** — proceed with the next planned action
- **OBSERVE** — gather additional information before proceeding
- **REPLAN** — revise the Task Graph due to changed circumstances
- **RETRY** — repeat the last action (e.g., after a recoverable failure)
- **ASK_USER** — request additional input or confirmation
- **WAIT** — pause for an external condition
- **COMPLETE** — the task is successfully finished
- **FAIL** — the task cannot be completed

## Success Criteria

The system is successful when:

- A natural-language request enters the pipeline and produces a structured response.
- The agentic control loop executes through the full EXECUTE → OBSERVE RESULT → VERIFY → UPDATE STATE cycle without hardcoded bypasses.
- The Decision Engine produces structurally validated decisions for every DECIDE step.
- All LLM interactions produce structured outputs validated against defined schemas.
- The system handles retry, replan, ASK_USER, completion, and failure paths without crashes.
- All core components are independently testable without external applications.
- Architecture violations are detectable through documentation review and test assertions.

## Glossary

| Term | Definition |
|---|---|
| **Request** | The structured representation of user input, produced by the Input Processor. |
| **Intent** | A validated, canonical representation of the user's intent, produced by the Intent Manager from Laya's raw classification. Contains a normalized form, validated entities, and refined constraints. Does not independently classify the request. |
| **Task** | A unit of work derived from an Intent, consisting of one or more steps in a Task Graph. |
| **Laya** | The component that performs semantic classification of a user request: intent category, entity extraction, confidence scoring, and ambiguity detection. Does not assess task complexity. |
| **Task Graph** | A directed graph of steps representing the planned execution strategy for a task. Nodes are actions; edges represent dependencies and ordering. |
| **Task Graph Node** | A single step in a Task Graph, representing one unit of planned work. |
| **Task Graph Edge** | A dependency relationship between two Task Graph Nodes. |
| **Agent State** | The in-memory runtime state of a single task execution. Contains the Request, Intent, Task Graph, execution history, and current status. Distinct from persistent memory. |
| **Decision** | A structured output from the Decision Engine specifying the next action. One of eight types: EXECUTE, OBSERVE, REPLAN, RETRY, ASK_USER, WAIT, COMPLETE, or FAIL. |
| **Decision Validation** | A two-phase process. Phase 1 (Decision Engine): structural validation of the Decision against the schema and parameter discriminated union. Phase 2 (Agent Orchestrator): contextual validation against the current AgentState plus policy validation via the Policy Engine. |
| **Agent Orchestrator** | The component that controls the agentic execution loop. It drives the OBSERVE → DECIDE → ACT → OBSERVE RESULT → VERIFY → UPDATE STATE → DECIDE AGAIN cycle. |
| **Policy Engine** | A downstream interface that validates actions against security and policy rules before execution. Represented as an interface in the current milestone. |
| **Tool Manager** | A downstream interface that manages tool discovery, registration, and execution. Represented as an interface in the current milestone. |
| **Tool** | An executable action unit. In the current milestone, tools are represented by deterministic mocks behind the Tool Manager interface. |
| **Observation** | The result returned after executing an action or gathering information. |
| **Verification** | The process of checking whether an Observation matches the expected outcome of a step. |
| **Replan** | The process of revising the Task Graph via `Planner.replan()`. The Agent Orchestrator decides when to replan; the Planner owns all graph construction and mutation. |
| **Schema Validation** | The process of checking structured data (LLM outputs, tool results, inter-component messages) against a defined schema. |

## Source of Truth Hierarchy

When conflicts arise, the following hierarchy determines authority:

1. **CLAUDE.md** — Project-level instructions and constraints
2. **docs/** — Architecture documentation (this directory)
3. **schemas/** — JSON Schema definitions for data contracts
4. **source code** — Implementation
5. **tests** — Test specifications

If code conflicts with documented architecture, do not silently redefine the architecture through code. Raise the conflict and propose a documented change.
