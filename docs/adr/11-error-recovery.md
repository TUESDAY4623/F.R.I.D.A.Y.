# Error Recovery

## Overview

The system must handle failures gracefully. This document defines the retry, replan, failure, and escalation paths for recoverable and unrecoverable errors.

## Error Categories

### Recoverable Errors

Errors from which the system can recover through retry or alternative paths.

| Error | Recovery Action |
|---|---|
| Tool execution timeout | RETRY with same parameters |
| Transient tool failure | RETRY with same parameters |
| Network error (mock) | RETRY |
| Low-confidence decision | Re-query Decision Engine or ASK_USER |
| Verification mismatch (minor) | RETRY or OBSERVE for more information |
| Policy warning (not denial) | Proceed with conditions logged |

### Unrecoverable Errors

Errors from which the system cannot recover. These lead to task failure.

| Error | Escalation |
|---|---|
| Tool execution failure after retry limit exhausted | FAIL |
| Policy denial with no alternative path | FAIL |
| Invalid Task Graph after replan attempt | FAIL |
| Decision Engine produces structurally invalid output after re-query | FAIL |
| Verification failure after replan | FAIL |
| User declines to proceed (ASK_USER) | FAIL |
| Wait timeout with no resolution | FAIL |

## Retry Logic

When a RETRY decision is issued:

1. The Orchestrator increments `AgentState.retry_count` for the current Task Graph node. `AgentState.retry_count` is the authoritative retry counter. `Decision.parameters.retry_count` is informational only — the Orchestrator must not trust it over `AgentState.retry_count`.
2. If `AgentState.retry_count ≤ RuntimeConfig.max_retries` (default: 3):
   - The Orchestrator re-invokes the tool/action.
   - The result is observed and verified as normal.
3. If `AgentState.retry_count > RuntimeConfig.max_retries`:
   - The Orchestrator does not issue another RETRY.
   - The Orchestrator issues a REPLAN decision. The Decision Engine reasons over the failure context and produces a structurally valid Decision.
   - The Orchestrator performs contextual state validation (checks replan limit) and policy validation.
   - After validation passes, the Orchestrator calls `Planner.replan()` to obtain a revised Task Graph.
   - The Orchestrator increments `AgentState.replan_count`. If `AgentState.replan_count > RuntimeConfig.max_replans`, the Orchestrator transitions to FAILED instead of OBSERVING.
   - If replanning produces a valid graph and the replan limit is not exceeded, the Orchestrator updates Agent State and continues.
   - If replanning is not possible or returns an invalid graph, the Orchestrator escalates to FAIL.

### Retry Parameters

```
RetryContext
├── node_id: string          // The node being retried
├── attempt: number          // Current attempt number (1-indexed)
├── max_attempts: number     // From TaskGraphNode.retry_limit
├── previous_errors: ErrorRecord[] // Errors from previous attempts
└── adjusted_params: object  // Modified parameters for this attempt (if any)
```

## Replan Logic

When a REPLAN decision is issued:

1. The Orchestrator calls `Planner.replan()`, passing the current Task Graph, current Agent State, the replan reason, and `preserve_completed`.
2. The Planner returns a revised Task Graph.
3. The Orchestrator validates the revised graph via `Planner.validate()`.
4. If the graph is valid, the Orchestrator updates Agent State with the new graph. The execution history is preserved.
5. The Orchestrator returns to OBSERVING with the new graph.

### Replan Limits

- `AgentState.replan_count` tracks the number of REPLAN decisions issued for the current task. The Orchestrator increments it after each REPLAN.
- `RuntimeConfig.max_replans` (default: 3) is the maximum number of replans allowed per task.
- The Orchestrator compares `AgentState.replan_count` against `RuntimeConfig.max_replans` before transitioning REPLANNING → OBSERVING. If `AgentState.replan_count > RuntimeConfig.max_replans`, the Orchestrator transitions REPLANNING → FAILED instead.
- The Orchestrator owns replan limit enforcement. No other component enforces this limit.
- Circular replanning (replanning back to a previous graph state) must be detected and prevented.
- The Orchestrator must never construct a Task Graph directly. All graph mutations go through `Planner.replan()`.

## ASK_USER Conditions

The ASK_USER decision is triggered when:

1. The Decision Engine determines that user input is required.
2. A tool requires user confirmation (policy rule).
3. The system encounters an ambiguous situation with no clear automated path forward.
4. A low-confidence decision cannot be resolved by re-querying.

ASK_USER must not be used as a substitute for proper decision-making. It is for genuine ambiguity or required user input only.

### ASK_USER Timeout

- ASK_USER has a configurable timeout (default: 300 seconds).
- If the user does not respond within the timeout:
  - If the task can continue without the input → OBSERVE with alternative path.
  - If the task cannot continue → FAIL with reason "user input timeout".

## WAIT Conditions

The WAIT decision is triggered when:

1. An external condition must be met before proceeding (e.g., a file appears, a process starts).
2. A rate limit requires a delay before the next action.

### WAIT Timeout

- WAIT has a configurable timeout.
- If the condition is not met within the timeout:
  - RETRY the last action (if the condition was transient).
  - Or issue REPLAN (Decision Engine reasons over the timeout context; Orchestrator calls `Planner.replan()`).
  - Or FAIL if no alternative exists.

## Loop Detection

The Orchestrator must detect and handle infinite loops:

1. If the same Decision is produced three consecutive times with the same result → escalate to REPLAN or FAIL.
2. If the Orchestrator cycles through the same Task Graph nodes without progress → escalate to REPLAN.
3. If replanning produces the same graph as a previous attempt → escalate to FAIL.

## Error Recording

All errors are recorded in AgentState.errors as ErrorRecord entries. Each record includes:
- Error code.
- Human-readable message.
- Whether the error is recoverable.
- The action that was being taken when the error occurred.
- Timestamp.

The error history is append-only. Errors are never removed.

## Constraints

1. Errors must never be silently swallowed. Every error is either recovered from, escalated, or recorded.
2. The retry limit is a hard ceiling. The Orchestrator must not exceed it.
3. Replanning must preserve completed nodes. Replanning does not restart the task from scratch.
4. The Orchestrator must always make forward progress. If stuck, it must escalate.
5. Error recovery must not create new errors. Recovery actions are themselves subject to policy validation.
