# ARCHITECTURE HISTORY — Earlier Design, Reset, and Transition

> Everything in this file is **Historical**: it describes the pre-reset
> project (2026-09-12 → 2026-09-27), which was *deliberately removed* in
> commit `031c27a` (2026-10-11, "Reset repository: replace with Phase 0/1
> contract foundation"). Nothing described here exists in the current tree.
> Evidence cited is from git history: the pre-reset tree is inspectable at
> `git show 031c27a^:<path>` (e.g. `progress.md`, `documentation.md`,
> `README.md`).

Last verified: commit `c5db884`.

## 1. The earlier architecture (Sept 2026, "Jarvis Desktop Agent")

**What it was** (verified from the pre-reset tree, `031c27a^`):

- A working **modular-monolith desktop agent** in Python (3.11, `uv`-locked)
  with a canonical **11-step execution loop**
  (`src/jarvis/orchestrator/loop.py`, 566 lines) driving real work:
  `check cancellation/deadline → observe → decide → policy check → approval →
  dispatch → observe → verify → update state → log → continue`.
- **Real file-system tools** behind a single `ToolManager` execution gateway:
  `read_file`, `write_file`, `list_directory`, `create_directory`,
  `move_file` (`src/jarvis/tools/`).
- **Rule-based intent parsing**: `IntentManager` parsed text commands with
  regex patterns (e.g., `create directory <path>`, `write "content" to
  <path>`) — no LLM in the pipeline at that point.
- **Recovery/retry/replan machinery**: 5-category failure classification
  (`RETRYABLE`, `RECOVERABLE`, `REPLAN_REQUIRED`, `USER_ACTION_REQUIRED`,
  `FATAL`), bounded retries, auto-recovery by injecting `create_directory`
  into the pipeline, `Planner.replan()` with plan versioning.
- **Approval lifecycle** with a PySide6 **GUI** (`jarvis_ui.py`,
  `src/jarvis/ui/`): modal `ApprovalDialog`, task controls
  (Pause/Resume/Cancel), live tool-call tree.
- **Event Logger** subsystem with credential redaction and streaming
  subscribers; GitHub Actions CI (`.github/workflows/test.yml`).
- Test growth recorded in the deleted `progress.md`: 10 → 29 → 40 → 69 →
  81 → **87 passing tests** by 2026-09-27 ("Phase 2 COMPLETED, verified,
  ready for sign-off"). Contributors: Sujeet, Adarsh, Tanmay.
- Its own roadmap had already pointed at **OS-level UI automation,
  UIA/DOM visual elements, OCR/vision grounding** as the next phase
  (`progress.md`, 2026-09-27 entry).

## 2. The reset (`031c27a`, 2026-10-11)

Verified facts (from the commit itself):
- Removed: all implementation code (`main.py`, `jarvis_ui.py`,
  `src/jarvis/{tools,orchestrator,logger,intent,planner,state,recovery,ui,…}`),
  all old tests, `progress.md`, `documentation.md`, `uv.lock`,
  `.python-version`, and the CI workflow.
- Kept: 14 ADR files (`docs/adr/00`–`13`), Group A contract models/schemas/tests.
- Rewrote `pyproject.toml` as a contracts package (`jarvis-contracts`,
  pydantic + jsonschema).

The accompanying commit `59d35f4` (same day, "Phase 0 complete, Phase 1 Group A
contracts implemented") introduced the **new** 13-ADR architecture and the
contract foundation, establishing a new phase scheme (0–8, ADR 13) that is
**different** from the old 0/1/2 scheme in the deleted `progress.md`.

**Retained / replaced / removed:**

| Old asset | Fate |
|---|---|
| 11-step loop, orchestrator, tools, UI, recovery, logger, `main.py` | **Removed** |
| Old 15 test files (tools, UI, recovery, benchmark) | **Removed** |
| `progress.md`, `documentation.md` | **Removed** (evidence survives in git history) |
| `CLAUDE.md`, ADRs 00–13, Group A contracts + tests | **Retained / rewritten as new foundation** |
| CI workflow | **Removed** (not re-added as of `c5db884`) |

## 3. Why the architecture changed

**Status: the rationale is not formally documented anywhere in the repository
— the reset commit lists what was changed but not why. The following is the
best-supported reconstruction, explicitly marked as inference:**

Supported observations:
1. The new architecture (ADR 00) is an **agentic LLM-driven core**: the
   Decision Engine's LLM proposes schema-validated decisions, and all real
   tool execution is explicitly deferred behind **interfaces and
   deterministic mocks** (ADR 00 §Scope; CLAUDE.md §Current Development
   Boundary). The GUI and OS automation are *out of scope*.
2. The old approach's next steps (per the old roadmap) were **OS UI
   automation, visual elements, OCR/vision grounding** — a direction
   incompatible with the new "agentic core first, mocks only" boundary.
3. The old `progress.md` records repeated **contract/schema mismatches**
   (Blocker 3 "Planner schema harmonization", Blocker 2 intent-parsing
   grammar fixes) and a false-success reporting defect (Blocker 5). The new
   architecture makes schema-validated contracts the *foundation* phase
   (ADR 13 Phase 1) — a reasonable inference: the team concluded contracts
   must be defined and frozen before components are built, reversing the
   earlier build-first order.

These three points are **inferences from evidence**, not a documented
decision. If a definitive rationale exists, it lives outside the
repository (team discussion, chat, meeting notes) and should be captured in a
short decision record; until then this section stands as "undocumented,
best-supported reconstruction."

## 4. Post-reset history (Oct 2026, current codebase)

| Date | Commit(s) | Change |
|---|---|---|
| 10-11 | `59d35f4`, `031c27a` | New foundation: 14 ADR files (`00`–`13`), Group A contracts, repository reset |
| 10-12 | `a4a1c79` | `brain/` folder created (`brain/temp`) |
| 10-15 | `ecdb343`, `0952c11` | Groups B (task-understanding) and C (agent runtime) contracts |
| 10-26 | `9b33019` | **PR #1** merged (Groups B+C) |
| 10-26 | `7ae6e41` | Groups D (execution boundary) and E (user interaction) contracts |
| 10-28 | `ac66b2a` | ADR 04/07 field-contract clarifications (`UserResponse.timestamp`, `ToolResult.duration_ms`) |
| 10-28 | `c5db884` | **PR #2** merged — **Phase 1 contract freeze** (tip of `main`/`origin/main`) |

## 5. Numbering caveat for readers

The old and new project phases are **not** the same numbering scheme:
old "Phase 1" = text-driven execution core + 5 file-system tools (complete,
then deleted); new Phase 1 = core contracts and schemas (complete, frozen at
`c5db884`). Documents and git messages must always say which scheme they use.
The simple-layer document [ARCHITECTURE_EVOLUTION.md](../simple/ARCHITECTURE_EVOLUTION.md)
repeats this warning in plain language.
