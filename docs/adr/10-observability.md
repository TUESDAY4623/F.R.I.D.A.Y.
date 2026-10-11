# Observability

## Overview

The system must be observable during execution. This document defines what is logged, what is traced, and what the debugging model looks like during agentic execution.

## Observability Events

The Agent Orchestrator emits structured observability events at key points in the agentic loop. Events are structured records with a type, timestamp, and payload.

### Event Types

| Event Type | Emitted When | Payload |
|---|---|---|
| `task.started` | A new task execution begins | Request ID, Intent, Task Graph summary |
| `task.completed` | A task reaches COMPLETED | Final status, step count, duration |
| `task.failed` | A task reaches FAILED | Failure reason, step count, error details |
| `loop.observe` | OBSERVE step begins | Current step ID, AgentState status |
| `loop.decide` | DECIDE step begins | Current AgentState snapshot (summary) |
| `loop.act` | ACT step begins | Decision type, target node ID |
| `loop.observe_result` | OBSERVE RESULT step begins | Tool/invocation result (summary) |
| `loop.verify` | VERIFY step begins | Expected vs. actual comparison |
| `loop.update_state` | UPDATE STATE step completes | State changes made |
| `decision.produced` | Decision Engine returns a Decision | Decision type, confidence, reasoning |
| `decision.validated` | Decision passes validation | Validation result |
| `decision.rejected` | Decision fails validation | Rejection reason |
| `tool.invoked` | A tool is called | Tool name, parameters, node ID |
| `tool.result` | A tool returns a result | Success/failure, duration |
| `policy.approved` | Policy Engine approves an action | Action, rule triggers |
| `policy.denied` | Policy Engine denies an action | Action, denial reason |
| `replan.triggered` | A REPLAN decision is executed | Reason, graph changes, current replan_count |
| `replan.limit_exceeded` | replan_count exceeds max_replans | Current replan_count, max_replans, task transitions to FAILED |
| `retry.triggered` | A RETRY decision is executed | Node ID, current retry_count |
| `retry.limit_exceeded` | retry_count exceeds max_retries | Current retry_count, max_retries, action taken (REPLAN or FAIL) |
| `ask_user.prompted` | An ASK_USER decision is presented | Question, options |
| `ask_user.responded` | User provides input to ASK_USER | Response received |
| `wait.started` | A WAIT decision begins waiting | Condition, timeout |
| `wait.resolved` | A WAIT condition is met | Resolution details |
| `error.recoverable` | A recoverable error occurs | Error details, recovery action |
| `error.unrecoverable` | An unrecoverable error occurs | Error details, escalation |

## Logging Format

All observability events use a structured format. The exact serialization format is determined by the implementation, but each event must include:

- `event_type`: string — one of the event types listed above
- `timestamp`: DateTime — when the event occurred
- `task_id`: string — the unique task identifier
- `step_number`: number — the current step number in the execution loop
- `payload`: object — event-specific data (types defined in ADR 04)

Event payloads may carry contracts defined in ADR 04: `Decision` (for `decision.produced`), `PolicyResult` (for `policy.approved` / `policy.denied`), `UserResponse` (for `ask_user.responded`), `ToolResult` (for `tool.result`), `WaitCondition` (for `wait.started`), `ErrorRecord` (for `error.recoverable` / `error.unrecoverable`).

## Trace Correlation

Each task execution has a unique `task_id`. All events emitted during a single task execution carry the same `task_id`. This enables:
- Tracing a complete task execution from start to finish.
- Correlating events across components.
- Debugging by filtering on a single task_id.

Step numbers increment monotonically within a task execution, starting from 0.

## Debugging Model

### Step-Level Debugging

The execution history (AgentState.execution_history) provides a complete record of every step taken during a task. Each step records:
- The step number.
- The Task Graph node that was executed.
- The Decision that triggered the step.
- The Observation (result).
- The VerificationResult.
- Timestamp and duration.

### State Snapshots

At each DECIDE step, the Decision Engine receives the current AgentState. In debug mode, a snapshot of the state can be captured and inspected.

### Decision Audit Trail

Every Decision produced by the Decision Engine is recorded with:
- The Decision content.
- The reasoning provided by the LLM.
- The confidence score.
- The validation result (schema, state, policy).
- The final outcome (acted upon, rejected, escalated).

### Tool Call Log

Every tool invocation is recorded with:
- Tool name and parameters.
- Execution context.
- Result (success, failure, data).
- Duration.

## Log Levels

| Level | Purpose |
|---|---|
| `debug` | Detailed internal state, LLM prompts and responses, parameter values |
| `info` | High-level flow events (loop steps, decisions, tool calls) |
| `warn` | Recoverable errors, policy warnings, low-confidence decisions |
| `error` | Unrecoverable errors, policy denials, task failures |

## Constraints

1. No sensitive data (credentials, personal information) may be logged at `debug` or `info` level.
2. Sensitive parameters must be redacted before logging.
3. LLM prompts and responses must be logged at `debug` level for debugging but must not include sensitive data.
4. Observability events must be non-blocking — logging failures must not affect execution flow.
5. The observability system must not modify AgentState.
