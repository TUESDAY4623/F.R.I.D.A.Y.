# Agentic Workflow

## The Agentic Control Loop

The fundamental execution loop for every task:

```
OBSERVE → DECIDE → ACT → OBSERVE RESULT → VERIFY → UPDATE STATE → DECIDE AGAIN
```

Each step is described below.

### 1. OBSERVE

The Agent Orchestrator collects the current state of the world:
- Reads the current `AgentState` (current step, execution history, status).
- Identifies the active Task Graph node and its prerequisites.
- Gathers any available observations from previous steps.

No new data is fetched during OBSERVE. The Orchestrator reads existing state.

### 2. DECIDE

The Orchestrator passes the current Agent State to the Decision Engine.

The Decision Engine:
- Reasons over the current state using an LLM.
- Produces a structured `Decision`.
- The Decision is one of eight types (see ADR 06).

After the Decision Engine returns, the Orchestrator performs three validation layers:

1. **Structural validation** — the Decision Engine has already validated the Decision against the Decision schema (ADR 04) and the discriminated parameter contract for its type. The Orchestrator trusts this structural validation unless the Decision is malformed in an obvious way (wrong `type` value, missing `id`).

2. **Contextual state validation** — the Orchestrator checks whether the Decision is valid in the current AgentState:
   - For EXECUTE: the target node exists and is PENDING; all dependencies are COMPLETED.
   - For RETRY: the target node has remaining retries. `AgentState.retry_count` is authoritative — the Orchestrator must not rely on `Decision.parameters.retry_count` for limit checks. The Orchestrator increments `AgentState.retry_count` after each RETRY.
   - For REPLAN: the current graph has at least one non-terminal node; the replan limit has not been exceeded.
   - For COMPLETE: all required nodes are COMPLETED.
   - For FAIL: the failure reason is valid.

3. **Policy validation** — the Orchestrator invokes the Policy Engine to approve or deny the proposed action.

If any validation layer fails, the Orchestrator rejects or transforms the Decision (re-queries the Decision Engine, issues a safer Decision type, or escalates to FAIL).

### 3. ACT

The Orchestrator executes the validated Decision:

- **EXECUTE** — invokes the corresponding tool through the Tool Manager interface. The tool operates on the current Task Graph node.
- **OBSERVE** — initiates an information-gathering action (e.g., reading a file, querying a knowledge source).
- **REPLAN** — invokes `Planner.replan()` to obtain a revised Task Graph. The Orchestrator never constructs graph structure itself.
- **RETRY** — re-invokes the last tool/action with the same or adjusted parameters.
- **ASK_USER** — pauses execution and presents a question or confirmation request to the user.
- **WAIT** — pauses execution and waits for an external condition.
- **COMPLETE** — terminates the loop with success.
- **FAIL** — terminates the loop with failure.

Tool execution goes through the Tool Manager interface. In the current milestone, the Tool Manager is a deterministic mock.

### 4. OBSERVE RESULT

After ACT, the Orchestrator collects the result:
- Tool execution result (output data, success/failure status).
- User response (for ASK_USER decisions).
- New Task Graph (for REPLAN decisions).
- Confirmation (for WAIT condition resolution).

### 5. VERIFY

The Orchestrator checks whether the observed result matches expectations:
- For EXECUTE: does the tool result match the expected outcome of the current Task Graph node?
- For OBSERVE: does the gathered information satisfy the information need?
- For REPLAN: is the new Task Graph valid and internally consistent?
- For RETRY: did the retry succeed where the original attempt failed?
- For ASK_USER: was a valid response received?
- For WAIT: did the expected condition occur?

Verification criteria are defined in the Task Graph node specification.

### 6. UPDATE STATE

The Orchestrator updates the Agent State:
- Records the observation in the execution history.
- Updates the current Task Graph node status.
- Updates the overall task status.
- Records the Decision and its outcome.
- If the task is COMPLETE or FAIL, transitions to the terminal state.

### 7. DECIDE AGAIN

The loop repeats. The Orchestrator calls the Decision Engine again with the updated Agent State.

## Loop Termination

The loop terminates when:
- The Decision Engine produces a **COMPLETE** decision and verification succeeds.
- The Decision Engine produces a **FAIL** decision.
- An unrecoverable error occurs (see ADR 11 — Error Recovery).
- The user explicitly cancels the task (future).

## Replanning

When a REPLAN decision is issued:

1. The Orchestrator checks `AgentState.replan_count` against `RuntimeConfig.max_replans` (default: 3). If `AgentState.replan_count > RuntimeConfig.max_replans`, the Orchestrator issues FAIL instead of REPLAN. The Orchestrator does not call `Planner.replan()` in this case.
2. The Orchestrator calls `Planner.replan()`, passing the current Task Graph, current Agent State, the replan reason (from `Decision.parameters.replan_reason`), and `preserve_completed` (from `Decision.parameters.preserve_completed`, default true).
3. The Planner returns a revised Task Graph. COMPLETED nodes are preserved. PENDING and FAILED nodes may be modified, added, or removed.
4. The Orchestrator validates the revised Task Graph via `Planner.validate()`.
5. The Orchestrator increments `AgentState.replan_count`.
6. The Orchestrator updates Agent State with the revised Task Graph. The execution history is preserved.
7. The loop continues from OBSERVE with the new graph.

Replanning does not reset the entire task. Existing observations and completed steps remain in the execution history.

The Orchestrator must never construct or mutate Task Graph structure directly. All graph mutations go through the Planner.

## Retry

When a RETRY decision is issued:
1. The Orchestrator re-invokes the last tool/action.
2. Retry count for the current step is incremented in Agent State.
3. If retry exceeds the configured maximum, the Orchestrator does not issue another RETRY. It escalates to FAIL or issues REPLAN.

## ASK_USER

When an ASK_USER decision is issued:
1. The Orchestrator pauses execution.
2. The user is presented with the question or confirmation request.
3. The user's response is captured.
4. The response is added to Agent State as an observation.
5. The loop continues from DECIDE.

## WAIT

When a WAIT decision is issued:
1. The Orchestrator pauses execution.
2. The Orchestrator waits for the specified external condition.
3. When the condition is met, the loop continues from OBSERVE.
4. If the wait times out, the Orchestrator escalates to FAIL or issues a RETRY decision.

## Constraints

1. The Orchestrator must never skip OBSERVE and go directly to DECIDE.
2. The Orchestrator must never skip VERIFY after ACT.
3. The Orchestrator must never execute tools without a validated Decision.
4. The Orchestrator must never construct or mutate Task Graph structure directly — all graph mutations go through `Planner.replan()`.
5. The Orchestrator must never exceed the retry limit or replan limit for a task. When a limit is reached, the Orchestrator must escalate to FAIL.
6. Agent State must be updated atomically — partial state updates are not allowed.
7. The loop must always make progress. If the same Decision is produced twice with the same result, the Orchestrator must detect the loop and escalate.
