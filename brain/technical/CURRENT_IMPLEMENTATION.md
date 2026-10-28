# CURRENT IMPLEMENTATION — What Is Being Built Now

> Describes the authorized, currently-pending implementation task, derived
> from the roadmap (ADR 13) and the current tree at commit `c5db884`.
> This is a **plan**, not a completion record. No Phase 2+ code exists yet.

## 1. What is being implemented next

**Phase 2 — Input Processor and Intent Layer** (ADR 13 §Phase 2), which
includes Laya's classification implementation:

| Item | Detail |
|---|---|
| Prerequisites | Phase 1 complete (met — contracts frozen, 431 tests passing) and Phase 0 formally closed (substantively met; formal closure not yet recorded, see [PROBLEMS_AND_SOLUTIONS.md](PROBLEMS_AND_SOLUTIONS.md) §PS-05) |
| Deliverables | Input Processor, Intent Manager, Laya classification implementations + unit tests + integration tests for the segment Input Processor → Intent Manager → Laya; **mock LLM integration** for Laya and Intent Manager |
| Boundaries | Downstream components remain interfaces/mocks; no real tool execution, no GUI (CLAUDE.md §Current Development Boundary) |

## 2. Scope of the immediate work, step by step

1. **Input Processor** → produces a schema-valid `Request`
   (Group A: `src/jarvis/contracts/models/group_a.py`).
2. **Laya classification** → produces a `LayaClassification`
   (category, entities, characteristics, confidence, ambiguity) via a
   **mock/structured-LLM boundary** — LLM outputs must be schema-validated
   (CLAUDE.md principle 11). LLM provider is **unselected** (ADR 01
   §Unresolved Decisions), so a deterministic mock or provider-adapter
   stub is the expected approach (ADR 13 lists "Mock LLM integration").
3. **Intent Manager** → normalizes the LayaClassification into a canonical
   `Intent` (entities, constraints, confidence, ambiguity resolution).
4. **Integration test** of the segment, all outputs validated against
   `schemas/` (ADR 04 §Validation Rules).

## 3. Acceptance criteria

Per ADR 13 §Phase 2 and the project's testing rules (ADR 12):
- Each of the three components is independently unit-testable without real
  external applications (ADR 00 §Success Criteria).
- Integration tests cover the pipeline segment end-to-end.
- Contract tests confirm every produced object validates against the
  corresponding JSON schema.
- All existing 431 contract tests still pass (no regressions).

## 4. What is explicitly **not** in this task

- No Task Profiler / Planner work (Phase 3), no Agent State runtime
  (Phase 4), no Decision Engine (Phase 5), no Orchestrator (Phase 6), no
  mock or real tools (Phases 7–8).
- No changes to contract models or schemas — those are frozen (PR #2). If a
  new phase reveals a contract gap, the contract must be changed through a
  documented decision, not silently.

## 5. Status as of this document

**Not started.** Last verified `c5db884`. Beginning Phase 2 requires an
explicit go-ahead (CLAUDE.md: "Do not skip phases without explicit approval").
