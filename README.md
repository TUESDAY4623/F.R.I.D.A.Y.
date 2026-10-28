# FRIDAY — Jarvis Agentic Desktop AI

**Jarvis** is an agentic desktop AI system: it understands natural-language
requests, profiles and plans the task, then carries it out through an
agentic control loop that observes results, verifies outcomes, and adapts.

> **Note for readers arriving from the old README:** an earlier version of
> this project (September 2026) was a working desktop app with file tools
> and a UI. The repository was **deliberately reset on 2026-10-11**
> (`031c27a`) to a contracts-first foundation. That old code no longer
> exists in the repository (it remains in git history). This README
> describes the **current** project.

## Current status (as of 2026-10-28, commit `c5db884`)

- **Done & verified:** 14 architecture decision records
  (`docs/adr/00`–`13`), a frozen set of data contracts
  (`src/jarvis/contracts/` + 48 JSON schemas in `schemas/`), and a
  **431-test** contract suite (passing on a local run).
- **Next (planned, not started):** the input/understanding pipeline
  (Input Processor → Laya → Intent Manager), then planning, runtime state,
  the decision engine, and the orchestrator. Real tool execution is
  intentionally deferred behind interfaces and mocks.
- **No CI is configured** in the current tree; test evidence is local.

Details, evidence, and history: see
[**`brain/` — the project knowledge base**](brain/README.md).

## Repository layout

| Path | What it is |
|---|---|
| `brain/` | Knowledge base: `simple/` (plain-English) and `technical/` (engineering) layers |
| `docs/adr/` | 14 architecture decision records (00–13) — source of truth for architecture |
| `src/jarvis/contracts/` | Pydantic contract models, five groups (A–E) |
| `schemas/` | 48 JSON Schemas generated from the models |
| `scripts/generate_schemas.py` | Regenerates `schemas/` from the models |
| `tests/contracts/` | Contract test suite (431 tests) |
| `CLAUDE.md` | Project rules, architecture principles, and phase markers |

## Setup

Python ≥ 3.11. Dependencies: `pydantic` and `jsonschema` (runtime);
`pytest` (dev). There is no lockfile in the current tree.

## Verification

```bash
# Run the full contract test suite
python -m pytest tests -q          # expected: 431 passed

# Regenerate JSON schemas and confirm no drift
python scripts/generate_schemas.py # expected: "Generated 48 schemas"
git status --porcelain             # expected: no changes under schemas/
```

## How this project is governed

`CLAUDE.md` sets the rules: the pipeline's current milestone ends at the
Agent Orchestrator; LLMs only ever produce schema-validated structured
decisions; downstream systems stay interfaces/mocks until later phases; and
phases must not be skipped without approval. Architecture lives in
`docs/adr/`; the two-layer knowledge base lives in `brain/`.
