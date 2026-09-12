# Jarvis Desktop Agent

Desktop Agent modular monolith architecture adhering to the Canonical Architecture (V1 Spec).

## System Architecture

### 1. Modular Monolith Design (Section 1)
- **Single Process**: Runs as a single unified process with strict internal module boundaries.
- **Strict Ownership**: Each component has one distinct responsibility per Section 4; no component silently absorbs another's responsibility.
- **Closed Loop**: The core execution model is a closed loop, not a linear pipeline.

```
src/jarvis/
├── types.py            # Core shared types (RiskLevel, TaskLifecycle, PolicyDecision, etc.)
├── logger/             # [REAL] Event Logger (redaction, streaming, in-memory & file sinks)
├── tools/              # [REAL CONTRACT] Tool Registry contract, registry, and tool manager stub
├── orchestrator/       # [REAL LOOP] 11-step canonical loop explicit state machine & AgentOrchestrator
├── state/              # [STUB] State Manager (runtime task truth, lifecycle status)
├── observation/        # [STUB] Observation Manager (surface observation normalization)
├── verification/       # [STUB] Verification Engine (compares observation vs expected outcome)
├── policy/             # [STUB] Policy Engine (ALLOW / CONFIRM / DENY pass-through)
├── approval/           # [STUB] Approval Manager (human-in-the-loop interaction)
├── planner/            # [STUB] Planner (task graph generation)
├── intent/             # [STUB] Intent / Context Manager
├── profiler/           # [STUB] Task Profiler (task complexity/risk profile)
├── memory/             # [STUB] Memory / Conversation Manager
├── recovery/           # [STUB] Error / Recovery Manager (failure classification & recovery)
├── router/             # [STUB] LLM Router
├── resources/          # [STUB] Resource Manager
├── connectivity/       # [STUB] Connectivity Manager
├── vault/              # [STUB] Credential Vault
├── context_budget/     # [STUB] Context Budget Manager
└── response/           # [STUB] Response Manager
```

---

### 2. Tool Registry Contract (Section 11)
Every tool must declare an immutable contract (`ToolContract`) before registration:
- `name`: Unique tool name string.
- `description`: Human and LLM capability description.
- `input_schema`: JSON Schema dict of valid arguments.
- `output_schema`: JSON Schema dict of return data.
- `risk_level`: `RiskLevel.LOW`, `RiskLevel.MEDIUM`, or `RiskLevel.HIGH`.
- `reversible`: `bool` indicating if side effects can be reversed.
- `rollback_strategy`: String identifier of rollback mechanism (mandatory for `MEDIUM` risk).
- `timeout`: Positive float execution timeout in seconds.
- `idempotency`: `bool` indicating if repeated execution with same args is safe.
- `required_capabilities`: List of required system capabilities.
- `platform_support`: List of supported platforms (e.g. `["windows"]`).

**Guardrails enforced by contract validation (Section 7 & 11):**
- Any tool declared `reversible: False` must be `HIGH` risk.
- Any tool declared `MEDIUM` risk must declare `reversible: True` and declare a `rollback_strategy`.

---

### 3. Orchestrator 11-Step Loop (Section 2)
The canonical execution sequence is implemented as an explicit state machine (`CanonicalLoopStateMachine`):
1. **Check cancellation / deadline** (State Manager)
2. **Observe current state** (Observation Manager)
3. **Decide next action** (Orchestrator + Planner task graph + State)
4. **Policy check** (Policy Engine)
5. **Approval if required** (Approval Manager ↔ User)
6. **Dispatch action** (Tool Manager → Tool)
7. **Observe resulting state** (Observation Manager)
8. **Verify expected outcome** (Verification Engine)
9. **Update State** (State Manager)
10. **Log event** (Event Logger)
11. **Continue → retry → recover → replan → complete** (Orchestrator control flow)

Every step logs its own name through the Event Logger.

---

### 4. Event Logger (Section 13) — First Real Component
- Records structured `LogEvent`s tagged with `task_id`, `step_name`, `event_type`, and `timestamp`.
- **Sensitive Data Redaction Guarantee**: Automatically sanitizes keys and strings matching credentials, tokens, passwords, and API keys (`[REDACTED]`).
- **Live Streaming Subscribers**: Sinks/subscribers can be registered to stream logs in real-time (consumed by the UI log pane).
- **In-Memory Query Buffer & Sinks**: Queryable by `task_id`, `event_type`, or log level.

---

## Running the Hello Loop (Phase 0 Exit Criterion)

Execute the Phase 0 Hello Loop:
```bash
uv run python main.py
```

Run test suite:
```bash
uv run pytest -v
```
