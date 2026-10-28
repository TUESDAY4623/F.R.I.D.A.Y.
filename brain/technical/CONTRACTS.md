# CONTRACTS — Groups, Schemas, Validation, Generation

> Authoritative definitions live in the models
> (`src/jarvis/contracts/models/`) and the generated JSON schemas
> (`schemas/`). This document explains and inventories; it deliberately does
> not duplicate field tables — ADR 04 (docs/adr/04-data-contracts.md) is the
> narrative source, the models are the machine source.

Last verified: commit `c5db884` (PR #2, contract freeze).

## 1. Design rules

- Contracts are **Pydantic models**; JSON schemas are **generated** from them
  — never hand-maintained. Generator: `scripts/generate_schemas.py`.
- All models extend `JarvisBaseModel`
  (`src/jarvis/contracts/models/base.py`) with: `str_strip_whitespace=True`,
  `validate_assignment=True`, `extra="forbid"`.
- Schemas are validated at every component boundary (ADR 04 §Validation
  Rules); LLM outputs (Decisions, TaskGraphs) must pass schema validation.
- **Verification performed:** running `python scripts/generate_schemas.py`
  regenerates all 48 schema files with **zero diff** against the committed
  `schemas/` (working tree stays clean), confirming models ↔ schemas are in
  sync at `c5db884`.

## 2. Contract groups

| Group | Module | Contracts (public) |
|---|---|---|
| A — request & understanding | `group_a.py` | `Request`, `LayaClassification`, `Intent`, `ExtractedEntity`, enums `EntityType` (12 values), `RequestCharacteristic` (7), `LayaCategory` (4) |
| B — task-understanding | `group_b.py` | `TaskProfile`, `TaskGraph`, `TaskGraphNode`, `TaskGraphEdge`, enums `TaskType`, `Complexity`, `NodeStatus`, `EdgeType` |
| C — agent runtime & decisions | `group_c.py` | `AgentState`, `ExecutionStep`, `Observation`, `VerificationResult`, `ErrorRecord`, `RuntimeConfig`, all 8 decision variants (`ExecuteDecision` … `FailDecision`) with their `*Params`, discriminated union `AnyDecision`/`AnyDecisionUnion` + `DECISION_ADAPTER`, enums `DecisionType`, `TaskStatus` |
| D — execution boundary | `group_d.py` | `ProposedAction`, `ToolResult`, `PolicyResult`, `ValidationResult`, `ValidationError_` |
| E — user interaction | `group_e.py` | `UserResponse`, `WaitCondition`, `WaitConditionType` |

## 3. Schemas

- **48 JSON Schema files** in `schemas/`, one per contract plus 10 enum
  schemas (e.g., `schemas/decision.json`, `schemas/agent-state.json`,
  `schemas/entity-type.json`).
- `schemas/decision.json` is generated from `DECISION_ADAPTER`
  (annotated discriminated union) so the `oneOf` + `type` discriminator is
  derived from the models.
- Frozen at `c5db884` (PR #2 added `policy-result`, `proposed-action`,
  `tool-result`, `user-response`, `wait-condition` + clarifications).

## 4. Validation & testing

- 431 tests (local run, no CI): unit + schema-alignment tests in
  `tests/contracts/test_group_{a..e}.py` plus `test_group_a_schemas.py`.
  See [TESTING.md](TESTING.md).
- Field-level contracts (e.g., `UserResponse.timestamp`,
  `ToolResult.duration_ms`) were clarified in ADR 04 at `ac66b2a` (PR #2).

## 5. Naming notes (do not "fix" these)

- `ValidationError_` (trailing underscore) in Group D: the name
  `ValidationError` collides with Pydantic's built-in; the model therefore
  uses the underscore-suffixed Python name while its **schema title remains
  `ValidationError`** (`ValidationError_.model_config["title"]`,
  `group_d.py` lines 73–76). This is intentional and tested.
- `src/jarvis/contracts/models/__init__.py` re-exports **only Groups D+E**
  while `src/jarvis/contracts/__init__.py` exports all five groups. This split
  dates from the per-group commit hygiene used to merge Phase 1 incrementally
  (Groups B/C in one PR, D/E in another) and is deliberate, not an
  oversight. If you need a specific contract, import from
  `jarvis.contracts` (top-level) — that is the public surface.

## 6. Known minor gap (unverified as intentional)

- `pyproject.toml` contains a `[tool.pydantic-models]` table whose only
  content is the comment `# Used by schema generation script`. The generator
  reads models directly and does **not** read this table. It is harmless but
  confusing; leaving it as-is was out of scope for a documentation-only pass.
