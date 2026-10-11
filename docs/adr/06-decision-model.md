# Decision Model

## Overview

The Decision Engine produces structured `Decision` objects that direct the Agent Orchestrator's next action. There are eight possible decision types, each with defined preconditions, actions, and outcomes.

## Decision Types

### EXECUTE

**Purpose:** Execute the next planned action in the Task Graph.

**Preconditions:**
- The current Task Graph node is in PENDING status.
- The node's prerequisites (dependencies) are all COMPLETED.
- The Policy Engine approves the action.

**Action:** The Orchestrator invokes the tool specified by the current Task Graph node through the Tool Manager.

**Outcome:**
- Success → moves to VERIFYING.
- Failure → may trigger RETRY or FAIL depending on recoverability.

**Parameters** (see ADR 04 — Decision parameters discriminated union):

| Parameter | Required | Description |
|---|---|---|
| `target_node_id` | yes | The Task Graph node to execute. |
| `tool_params` | no | Parameters to pass to the tool. |

---

### OBSERVE

**Purpose:** Gather additional information without executing a tool action.

**Preconditions:**
- Additional information is needed before proceeding.
- The current state does not have sufficient data to make a better decision.

**Action:** The Orchestrator performs an observation action (e.g., reading current state, querying a data source through a mock).

**Outcome:**
- Observation result is added to AgentState.
- Loop returns to DECIDING with updated state.

**Parameters** (see ADR 04 — Decision parameters discriminated union):

| Parameter | Required | Description |
|---|---|---|
| `observation_target` | no | What to observe. |
| `observation_params` | no | Parameters for the observation. |

---

### REPLAN

**Purpose:** Revise the Task Graph in response to changed circumstances.

**Preconditions:**
- Current plan is no longer valid or optimal.
- New information has changed the task requirements.
- A previous step failed and the current graph cannot proceed.

**Action:** The Orchestrator calls `Planner.replan()` with the current Task Graph, Agent State, `replan_reason`, and `preserve_completed`. The Planner returns a revised Task Graph. The Orchestrator validates it via `Planner.validate()` and updates Agent State.

**Outcome:**
- New Task Graph is validated.
- Loop returns to OBSERVING with the new graph.

**Parameters** (see ADR 04 — Decision parameters discriminated union):

| Parameter | Required | Description |
|---|---|---|
| `replan_reason` | yes | Why replanning is needed. |
| `preserve_completed` | no | Whether to keep completed nodes (default: true). |

---

### RETRY

**Purpose:** Repeat the last failed action.

**Preconditions:**
- The previous step failed.
- The failure is recoverable.
- `AgentState.retry_count` is below the retry limit. (The Orchestrator enforces this — `AgentState.retry_count` is authoritative, not `Decision.parameters.retry_count`.)

**Action:** The Orchestrator re-invokes the last tool/action, optionally with adjusted parameters.

**Outcome:**
- Success → moves to VERIFYING.
- Failure (retry exhausted) → escalates to FAIL or REPLAN.

**Parameters** (see ADR 04 — Decision parameters discriminated union):

| Parameter | Required | Description |
|---|---|---|
| `target_node_id` | yes | The node to retry. |
| `adjusted_params` | no | Modified parameters for the retry. |
| `retry_count` | yes | Current retry attempt number (1-indexed) — the Decision Engine's reasoning about the attempt. AgentState.retry_count is authoritative for enforcement. |

---

### ASK_USER

**Purpose:** Request additional input or confirmation from the user.

**Preconditions:**
- The system cannot proceed without user input.
- The question is well-defined and can be presented to the user.

**Action:** The Orchestrator pauses execution and presents a question or confirmation to the user. Execution resumes when the user responds.

**Outcome:**
- User provides input → input is added as an observation; loop returns to DECIDING.
- User declines/cancels → escalates to FAIL.

**Parameters** (see ADR 04 — Decision parameters discriminated union):

| Parameter | Required | Description |
|---|---|---|
| `question` | yes | The question or prompt for the user. |
| `options` | no | Predefined response options. |
| `required` | no | Whether a response is mandatory (default: true). |

---

### WAIT

**Purpose:** Pause execution for an external condition.

**Preconditions:**
- An external condition must be met before proceeding.
- A timeout is defined.

**Action:** The Orchestrator pauses and monitors for the condition. Execution resumes when the condition is met or the timeout expires.

**Outcome:**
- Condition met → loop returns to OBSERVING.
- Timeout → escalates to FAIL or RETRY.

**Parameters** (see ADR 04 — Decision parameters discriminated union):

| Parameter | Required | Description |
|---|---|---|
| `condition` | yes | Description of the condition to wait for. |
| `timeout_ms` | yes | Maximum wait duration in milliseconds. |

---

### COMPLETE

**Purpose:** Signal successful task completion.

**Preconditions:**
- All required Task Graph nodes are COMPLETED.
- Verification has confirmed the final outcome.
- No remaining work is pending.

**Action:** The Orchestrator terminates the agentic loop. The final result is produced.

**Outcome:**
- Loop terminates. AgentState.status = COMPLETED.

**Parameters** (see ADR 04 — Decision parameters discriminated union):

| Parameter | Required | Description |
|---|---|---|
| `summary` | no | Description of the completed task. |
| `result` | no | Final result data. |

---

### FAIL

**Purpose:** Signal that the task cannot be completed.

**Preconditions:**
- All retry attempts exhausted.
- Replanning has been attempted and failed.
- The error is not recoverable.
- The user has declined to proceed (for ASK_USER).

**Action:** The Orchestrator terminates the agentic loop. The failure is recorded.

**Outcome:**
- Loop terminates. AgentState.status = FAILED.
- Error details are recorded in AgentState.errors.

**Parameters** (see ADR 04 — Decision parameters discriminated union):

| Parameter | Required | Description |
|---|---|---|
| `reason` | yes | Why the task failed. |
| `error` | no | ErrorRecord describing the failure. |

---

## Decision Validation

Decision validation happens in two phases across two components.

### Phase 1 — Structural Validation (Decision Engine)

The Decision Engine validates its own output before returning it to the Orchestrator:

1. **Schema validation** — the Decision conforms to the Decision schema (ADR 04).
2. **Parameter contract validation** — the Decision's `parameters` contain all required fields for its `DecisionType` per the discriminated union in ADR 04.

The Decision Engine does not have access to AgentState for contextual checks. It does not perform policy validation. It returns the Decision if structural validation passes, or re-queries the LLM if the output is malformed.

### Phase 2 — Contextual and Policy Validation (Agent Orchestrator)

After receiving a structurally valid Decision, the Orchestrator performs:

1. **Contextual state validation** — the Decision is checked against the current AgentState:
   - For EXECUTE: the target node exists and is PENDING; all dependencies are COMPLETED.
   - For RETRY: the target node has remaining retries within its retry limit.
   - For REPLAN: the current graph has at least one non-terminal node; the replan limit has not been exceeded.
   - For COMPLETE: all required nodes are COMPLETED.
   - For FAIL: the failure reason is valid.

2. **Policy validation** — the Orchestrator invokes the Policy Engine to approve or deny the proposed action (see ADR 09 — Security and Policy).

If contextual or policy validation fails, the Orchestrator rejects or transforms the Decision (re-queries the Decision Engine, issues a safer Decision type, or escalates to FAIL).

## Decision Confidence

Each Decision carries a confidence score (0.0–1.0) from the LLM. Low-confidence decisions (below a configurable threshold) trigger additional scrutiny:
- The Orchestrator may re-query the Decision Engine.
- The Orchestrator may issue an ASK_USER decision for human confirmation.
- The Policy Engine may impose stricter checks.
