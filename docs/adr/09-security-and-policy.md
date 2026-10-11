# Security and Policy

## Overview

The Policy Engine is a downstream interface that validates actions against security and policy rules before execution. In the current milestone, the Policy Engine is represented as an interface with a deterministic mock implementation.

## Policy Engine Interface

```
IPolicyEngine
├── validate(action: ProposedAction, context: ExecutionContext): PolicyResult    // (see ADR 04)
├── approve(action: ProposedAction): ApprovalToken                                // (see ADR 04)
├── deny(action: ProposedAction, reason: string): DenialRecord                    // (see ADR 04)
└── rules: PolicyRule[]            // Active policy rules (read-only)
```

### ProposedAction

```
ProposedAction
├── action_type: string       // Type of action (e.g., "tool_call", "file_read", "browser_navigate")
├── tool_name: string         // Which tool would be invoked
├── parameters: object        // The proposed parameters
├── agent_state: AgentState   // Current state at time of proposal — (see ADR 04)
├── task_graph_node_id: string // Which Task Graph node this serves
└── timestamp: DateTime
```

### PolicyResult

```
PolicyResult
├── approved: boolean         // Whether the action is approved
├── reason: string            // Explanation (especially for denials)
├── conditions: string[]      // Conditions attached to the approval (e.g., "read-only")
├── rule_triggers: string[]   // Which policy rules were evaluated
└── approval_token: string    // Token for approved actions (present when approved)
```

All PolicyResult field types are formally defined in ADR 04.

### PolicyRule

```
PolicyRule
├── id: string                // Unique rule identifier
├── name: string              // Human-readable rule name
├── description: string       // What the rule enforces
├── action_types: string[]    // Which action types this rule applies to
├── condition: string         // Rule condition (structured, evaluable)
├── severity: string          // "info" | "warning" | "deny"
└── enabled: boolean          // Whether the rule is active
```

### ApprovalToken

```
ApprovalToken
├── token: string              // The approval token value
├── expires_at: DateTime       // When the token expires
├── conditions: string[]       // Conditions the approval is subject to
└── action_id: string          // The action this token authorizes
```

Returned by `IPolicyEngine.approve()`. Formally defined in ADR 04.

### DenialRecord

```
DenialRecord
├── action_id: string          // The action that was denied
├── reason: string             // Why the action was denied
├── triggered_rules: string[]  // Which rules caused the denial
└── timestamp: DateTime
```

Returned by `IPolicyEngine.deny()`. Formally defined in ADR 04.

## Policy Check Points

1. **Before tool execution** — when the Orchestrator issues an EXECUTE decision, the proposed action is validated before the tool is invoked.
2. **Before REPLAN** — when the Orchestrator issues a REPLAN decision, the proposed new Task Graph is validated.
3. **Before ASK_USER** — when the Orchestrator presents a question to the user, the question content is validated.
4. **Decision-level validation** — as part of the Orchestrator's contextual validation (see ADR 06), the Orchestrator invokes the Policy Engine to check the proposed action against active policy rules. The Decision Engine does not perform policy validation.

## Policy Evaluation Flow

```
Orchestrator proposes action
    │
    ▼
Policy Engine evaluates against active rules
    │
    ├── All rules pass → APPROVED → action proceeds
    ├── Warning-level rule triggered → APPROVED with conditions → action proceeds with conditions logged
    └── Deny-level rule triggered → DENIED → action blocked, error recorded
```

## Default Policy Rules (Mock)

The mock Policy Engine includes the following default rules:

| Rule | Severity | Description |
|---|---|---|
| `no-destructive-tools-without-confirmation` | deny | Tools that delete or modify data require ASK_USER |
| `no-external-network` | deny | Tools that access external networks are blocked |
| `rate-limit-tool-calls` | warning | More than 10 tool calls in 60 seconds triggers a warning |
| `require-confirmation-for-system-changes` | deny | System-level changes require user confirmation |

These rules are configurable. The mock implementation uses them as defaults.

## Security Constraints

1. No action may be executed without passing the Policy Engine check.
2. The Policy Engine check is not bypassable by the Orchestrator.
3. Policy decisions are logged in the execution history.
4. Denied actions are recorded as errors in AgentState.
5. The Policy Engine must not modify AgentState — it only evaluates and returns decisions.
6. Policy rules are read-only during task execution (no dynamic rule changes mid-task).
7. The mock Policy Engine must simulate both approval and denial scenarios for testing.
