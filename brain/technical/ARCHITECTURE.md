# ARCHITECTURE — Current Intended Design

> Scope: this document describes the **intended** architecture of the current
> (post-reset) codebase, as defined by `CLAUDE.md` and `docs/adr/00`–`13`.
> Nothing here claims a component is implemented — see
> [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) for what actually exists.
> Claim classes used throughout: **Implemented**, **Verified**, **Planned**,
> **Historical**, **Unknown/Unverified** (defined in [README.md](README.md)).

Last verified: commit `c5db884` (2026-10-28, PR #2 merge).

---

## 1. Purpose

Jarvis is an agentic desktop AI system: it accepts a natural-language request,
understands the intent, profiles and plans the task, then executes a sequence of
actions through an agentic control loop that observes results, verifies
outcomes, and adapts (ADR 00 §Purpose).

## 2. Pipeline and milestone boundary

The current milestone implements the pipeline up to and including the
**Agent Orchestrator**:

```
User Input → Input Processor → Laya → Intent Manager → Task Profiler
           → Planner → Agent State → Decision Engine → Agent Orchestrator
```

Everything downstream of that boundary (Policy Engine, Tool Manager, browser /
Windows / file-system tools, Vision, real-world execution) is represented in
this milestone only as **interfaces and deterministic mocks** (ADR 00 §Current
Implementation Boundary, ADR 01 §Downstream Systems). This is a design rule,
not an implementation status.

## 3. Component boundaries

Nine components, each with a single responsibility, communicating only through
validated data contracts (ADR 01 §Component Boundaries):

| Component | Owns | Does not own |
|---|---|---|
| Input Processor | normalizing/structuring raw input into a `Request` | classification, planning |
| Laya | semantic classification, entity extraction, ambiguity detection, confidence | intent normalization, complexity |
| Intent Manager | normalizing Laya's classification into a canonical `Intent` | independent classification |
| Task Profiler | task requirements and **complexity** (sole complexity authority) | strategy |
| Planner | TaskGraph construction and revision (`replan()`, `validate()`) | runtime state, execution decisions |
| Agent State | runtime state for one task execution | planning, deciding |
| Decision Engine | producing a structurally validated `Decision` via LLM reasoning | graph construction, tool execution |
| Agent Orchestrator | driving the control loop, state transitions, observation | decision logic, tool implementation |

Key boundary rules (ADR 01 §Design Constraints):

- No component executes tools outside the Tool Manager interface.
- LLM outputs always pass schema validation before reaching any component.
- `AgentState` is the single source of truth for runtime task state.
- The TaskGraph is revisable — never a rigid workflow (CLAUDE.md principle 6).
- On REPLAN the Orchestrator calls `Planner.replan()`; it never mutates graph
  structure itself (ADR 01 §Data Flow, step 9).

## 4. Agentic control loop

```
OBSERVE → DECIDE → ACT → OBSERVE RESULT → VERIFY → UPDATE STATE → DECIDE AGAIN
```

Each DECIDE step yields one of eight decision types (ADR 06):
`EXECUTE`, `OBSERVE`, `REPLAN`, `RETRY`, `ASK_USER`, `WAIT`, `COMPLETE`,
`FAIL`. The loop terminates on `COMPLETE` or `FAIL`. The Orchestrator reacts
to observations rather than blindly following the original plan
(CLAUDE.md principle 14).

Decision validation is two-phase (ADR 00 §Glossary, ADR 03 §DECIDE):
1. **Structural** — Decision validated against its schema + parameter
   discriminated union (inside the Decision Engine).
2. **Contextual** — validated against current `AgentState` plus policy
   validation via the Policy Engine interface (inside the Orchestrator).

## 5. Safety and LLM rules

- LLMs propose structured decisions; they never execute tools directly
  (CLAUDE.md principle 10).
- All LLM output is schema-validated (principle 11); tool execution happens
  only behind explicit interfaces (principle 12).
- `AgentState.retry_count` is authoritative for retry limits; the Orchestrator
  enforces `RuntimeConfig.max_retries` / `max_replans` (ADR 04 §Runtime
  Configuration).
- No GUI, voice, persistent memory, multi-agent, or real automation are in the
  current milestone scope (CLAUDE.md §Scope Control, ADR 00 §Out of Scope).

## 6. Downstream systems (interface-only in this milestone)

Per ADR 01 §Downstream Systems and ADR 07/09: **Policy Engine**,
**Tool Manager**, **Browser / Windows / File System Tools**, and **Vision**
are specified as interfaces/mocks. Real integration belongs to later roadmap
phases (see [ROADMAP](../simple/ROADMAP.md)).

## 7. Documentation authority

The source-of-truth hierarchy is fixed by `CLAUDE.md`:
1. `CLAUDE.md` → 2. `docs/` (ADRs) → 3. `schemas/` → 4. source code →
5. tests. Conflicts between code and documented architecture must be raised
and documented, never silently redefined.

## 8. Open architectural decisions (verified open)

From ADR 01 §Unresolved Decisions:
- **LLM provider** — not yet selected. This genuinely remains open as of
  `c5db884`; it constrains Phase 5 (Decision Engine).
- **Technology stack** — the ADR states the stack was "not yet selected." The
  contract layer now in fact uses Python ≥3.11, Pydantic ≥2, jsonschema,
  pytest (`pyproject.toml` at `c5db884`). The ADR text has **not** been
  updated to record this; treat the ADR statement as stale relative to the
  contract layer. Full component-stack decisions (e.g., LLM SDK, any UI
  framework) remain open.
