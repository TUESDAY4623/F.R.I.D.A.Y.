# Component Specification

This document defines the responsibility, inputs, outputs, and dependencies of each component in the Jarvis pipeline.

## 1. Input Processor

**Responsibility:** Accept raw user input, normalize it, validate its structure, and produce a structured `Request` object.

**Inputs:**
- Raw user input (natural language text, may include structured data from future interfaces)

**Outputs:**
- `Request` — structured representation of the user's input

**Behavior:**
- Performs input normalization (encoding, whitespace, formatting).
- Validates that the input is non-empty and well-formed.
- Does not classify intent or analyze the request's content.
- Does not modify the semantic meaning of the input.
- Produces a `Request` and passes it to the Intent Manager.

**Dependencies:**
- None (entry point of the pipeline)

**Does not:**
- Classify the user's intent
- Plan or execute tasks
- Call any LLM

---

## 2. Intent Manager

**Responsibility:** Accept Laya's raw classification and produce a validated, canonical Intent. The Intent Manager is the application-level normalization layer between raw classification and downstream task analysis. It does not independently classify the request.

**Inputs:**
- `LayaClassification` from Laya

**Outputs:**
- `Intent` — a validated, normalized intent derived from Laya's classification

**Behavior:**
- Takes Laya's raw semantic classification (`category`, `entities`, `characteristics`, `confidence`, `ambiguous`) and produces a canonical intent representation.
- Validates and enriches extracted entities.
- Refines Laya's characteristics into intent-level constraints.
- Normalizes the intent form (canonical wording, structured representation).
- Resolves or flags ambiguity.
- Produces an `Intent` and passes it to the Task Profiler.

**Dependencies:**
- Laya (upstream)
- Task Profiler (downstream)

**Does not:**
- Independently classify the request (Laya performs the initial classification)
- Detect request complexity (that is the Task Profiler's job)
- Construct execution plans

---

## 3. Laya

**Responsibility:** Perform semantic classification of the user's request. Laya produces a raw classification including intent category, entity extraction, confidence, and ambiguity detection. Laya does not classify task complexity.

**Inputs:**
- `Request` from the Input Processor

**Outputs:**
- `LayaClassification` — raw semantic classification of the request

**Behavior:**
- Determines the semantic intent category of the request (e.g., informational, actionable, query, command).
- Extracts entities from the request (file paths, app names, URLs, etc.).
- Assigns a classification confidence score.
- Detects whether the request is ambiguous and records the reason.
- Identifies request characteristics (e.g., multi-step, external-data, requires-confirmation).
- Does not assess task complexity — that belongs to the Task Profiler.
- Produces a `LayaClassification` and passes it to the Intent Manager.

**Dependencies:**
- Input Processor (upstream)
- Intent Manager (downstream, receives LayaClassification for normalization)
- Task Profiler (downstream, receives LayaClassification for profiling)

**Does not:**
- Normalize intent (that is the Intent Manager's job)
- Profile task requirements (that is the Task Profiler's job)
- Assess task complexity (that is the Task Profiler's job)
- Construct execution plans

---

## 4. Task Profiler

**Responsibility:** Analyze the classified intent and request to determine the characteristics and requirements of the task.

**Inputs:**
- `Intent` from the Intent Manager
- `LayaClassification` from Laya

**Outputs:**
- `TaskProfile` — analysis of task characteristics, requirements, constraints, and complexity

**Behavior:**
- Classifies task characteristics (single-step, multi-step, exploratory, etc.).
- Estimates task complexity (low, medium, high).
- Identifies required capabilities (tools needed, data needed, permissions needed).
- Identifies constraints and prerequisites.
- Provides an informational step count estimate (`estimated_steps`) in TaskProfile. The Planner is not bound by this estimate — the TaskGraph is authoritative for actual execution structure.
- Produces a `TaskProfile` and passes it to the Planner.

**Dependencies:**
- Intent Manager (upstream)
- Laya (upstream)
- Planner (downstream)

**Does not:**
- Classify the request (Laya's job)
- Determine the actual execution step count (the Planner does that via the TaskGraph)
- Construct the execution strategy (Planner's job)
- Execute any actions

---

## 5. Planner

**Responsibility:** Formulate the execution strategy by constructing a TaskGraph from the TaskProfile.

**Inputs:**
- `TaskProfile` from the Task Profiler
- `Intent` from the Intent Manager
- `LayaClassification` from Laya

**Outputs:**
- `TaskGraph` — the authoritative representation of the execution structure

**Behavior:**
- Receives the TaskProfile from the Task Profiler.
- Determines the actual task decomposition — the number and nature of execution steps. The Planner is not bound by `TaskProfile.estimated_steps`; the TaskGraph it produces is the sole source of truth for execution structure.
- Constructs a TaskGraph where each node represents one execution step and edges represent dependencies and ordering.
- The TaskGraph is the authoritative execution structure. Downstream components (Agent State, Decision Engine, Agent Orchestrator) consume the TaskGraph, not the TaskProfile, for execution planning.
- Assigns identifiers to nodes and defines their dependencies.
- Produces a `TaskGraph` and passes it to Agent State for initialization.
- Provides `replan()` to construct a revised TaskGraph when the Orchestrator requests replanning. Replanning preserves COMPLETED nodes and modifies or replaces PENDING and FAILED nodes. The execution history is preserved. Replanning produces a new TaskGraph — it does not patch the existing graph.

**Interface:**

```
Planner
├── plan(profile: TaskProfile, intent: Intent, laya: LayaClassification): TaskGraph
├── replan(current_graph: TaskGraph, agent_state: AgentState, reason: string, preserve_completed: boolean): TaskGraph
└── validate(graph: TaskGraph): ValidationResult    // (see ADR 04)
```

**Dependencies:**
- Task Profiler (upstream, provides TaskProfile)
- Agent State (upstream, provides replan context)
- Agent Orchestrator (downstream, receives TaskGraphs)

**Task Graph properties:**
- Nodes are action steps. Each node has a type, parameters, and expected outcome.
- Edges define ordering and dependency constraints.
- The TaskGraph is the sole authoritative representation of execution structure.

**Does not:**
- Assess task complexity (that is the Task Profiler's job)
- Follow `TaskProfile.estimated_steps` as a constraint on node count
- Mutate the TaskGraph directly during execution — mutations go through `replan()`, which produces a new TaskGraph
- Determine runtime execution decisions (Decision Engine's job)
- The graph may be linear or branched.
- The graph is mutable — the Planner may add, remove, or reorder nodes during replanning. The Orchestrator must never mutate graph structure directly.

**Does not:**
- Execute actions
- Track runtime state
- Make decisions during execution
- Mutate the Task Graph in place (graph mutations go through `replan()`, which returns a new graph)

---

## 6. Agent State

**Responsibility:** Represent and maintain the current runtime state of a single task execution.

**Inputs:**
- `Request` from the Input Processor
- `Intent` from the Intent Manager
- `LayaClassification` from Laya
- `TaskGraph` from the Planner

**Outputs:**
- Current state snapshot provided to the Decision Engine
- Updated state after each execution step

**Behavior:**
- Initializes with the Request, Intent, LayaClassification, and TaskGraph.
- Tracks the current execution step (which node in the Task Graph is active).
- Maintains an execution history (observations, results, decisions made).
- Tracks the current status of the task (pending, executing, completed, failed, awaiting user input).
- Is mutated only by the Agent Orchestrator through explicit update operations.
- Is the single source of truth for runtime task state.
- Is distinct from persistent memory — it is in-memory and scoped to a single task execution.

**Dependencies:**
- Input Processor (upstream, receives Request)
- Intent Manager (upstream, receives Intent)
- Laya (upstream, receives LayaClassification)
- Planner (upstream, receives TaskGraph)
- Decision Engine (downstream, provides state for reasoning)
- Agent Orchestrator (downstream, mutated by orchestrator)

**Does not:**
- Classify requests or intents
- Plan tasks
- Make decisions
- Execute tools

---

## 7. Decision Engine

**Responsibility:** Reason over the current Agent State and determine what should happen next.

**Inputs:**
- Current `AgentState` snapshot

**Outputs:**
- `Decision` — a structured decision specifying the next action

**Behavior:**
- Receives the current Agent State from the Agent Orchestrator.
- Uses an LLM to reason over the state and produce a structured Decision.
- The Decision is one of eight types: EXECUTE, OBSERVE, REPLAN, RETRY, ASK_USER, WAIT, COMPLETE, or FAIL.
- Performs structural validation before returning:
  - Schema validation — the Decision conforms to the Decision schema (ADR 04).
  - Parameter contract validation — the Decision's `parameters` contain all required fields for its `DecisionType` (ADR 04 discriminated union).
- Does not perform contextual AgentState validation (e.g., checking whether the target node is PENDING, whether dependencies are COMPLETED, whether retry limits are exceeded).
- Does not perform policy validation.
- Produces a `Decision` and passes it to the Agent Orchestrator.

**Dependencies:**
- Agent State (upstream, read-only reference for LLM reasoning context)
- Agent Orchestrator (downstream)
- LLM provider (external, via adapter)

**Does not:**
- Execute the Decision (the Agent Orchestrator does that)
- Modify Agent State directly
- Construct the Task Graph
- Validate whether a Decision is contextually valid in the current AgentState (the Orchestrator does that)
- Perform policy validation (the Orchestrator invokes the Policy Engine)

---

## 8. Agent Orchestrator

**Responsibility:** Control the full agentic execution loop, from observation through decision, action, verification, and state update.

**Inputs:**
- `Decision` from the Decision Engine
- Tool results and observations from downstream systems (mocked)

**Outputs:**
- Updated `AgentState`
- Final task result

**Behavior:**
- Drives the OBSERVE → DECIDE → ACT → OBSERVE RESULT → VERIFY → UPDATE STATE → DECIDE AGAIN loop.
- Calls the Decision Engine to obtain a Decision.
- After receiving a Decision, performs full validation before acting:
  1. **Structural validation** — the Decision conforms to the Decision schema and its parameters match the discriminated union for its type. (This is the Decision Engine's own output validation.)
  2. **Contextual state validation** — the Decision is valid given the current AgentState:
     - For EXECUTE: the target node exists and is PENDING; all dependencies are COMPLETED.
     - For RETRY: the target node exists and has remaining retries. `AgentState.retry_count` is authoritative — the Orchestrator must not rely on `Decision.parameters.retry_count` for limit checks. The Orchestrator increments `AgentState.retry_count` after each RETRY.
     - For REPLAN: `AgentState.replan_count < RuntimeConfig.max_replans` (the Orchestrator increments `replan_count` after issuing the REPLAN; if the new count exceeds `max_replans`, the Orchestrator transitions to FAILED instead of OBSERVING).
     - For COMPLETE: all required nodes are COMPLETED.
     - For FAIL: the failure reason is valid.
  3. **Policy validation** — the Decision is submitted to the Policy Engine for approval when required.
- Rejects or transforms invalid Decisions (re-queries the Decision Engine, escalates to a safer Decision type, or escalates to FAIL).
- Enforces retry and replan limits.
- On REPLAN: calls `Planner.replan()` to obtain a revised Task Graph, then updates Agent State with the new graph. The Orchestrator never constructs or mutates graph structure itself.
- Executes the Decision by invoking tools through the Tool Manager interface.
- Observes tool results.
- Verifies results against expectations.
- Updates Agent State.
- Handles terminal decisions (COMPLETE, FAIL).
- Emits observability events at each step.
- Is the current implementation boundary — all upstream components (Input Processor through Decision Engine) are part of this milestone. Downstream tool execution goes through mocks.

**Dependencies:**
- Decision Engine (upstream, for decisions)
- Agent State (read/write)
- Policy Engine (interface, for validation)
- Tool Manager (interface, for execution)

**Does not:**
- Classify requests or intents
- Construct the Task Graph
- Mutate Task Graph structure directly (delegates to Planner)
- Directly reason over LLM outputs (the Decision Engine does that)
- Perform structural schema validation on Decisions (the Decision Engine does that)
