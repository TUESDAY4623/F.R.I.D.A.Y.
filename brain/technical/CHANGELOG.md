# CHANGELOG — Chronological Record of Significant, Verified Changes

> Append-only. Each entry cites its commit(s). Pre-reset history is
> summarized; the full detail survives in git
> (`git log --all`, deleted files at `git show 031c27a^:<path>`).
> Maintenance rule: when a significant change merges into `main`, add one line
> here in the same review that approves it.

Last verified: commit `c5db884` (tip of `main` / `origin/main`, 2026-10-28).

## 2026-10 (current contract foundation)

| Date | Commit(s) | Change |
|---|---|---|
| 10-11 | `59d35f4` | **Phase 0 complete + Phase 1 Group A.** 13 ADRs (`docs/adr/00`–`13`); Group A contracts (`Request`, `LayaClassification`, `Intent`, `ExtractedEntity` + 3 enums) with 7 generated schemas; 68 tests passing at merge. |
| 10-11 | `031c27a` | **Repository reset.** Removed the entire pre-reset implementation (tools, orchestrator, logger, UI, recovery, `main.py`, `jarvis_ui.py`, old tests, `progress.md`, `documentation.md`, `uv.lock`, CI workflow). Kept ADRs + Group A contracts. `pyproject.toml` rewritten as `jarvis-contracts` package. |
| 10-12 | `a4a1c79` | Created `brain/` folder (contains only the 2-byte scratch file `brain/temp`). |
| 10-15 | `ecdb343` | Group B contracts: `TaskProfile`, `TaskGraph(+Node/Edge)`, enums `TaskType`/`Complexity`/`NodeStatus`/`EdgeType`. |
| 10-15 | `0952c11` | Group C contracts: `AgentState`, `ExecutionStep`, `Observation`, `VerificationResult`, `ErrorRecord`, `RuntimeConfig`, 8 decision variants + params, discriminated union `DECISION_ADAPTER`. |
| 10-26 | `9b33019` | **PR #1** merged — Phase 1 Groups B + C. |
| 10-26 | `7ae6e41` | Group D (execution boundary: `ProposedAction`, `ToolResult`, `PolicyResult`, `ValidationResult`, `ValidationError_`) + Group E (`UserResponse`, `WaitCondition`). |
| 10-28 | `ac66b2a` | ADR 04/07 clarifications: `UserResponse.timestamp` and `ToolResult.duration_ms` field contracts. |
| 10-28 | `c5db884` | **PR #2 merged — Phase 1 contract freeze.** 48 JSON schemas, 431 passing tests (local verification). |
| 10-28+ | — | **This documentation system** (`brain/`, root `README.md` rewrite) — branch `docs/brain-knowledge-base`, pending approval/merge. |

## 2026-09 (historical implementation — deleted in `031c27a`)

Summarized; full per-session log was the deleted `progress.md`
(`git show 031c27a^:progress.md`).

| Date | Reference | Change |
|---|---|---|
| 09-12 | `eccff73` | Old project Phase 0: modular monolith, Tool Registry contract, 11-step loop stubs, Event Logger, `main.py` Hello Loop. 10 tests. |
| 09-14 | `457349d` (+ CI commits) | PySide6 UI shell; CI workflows added. |
| 09-16 | `084070d`, `a0cc0aa`, `75d15a8` | Filesystem tools `write_file`, `create_directory` (+ fix). |
| 09-16 | `cabeedd`, `4edcd49` | Merges: `adarsh/phase-1-filesystem-tools`; PR #3 (old repo) fixing CI. |
| 09-20 | `bdf14e9`, `e8b43ed`…`e8bfe60` | Phase 2 core: failure classification, recovery, replanning, approval lifecycle; CI fixes (offscreen Qt, system libs). |
| 09-24 | `84e3d8b` | Phase 2 UI: modal ApprovalDialog, task controls, recovery visualizer. |
| 09-27 | `2c68036` | Old project "Phase 2 sign-off": 87 tests passing, 5 manual GUI scenarios verified. **(Superseded — code no longer exists.)** |

> Reader note: the "Phase N" labels in the 2026-09 rows are the **old**
> numbering (0/1/2 for tool+UI milestones), *not* the current ADR 13 scheme.
