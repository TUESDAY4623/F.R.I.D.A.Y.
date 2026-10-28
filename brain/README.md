# FRIDAY / Jarvis — Documentation Index

This folder (`brain/`) is the project's knowledge base. It has **two
layers**; read the one that matches your role, and jump across where
needed.

> `brain/temp` is a pre-existing scratch file. It is intentionally
> preserved untouched and holds nothing.

## Two layers, one set of facts

| Layer | For | Style |
|---|---|---|
| [`simple/`](simple/README.md) | A mentor or reviewer who wants the plain-English picture | Short, no jargon, no code |
| [`technical/`](technical/README.md) | Developers and future contributors | Detailed, evidence-cited (commits, tests, files) |

**Rule:** facts are written in the technical layer first; the simple layer
is a *summary* that links up to it. The layers must never contradict each
other. If you can't find a fact in `technical/`, it isn't established —
don't invent it in `simple/`.

## Start here

- **Mentor / reviewer →** [`simple/README.md`](simple/README.md) (what the
  project is), then `simple/PROJECT_STATUS.md`.
- **Developer →** [`technical/README.md`](technical/README.md) (how to
  navigate), then `technical/IMPLEMENTATION_STATUS.md` and
  `technical/ARCHITECTURE.md`.

## The two layers, document by document

| `simple/` | summarizes | `technical/` |
|---|---|---|
| [`simple/README.md`](simple/README.md) | — | `technical/ARCHITECTURE.md` |
| [`simple/PROJECT_STATUS.md`](simple/PROJECT_STATUS.md) | — | `technical/IMPLEMENTATION_STATUS.md` |
| [`simple/PROGRESS.md`](simple/PROGRESS.md) | — | `technical/CHANGELOG.md` |
| [`simple/ROADMAP.md`](simple/ROADMAP.md) | — | `technical/CURRENT_IMPLEMENTATION.md` |
| [`simple/ARCHITECTURE_EVOLUTION.md`](simple/ARCHITECTURE_EVOLUTION.md) | — | `technical/ARCHITECTURE_HISTORY.md` |
| [`simple/PROBLEMS_AND_SOLUTIONS.md`](simple/PROBLEMS_AND_SOLUTIONS.md) | — | `technical/PROBLEMS_AND_SOLUTIONS.md` |

## What lives *outside* `brain/` (do not duplicate here)

- **`docs/adr/`** — the 14 Architecture Decision Records (00–13). These are
  the source of truth for *architecture*. `brain/technical/` summarizes and
  links; it never overrides an ADR.
- **`CLAUDE.md`** — the project rules and current-phase marker.
- **`schemas/` + `src/jarvis/contracts/`** — the frozen data contracts.
- **`tests/`** — the contract test suite (431 passing as of 2026-10-28).

## Maintenance instructions

1. **Status changes** (a phase closes, a merge lands on `main`) → update
   `technical/IMPLEMENTATION_STATUS.md` and add a `technical/CHANGELOG.md`
   line, *in the same review*; then refresh the affected `simple/` doc.
2. **Contract changes** → update `technical/CONTRACTS.md`, regenerate
   schemas, re-run the suite.
3. **New problem resolved** → add an entry to
   `technical/PROBLEMS_AND_SOLUTIONS.md` with its evidence.
4. Every status-bearing doc carries a "Last verified: <date/commit>" line —
   update it when you re-verify.
5. **No CI exists.** Never write "CI passed"; only cite a local run with
   its command, count, and date.
6. If writing a doc reveals a problem with *source code or configuration*,
   **stop and report it** — this is a documentation-only system.
