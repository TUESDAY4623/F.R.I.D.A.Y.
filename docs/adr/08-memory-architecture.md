# Memory Architecture

## Two Memory Layers

Jarvis has two distinct memory layers. Confusing them is a common architectural error. This document defines the boundary clearly.

### Agent State (Transient, Per-Task)

AgentState is the runtime representation of a single task execution. It is:

- **In-memory only** — not persisted to disk or any external store.
- **Scoped to one task** — created when a task begins, destroyed when the task reaches a terminal state (COMPLETED or FAILED).
- **Mutable during execution** — updated by the Agent Orchestrator at each step.
- **The single source of truth for runtime task state** — all components read from AgentState, none write to it except the Orchestrator.

AgentState contains:
- The original Request, Intent, LayaClassification, and TaskProfile.
- The current (possibly revised) TaskGraph.
- The execution history (observations, decisions, verifications).
- The current node being executed.
- The overall task status.
- Error records.

### Persistent Memory (Future, Cross-Task)

Persistent Memory is a planned system for retaining information across task executions. It is **not implemented in the current milestone**.

In future phases, Persistent Memory may include:
- User preferences and settings.
- Learned facts about the user's environment.
- Past task outcomes and lessons learned.
- Tool usage patterns.
- Conversation history.

Persistent Memory is a separate system from AgentState. It is owned by a future memory subsystem, not by any current component.

## Relationship Between the Two

```
AgentState (this task)                    Persistent Memory (future)
┌──────────────────────┐                 ┌──────────────────────┐
│ Request              │                 │ User preferences      │
│ Intent               │                 │ Past task outcomes    │
│ TaskGraph            │                 │ Learned facts         │
│ Execution history    │                 │ Conversation history  │
│ Current step         │                 │                      │
│ Status               │                 │                      │
│ Observations         │                 │                      │
│ Errors               │                 │                      │
└──────────────────────┘                 └──────────────────────┘
        │                                           │
        │  may reference                            │  may inform
        │                                           │
        └───────────────────┬───────────────────────┘
                            ▼
                    Agent Orchestrator
```

The Orchestrator may:
- **Read** from Persistent Memory to inform decisions (future).
- **Write** to Persistent Memory after task completion (future).
- **Never** let Persistent Memory modify AgentState directly.

AgentState may reference Persistent Memory entries (e.g., a user preference that affects how a task is planned), but Persistent Memory does not control AgentState transitions.

## What Is Not Memory

The following are explicitly **not** part of the memory architecture:

- **Execution history** within AgentState is an audit trail, not memory. It records what happened during this task execution but is not used to inform future tasks (until Persistent Memory is implemented).
- **Task Graph** is a plan, not memory. It represents the intended strategy, not learned knowledge.
- **LLM context** (prompt history) is part of the Decision Engine's implementation, not a memory system. It is ephemeral and scoped to a single LLM call.

## Constraints

1. AgentState is never serialized or persisted in the current milestone.
2. AgentState is destroyed when a task reaches a terminal state.
3. No component except the Orchestrator may modify AgentState.
4. Persistent Memory is not implemented. References to it are forward-looking and must not be implemented as runtime behavior.
5. The Decision Engine may use AgentState as context for LLM calls but must not store LLM context in AgentState.
6. Test fixtures may serialize AgentState for test setup, but production code must not.
