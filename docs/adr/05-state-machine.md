# State Machine

## AgentState Lifecycle

The `AgentState` object transitions through a defined set of states during its lifetime. State transitions are controlled exclusively by the Agent Orchestrator.

```
                    ┌─────────┐
                    │ PENDING  │ (initial state after initialization)
                    └────┬────┘
                         │ Orchestrator begins loop
                         ▼
                    ┌─────────┐
          ┌───────▶│ OBSERVING│◀──────────┐
          │        └────┬────┘            │
          │             │                 │
          │             ▼                 │
          │       ┌──────────┐            │
          │       │ DECIDING │            │
          │       └────┬─────┘            │
          │             │                 │
          │    ┌────────┼────────┐        │
          │    │        │        │        │
          │    ▼        ▼        ▼        │
          │  ┌──────┐ ┌──────┐ ┌────────┐│
          │  │EXEC- │ │REPLAN│ │ASK_USER││
          │  │UTING │ │NING  │ │ / WAIT ││
          │  └──┬───┘ └──┬───┘ └───┬────┘│
          │     │        │         │     │
          │     │        │         │     │
          │     ▼        ▼         ▼     │
          │  ┌─────────────────────────┐ │
          │  │      VERIFYING          │ │
          │  └───────────┬─────────────┘ │
          │              │               │
          │              ▼               │
          │    ┌──────────────────┐      │
          └────│     COMPLETED    │──────┘
               │     or FAILED    │
               └──────────────────┘
```

## State Definitions

### PENDING

**Initial state.** The AgentState has been created by the Planner but the agentic loop has not started.

**Transitions:**
- → OBSERVING: The Orchestrator begins the first loop iteration.

### OBSERVING

**Active.** The Orchestrator is collecting the current state of the world and the active Task Graph node.

**Transitions:**
- → DECIDING: Observation is complete; the Orchestrator passes state to the Decision Engine.

### DECIDING

**Active.** The Orchestrator is waiting for the Decision Engine to produce a Decision.

**Transitions:**
- → EXECUTING: Decision is EXECUTE, validation and policy pass.
- → OBSERVING: Decision is OBSERVE (information gathering).
- → REPLANNING: Decision is REPLAN.
- → VERIFYING (special): Decision is RETRY (skip to verify/retry the previous step).
- → AWAITING: Decision is ASK_USER or WAIT.
- → COMPLETED: Decision is COMPLETE.
- → FAILED: Decision is FAIL.

### EXECUTING

**Active.** The Orchestrator is executing a tool or action.

**Transitions:**
- → VERIFYING: Tool execution returns a result.
- → FAILED: Tool execution encounters an unrecoverable error.

### REPLANNING

**Active.** The Task Graph is being revised.

**Transitions:**
- → OBSERVING: Replan is complete; the new Task Graph is set; loop restarts.
- → FAILED: `AgentState.replan_count` exceeds `RuntimeConfig.max_replans` (default: 3). The Orchestrator enforces this limit.

### AWAITING

**Active (blocked).** The Orchestrator is waiting for user input or an external condition.

**Transitions:**
- → OBSERVING: User responded or condition met.
- → FAILED: Timeout or user cancellation.

### VERIFYING

**Active.** The Orchestrator is verifying the result of the last action.

**Transitions:**
- → OBSERVING: Verification passed or needs another observation.
- → REPLANNING: Verification revealed that replanning is needed.
- → EXECUTING: Decision is RETRY and retry count is within limits.
- → FAILED: Verification failed and both retry and replan are not possible (retry_count ≥ max_retries AND replan_count ≥ max_replans).

### COMPLETED

**Terminal.** The task finished successfully.

**Transitions:**
- None (terminal state).

### FAILED

**Terminal.** The task could not be completed.

**Transitions:**
- None (terminal state).

## TaskGraph Node Lifecycle

Individual nodes within the TaskGraph also follow a lifecycle:

```
PENDING → ACTIVE → COMPLETED
              │
              ▼
           FAILED → RETRYING → ACTIVE (if retry available)
                    │
                    ▼
                 FAILED (if retry exhausted)
```

| Node Status | Meaning |
|---|---|
| **PENDING** | Node has not been reached yet. |
| **ACTIVE** | Node is currently being executed. |
| **COMPLETED** | Node executed successfully and passed verification. |
| **FAILED** | Node execution failed. |
| **RETRYING** | Node is being retried after a failure. |
| **SKIPPED** | Node was bypassed during replanning. |

## Invariants

1. Only one node is ACTIVE at a time.
2. A node cannot transition from PENDING to COMPLETED without passing through ACTIVE.
3. A node marked COMPLETED cannot be returned to ACTIVE.
4. The AgentState can only be in one status at a time.
5. Transitions to terminal states (COMPLETED, FAILED) are irreversible.
6. During REPLANNING, existing COMPLETED nodes remain COMPLETED. Only PENDING and FAILED nodes are eligible for modification.
7. The execution history is append-only. Steps are never removed or modified after recording.
8. The Orchestrator enforces `RuntimeConfig.max_replans`. When `AgentState.replan_count > RuntimeConfig.max_replans`, the Orchestrator transitions REPLANNING to FAILED. The Orchestrator owns this check; no other component enforces it.

## State and Persistent Memory

AgentState is transient — it exists only for the duration of a single task execution. It is not persisted across restarts.

Persistent memory (future phase) is a separate system. AgentState and persistent memory are distinct and must not be conflated. AgentState may reference persistent memory entries, but persistent memory does not control AgentState transitions.
