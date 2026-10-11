# System Architecture

## Overview

Jarvis is a pipeline of nine components through which a natural-language request flows from entry to agentic execution. Each component has a single, well-defined responsibility and communicates with adjacent components through explicit data contracts.

```
User Input
    │
    ▼
┌─────────────────┐     ┌────────────────┐     ┌────────────────┐
│  Input Processor │────▶│ Laya           │────▶│ Intent         │
│                  │     │                │     │ Manager        │
└─────────────────┘     └────────────────┘     └────────────────┘
                                                       │
                                                       ▼
                                              ┌────────────────┐
                                              │ Task Profiler  │
                                              └────────────────┘
                                                       │
                                                       ▼
                                              ┌────────────────┐
                                              │ Planner        │
                                              └────────────────┘
                                                       │
                                                       ▼
                                              ┌────────────────┐
                                              │ Agent State    │
                                              └────────────────┘
                                                       │
                                              ┌────────┴────────┐
                                              ▼                 ▼
                                    ┌──────────────┐  ┌────────────────┐
                                    │ Decision      │  │ Agent           │
                                    │ Engine        │  │ Orchestrator    │
                                    └──────────────┘  └────────────────┘
                                              │                 │
                                              └────────┬────────┘
                                                       ▼
                                              ┌────────────────┐
                                              │ Downstream     │
                                              │ Systems        │
                                              │ (mocked)       │
                                              └────────────────┘
```

## Component Boundaries

Each component owns a specific stage of the pipeline. Ownership is strict — a component must not perform the responsibilities of another component.

| Component | Owns | Does Not Own |
|---|---|---|
| **Input Processor** | Raw input normalization, validation, structuring | Intent classification, planning |
| **Intent Manager** | Normalization of Laya's classification into a validated, canonical Intent | Independent request classification (Laya), task complexity (Task Profiler), strategy formulation |
| **Laya** | Semantic intent classification, entity extraction, ambiguity detection, confidence scoring | Intent normalization (Intent Manager), task complexity (Task Profiler), strategy formulation |
| **Task Profiler** | Task characteristic analysis, requirement identification, complexity assessment | Strategy formulation (Planner), execution, complexity assessment by other components |
| **Planner** | Task decomposition, TaskGraph construction, execution strategy, graph revision (`replan()`). The TaskGraph is authoritative — the TaskGraph determines the actual step count. | Runtime state tracking (Agent State), execution decisions, direct graph mutation by other components, binding to TaskProfile.estimated_steps |
| **Agent State** | Runtime state tracking for a single task execution | Strategy planning (Planner), decision-making |
| **Decision Engine** | Determining the next action via LLM reasoning | Task Graph construction (Planner), tool execution |
| **Agent Orchestrator** | Control loop execution, state transitions, observation | Decision logic (Decision Engine), tool implementation |

## Data Flow

1. **User Input** arrives as raw text.
2. **Input Processor** normalizes and validates it into a structured `Request`.
3. **Laya** performs semantic classification on the Request, producing a `LayaClassification` (category, entities, characteristics, confidence, ambiguity detection). Task complexity is not assessed here.
4. **Intent Manager** takes Laya's raw classification and produces a validated, canonical `Intent` (normalized form, validated entities, refined constraints, resolved ambiguity). The Intent Manager does not independently classify the request.
5. **Task Profiler** analyzes the Intent and LayaClassification to determine task requirements and **task complexity** (the only component that assesses complexity), producing a `TaskProfile`.
6. **Planner** receives the TaskProfile from the Task Profiler and the Intent/LayaClassification from the prior stages. The Planner determines the actual task decomposition and constructs a TaskGraph. The TaskGraph is authoritative for execution structure — it is not constrained by TaskProfile.estimated_steps.
7. **Agent State** is initialized with the Request, Intent, LayaClassification, TaskGraph, and begins tracking execution.
8. **Decision Engine** reasons over Agent State to produce a structurally validated `Decision`.
9. **Agent Orchestrator** acts on the Decision:
   - On REPLAN: calls `Planner.replan()` to obtain a revised Task Graph, validates it via `Planner.validate()`, and updates Agent State. The Orchestrator never constructs or mutates graph structure directly.
   - On other decisions: executes the action, observes results, verifies outcomes, and updates Agent State.
10. The Orchestrator loops back to the Decision Engine until the task reaches a terminal state.

## Control Flow

The Agent Orchestrator drives the main execution loop:

```
LOOP:
    1. OBSERVE   — collect current Agent State
    2. DECIDE    — Decision Engine produces a Decision
    3. VALIDATE  — Decision is validated (schema + decision validation + policy)
    4. ACT       — Orchestrator executes the Decision (tool call or user interaction)
    5. OBSERVE   — collect the result (tool output, user response)
    6. VERIFY    — check the result against expectations
    7. UPDATE     — update Agent State with new observations
    8. REPEAT     — return to DECIDE
```

The loop terminates when the Decision is COMPLETE or FAIL.

## Downstream Systems (Current Milestone)

The following systems are **not implemented** in the current milestone. They exist as interfaces and deterministic mocks:

- **Policy Engine** — validates actions against security and policy rules
- **Tool Manager** — discovers, registers, and executes tools
- **Browser Tools** — browser interaction capabilities
- **Windows Tools** — OS-level desktop automation
- **File System Tools** — filesystem read/write operations
- **Vision** — image understanding capabilities

## Design Constraints

1. No component may bypass the Agent Orchestrator to execute tools directly.
2. No component may reach into another component's internal state.
3. LLM outputs always flow through schema validation before reaching any component.
4. All inter-component communication uses defined data contracts.
5. Agent State is the single source of truth for runtime task state.
6. The Task Graph may be revised at any point but must be represented in Agent State.
7. Downstream system interfaces must be mockable with deterministic behavior for testing.

## Unresolved Decisions

- **Technology stack** — Programming language, runtime, build tool, and dependency management are not yet selected. This affects how interfaces, schemas, and components are expressed.
- **LLM provider** — Which LLM provider and SDK are used is not yet selected. This affects the Decision Engine's integration approach.
