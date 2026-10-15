# Data Contracts

This document defines the structured data contracts used for communication between components. All contracts are defined as schemas that must be validated at component boundaries.

## General Principles

- All inter-component data must conform to a defined contract.
- Contracts are validated at the receiving component's boundary.
- LLM-generated data (Decisions, Task Graphs) must pass schema validation.
- Tool results must be validated before being accepted into Agent State.
- A contract violation is an error condition handled by the Error Recovery process (ADR 11).

## ValidationResult

Returned by parameter validation on tools and inputs.

```
ValidationResult
├── valid: boolean              // Whether the input passed validation
├── errors: ValidationError[]   // List of validation errors (empty if valid)
└── warnings: string[]          // Non-blocking warnings
```

#### ValidationError

```
ValidationError
├── field: string          // The field that failed validation
├── message: string        // Human-readable description
└── code: string           // Machine-readable error code
```

## Policy Contracts

### PolicyResult

Returned by the Policy Engine's `validate()` method.

```
PolicyResult
├── approved: boolean          // Whether the action is approved
├── reason: string             // Explanation (especially for denials)
├── conditions: string[]       // Conditions attached to the approval (e.g., "read-only")
├── rule_triggers: string[]    // Which policy rules were evaluated
└── approval_token: string     // Token for approved actions (present when approved)
```

### ApprovalToken

```
ApprovalToken
├── token: string              // The approval token value
├── expires_at: DateTime       // When the token expires
├── conditions: string[]       // Conditions the approval is subject to
└── action_id: string          // The action this token authorizes
```

### DenialRecord

```
DenialRecord
├── action_id: string          // The action that was denied
├── reason: string             // Why the action was denied
├── triggered_rules: string[]  // Which rules caused the denial
└── timestamp: DateTime
```

## User I/O Contracts

### UserResponse

Returned by the user when responding to an ASK_USER decision.

```
UserResponse
├── response_id: string    // Links to the ASK_USER prompt
├── task_id: string        // The task this response belongs to
├── answer: string         // The user's answer text
├── selected_option: string // (Optional) if predefined options were offered
├── confirmed: boolean     // Whether the user confirmed or declined
└── timestamp: DateTime
```

### WaitCondition

Describes the condition a WAIT decision monitors.

```
WaitCondition
├── description: string    // Human-readable description of the condition
├── condition_type: string // "file_presence" | "process_start" | "time_delay" | "external_event"
├── parameters: object     // Condition-specific parameters
├── timeout_ms: number     // Maximum wait duration
└── poll_interval_ms: number // How often to check (if applicable)
```

## Core Types

### Request

Represents the structured output of the Input Processor.

```
Request
├── id: string              // Unique identifier for this request
├── raw_input: string        // Original user input text
├── normalized_input: string // Cleaned/normalized version
├── timestamp: DateTime      // When the request was created
└── metadata: object         // Optional metadata (future extensibility)
```

### Intent

Represents the classified and normalized intent derived by the Intent Manager. The Intent Manager takes Laya's raw classification and produces a validated, canonical intent representation. The Intent does not independently classify the request — it normalizes and enriches Laya's classification.

```
Intent
├── request_id: string           // Links back to the originating Request
├── laya_category: string        // Laya's raw category (e.g., "informational", "actionable", "query", "command")
├── normalized_form: string      // Canonical representation of the intent
├── entities: ExtractedEntity[]  // Validated and enriched entities (from LayaClassification)
├── constraints: string[]        // Identified constraints (refined from LayaClassification.characteristics)
├── confidence: number           // 0.0–1.0 — Intent Manager's confidence in the normalized form
├── ambiguous: boolean           // Whether the intent remains ambiguous after normalization
└── metadata: object             // Additional context from Intent Manager
```

### LayaClassification

Represents the output of Laya's classification step. Laya produces a raw classification of the user's request: its semantic intent category, extracted entities, confidence, and any ambiguity. Task complexity is not part of LayaClassification — that belongs to TaskProfile (from the Task Profiler).

```
LayaClassification
├── request_id: string        // Links back to the originating Request
├── category: string          // Semantic intent category (e.g., "informational", "actionable", "query", "command")
├── entities: ExtractedEntity[] // Entities extracted from the request
├── characteristics: string[] // Request characteristics (e.g., "multi-step", "external-data", "requires-confirmation")
├── confidence: number        // 0.0–1.0 classification confidence
├── ambiguous: boolean        // Whether the request is ambiguous
├── ambiguity_reason: string  // If ambiguous: why (null if not ambiguous)
└── metadata: object          // Additional classification details
```

#### ExtractedEntity

```
ExtractedEntity
├── type: string        // Entity type (e.g., "file_path", "app_name", "url", "person")
├── value: string       // The extracted entity value
├── confidence: number  // 0.0–1.0 extraction confidence
└── context: string     // Surrounding context from the request
```

### TaskProfile

Represents the output of the Task Profiler. Task complexity analysis lives here, not in LayaClassification.

```
TaskProfile
├── intent_id: string          // Links back to the Intent
├── task_type: string          // e.g., "single-step", "multi-step", "exploratory"
├── requirements: string[]     // What the task needs (tools, data, etc.)
├── constraints: string[]      // Task-specific constraints
├── complexity: string         // "low", "medium", "high" — Task Profiler's own assessment
├── estimated_steps: number    // Informational hint only. The Planner determines the actual step count.
├── prerequisites: string[]    // Conditions that must be met before execution
└── metadata: object           // Additional profiling details
```

### TaskGraph

Represents the execution strategy constructed by the Planner.

```
TaskGraph
├── id: string                    // Unique identifier for this graph
├── nodes: TaskGraphNode[]        // Ordered list of steps
├── edges: TaskGraphEdge[]        // Dependency relationships
├── entry_node_id: string         // ID of the first node to execute
└── metadata: object              // Graph-level metadata
```

#### TaskGraphNode

```
TaskGraphNode
├── id: string                  // Unique node identifier
├── type: string                // Action type (e.g., "tool_call", "observe", "ask_user")
├── description: string         // Human-readable description of this step
├── parameters: object          // Parameters for the action
├── expected_outcome: string    // What success looks like
├── retry_limit: number         // Maximum retry attempts (default: 3)
├── status: NodeStatus          // "pending", "active", "completed", "failed", "skipped"
└── result: object              // Execution result (populated after execution)
```

#### TaskGraphEdge

```
TaskGraphEdge
├── from: string  // Source node ID
├── to: string    // Target node ID
└── type: string  // "sequence" | "condition" | "alternative"
```

### AgentState

Represents the runtime state of a task execution.

```
AgentState
├── request: Request            // The original request
├── intent: Intent              // The classified intent
├── laya_classification: LayaClassification // Laya's classification
├── task_profile: TaskProfile   // Profiled task characteristics
├── task_graph: TaskGraph       // Current (possibly revised) task graph
├── execution_history: ExecutionStep[] // Record of all steps taken
├── current_step_id: string     // ID of the currently active node
├── status: TaskStatus          // Overall task status
├── observations: Observation[] // Collected observations
├── errors: ErrorRecord[]       // Error history
├── retry_count: number         // Authoritative runtime retry counter for the current node (Orchestrator-incremented)
├── replan_count: number        // Number of REPLAN decisions issued for this task
└── metadata: object            // Additional runtime data
```

#### ExecutionStep

```
ExecutionStep
├── step_number: number         // Sequential step number
├── node_id: string             // Task Graph node that was executed
├── decision: Decision          // The Decision that triggered this step
├── action: string              // What was done
├── observation: Observation    // Result of the action
├── verification: VerificationResult // Outcome of verification
├── timestamp: DateTime         // When this step occurred
└── duration_ms: number         // How long the step took
```

#### Observation

```
Observation
├── source: string            // What produced this observation (tool, user, system)
├── data: object              // The observed data
├── success: boolean          // Whether the action succeeded
├── error: ErrorRecord        // Error details if not successful
└── timestamp: DateTime
```

#### VerificationResult

```
VerificationResult
├── passed: boolean           // Whether verification succeeded
├── expected: object          // What was expected
├── actual: object            // What was observed
├── discrepancy: string       // Human-readable description if failed
└── severity: string          // "none" | "warning" | "error"
```

#### ErrorRecord

```
ErrorRecord
├── code: string              // Error code
├── message: string           // Human-readable description
├── recoverable: boolean      // Whether retry/recovery is possible
├── context: object           // Additional error context
└── timestamp: DateTime
```

### Decision

Represents the structured output of the Decision Engine. The Decision is the central control signal of the system.

```
Decision
├── id: string                // Unique decision identifier
├── type: DecisionType        // One of eight types — determines required parameters
├── reasoning: string         // LLM's reasoning for this decision
├── parameters: object        // Decision-type-specific parameters (see discriminated union below)
├── target_node_id: string    // Denormalized convenience copy of the target node identifier. For EXECUTE and RETRY, the corresponding decision parameter model's target_node_id is authoritative; this top-level field must not override it. No schema-level cross-field consistency rule is currently enforced.
├── confidence: number        // 0.0–1.0
├── retry_count: number       // Decision Engine's reasoning about the current retry attempt (1-indexed). AgentState.retry_count is authoritative — the Orchestrator must not trust this field over AgentState.retry_count.
└── timestamp: DateTime
```

### DecisionType (enum)

```
EXECUTE    | OBSERVE   | REPLAN    | RETRY
ASK_USER   | WAIT      | COMPLETE  | FAIL
```

### Decision Parameters — Discriminated Union

The `parameters` field's shape is determined by `Decision.type`. Schema validation must reject a `Decision` whose `parameters` are missing required fields for its type. The table below defines the contract for each type.

| Field | EXECUTE | OBSERVE | REPLAN | RETRY | ASK_USER | WAIT | COMPLETE | FAIL |
|---|---|---|---|---|---|---|---|---|
| `target_node_id` | **required** | — | — | **required** | — | — | — | — |
| `tool_params` | optional | — | — | optional | — | — | — | — |
| `observation_target` | — | optional | — | — | — | — | — | — |
| `observation_params` | — | optional | — | — | — | — | — | — |
| `replan_reason` | — | — | **required** | — | — | — | — | — |
| `preserve_completed` | — | — | optional | — | — | — | — | — |
| `adjusted_params` | — | — | — | optional | — | — | — | — |
| `retry_count` | — | — | — | **required** | — | — | — | — |
| `question` | — | — | — | — | **required** | — | — | — |
| `options` | — | — | — | — | optional | — | — | — |
| `required` | — | — | — | — | optional | — | — | — |
| `condition` | — | — | — | — | — | **required** | — | — |
| `timeout_ms` | — | — | — | — | — | **required** | — | — |
| `summary` | — | — | — | — | — | — | optional | — |
| `result` | — | — | — | — | — | — | optional | — |
| `reason` | — | — | — | — | — | — | — | **required** |
| `error` | — | — | — | — | — | — | — | optional |

**Rejection examples (must be caught by schema validation):**

```json
{ "type": "EXECUTE", "parameters": {} }
// REJECTED: target_node_id is required for EXECUTE

{ "type": "ASK_USER", "parameters": {} }
// REJECTED: question is required for ASK_USER

{ "type": "FAIL", "parameters": {} }
// REJECTED: reason is required for FAIL
```

The schema validator checks that `parameters` contains all required fields for the given `type` and ignores fields that belong to other types.

### TaskStatus (enum)

```
PENDING       | OBSERVING  | DECIDING   | EXECUTING
VERIFYING     | REPLANNING | AWAITING   | COMPLETED
FAILED        | CANCELLED
```

### NodeStatus (enum)

```
PENDING  | ACTIVE  | COMPLETED  | FAILED  | SKIPPED  | RETRYING
```

## Validation Rules

| Contract | When Validated | On Failure |
|---|---|---|
| Request | Input Processor output | Return error to user |
| Intent | Intent Manager normalization output | Fallback to default intent normalization |
| LayaClassification | Laya output | Treat as low-confidence classification |
| TaskProfile | Task Profiler output | Abort — cannot plan without a profile |
| TaskGraph | Planner output | Abort — cannot execute without a plan |
| Decision | Decision Engine output | Re-query the Decision Engine |
| ToolResult | Tool Manager output | Handle via Error Recovery (ADR 11) |

## Schema Format

Schemas are defined in `schemas/` as JSON Schema documents. Each schema file corresponds to one contract type and is named after the type (e.g., `schemas/request.json`, `schemas/decision.json`).

Schema validation is performed at every component boundary. Components must not accept data that does not conform to the expected schema.

## Runtime Configuration

Runtime configuration defines limits that control behavior at the Orchestrator level. These are not task-specific — they apply to every task execution.

```
RuntimeConfig
├── max_retries: number       // Maximum retries per node (default: 3)
├── max_replans: number       // Maximum replans per task (default: 3)
└── global_timeout_ms: number // Maximum task/runtime duration in milliseconds (optional, default: no limit)
```

### RuntimeConfig Field Contract

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `max_retries` | number | yes | 3 | Maximum number of RETRY decisions for a single node. |
| `max_replans` | number | yes | 3 | Maximum number of REPLAN decisions for a single task. |
| `global_timeout_ms` | number | no | — | Maximum task execution duration in milliseconds. This is a per-task limit, distinct from the per-decision `timeout_ms` used by WAIT decisions. Enforcement of this limit is deferred to a future implementation phase.

The Orchestrator owns enforcement of RuntimeConfig limits. The Orchestrator:
- Increments `AgentState.retry_count` after each RETRY and compares it to `RuntimeConfig.max_retries`.
- Increments `AgentState.replan_count` after each REPLAN and compares it to `RuntimeConfig.max_replans`.
- When `AgentState.replan_count > RuntimeConfig.max_replans`, the Orchestrator transitions to FAILED instead of REPLANING.
- When `AgentState.retry_count > RuntimeConfig.max_retries`, the Orchestrator transitions to FAILED instead of EXECUTING.

No other component enforces these limits.
