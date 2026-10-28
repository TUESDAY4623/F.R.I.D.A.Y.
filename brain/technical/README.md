# Technical Documentation Index

Engineering-level documentation for the Jarvis agentic desktop AI project.
Every significant claim is tagged with one of five **claim classes**:

- **Implemented** — code exists in `src/` at the cited commit.
- **Verified** — a test run or recorded result supports the claim (count +
  command + date given; local runs are labeled, since there is **no CI**).
- **Planned** — appears in a roadmap or plan (ADR 13); not built.
- **Historical** — belongs to the pre-reset project (deleted in `031c27a`);
  survives only in git history.
- **Unknown / Unverified** — stated as such, never asserted as fact.

## Documents

| Document | Owns | Primary evidence |
|---|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Current intended architecture, component boundaries, control loop, open decisions | `CLAUDE.md`, ADRs 00–01/03/05/06 |
| [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) | What exists per phase/component; verified test counts | working tree at `c5db884`, git log, local pytest |
| [CURRENT_IMPLEMENTATION.md](CURRENT_IMPLEMENTATION.md) | The next authorized task (Phase 2), scope, acceptance criteria | ADR 13 §Phase 2, contract models |
| [CONTRACTS.md](CONTRACTS.md) | Contract groups A–E, schemas, generation, validation, naming notes | `src/jarvis/contracts/`, `schemas/`, generator |
| [TESTING.md](TESTING.md) | Test layout, commands, results, verification limitations | `tests/contracts/`, `pyproject.toml`, local runs |
| [ARCHITECTURE_HISTORY.md](ARCHITECTURE_HISTORY.md) | Earlier architecture, the reset, transition; numbering caveat | git history (`031c27a^`, old `progress.md`) |
| [PROBLEMS_AND_SOLUTIONS.md](PROBLEMS_AND_SOLUTIONS.md) | Actual engineering problems (PS-01…PS-10) and resolutions, with evidence | old logs in git, commits, current tree |
| [CHANGELOG.md](CHANGELOG.md) | Chronological record of significant verified changes | `git log --all` |

## What this layer does not own (to avoid duplication)

- **Full ADR text / decision rationale** → `docs/adr/` remains the source of
  truth. These docs summarize and link; they never contradict.
- **Field-level contract definitions** → the models and JSON schemas.
  [CONTRACTS.md](CONTRACTS.md) inventories and explains, not redefines.
- **Plain-English mentor summaries** → `brain/simple/`, which is derived from
  this layer. Facts live here first; the simple layer links up, never
  diverges.

## Update workflow (keep this layer trustworthy)

1. **Phase/feature state changes** (a merge into `main`) → update
   [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) and add a
   [CHANGELOG.md](CHANGELOG.md) line in the same review.
2. **Contract changes** → update [CONTRACTS.md](CONTRACTS.md), regenerate
   schemas (`python scripts/generate_schemas.py`), re-run the suite.
3. **New decision / problem resolution** → add to
   [PROBLEMS_AND_SOLUTIONS.md](PROBLEMS_AND_SOLUTIONS.md) with evidence.
4. Every status-bearing doc carries an "Last verified: commit X" line so
   staleness is detectable. Update that line when you re-verify.
5. No document may claim "CI passed" — there is no CI (PS-08).
