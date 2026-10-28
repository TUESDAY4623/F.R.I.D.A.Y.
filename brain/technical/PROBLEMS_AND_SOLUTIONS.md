# PROBLEMS & SOLUTIONS — Verified Engineering Problems and Resolutions

> This is a record of problems that **actually occurred** and are supported by
> evidence (deleted logs in git history, commits, tests, or the current tree).
> Each entry states status and evidence. It is **not** a speculative risk
> register. The architectural reset is recorded as project history in
> [ARCHITECTURE_HISTORY.md](ARCHITECTURE_HISTORY.md), not categorized here as a
> "problem." Items marked *(Historical)* belong to the pre-reset project and
> are cited from the deleted `progress.md` / `documentation.md`
> (`git show 031c27a^:progress.md`).

Last verified: commit `c5db884`.

---

## Historical problems (pre-reset project, evidence in git history)

### PS-01 *(Historical)* — Stale test counts in documentation
- **Symptom:** `documentation.md`/`README.md` reported "10 tests passed" while the actual verified suite had grown to 29.
- **Root cause:** docs were updated per-feature but not re-synced to the latest test run.
- **Resolution:** corrected counts to the verified 29; kept the progress log append-only.
- **Evidence:** `progress.md` 2026-09-16 entry, "Issue 1 — Outdated test count."
- **Status:** Resolved (then the files were deleted in the reset). **The same
  failure mode recurs today** — the root `README.md` still documents the
  deleted 87-test/UI build. See PS-07.

### PS-02 *(Historical)* — Orphaned root-level test
- **Symptom:** a `test_throwaway_tools.py` at repo root had broken imports and sat outside `testpaths=["tests"]`, so it never ran.
- **Resolution:** removed the orphaned root copy; kept the canonical
  `tests/test_throwaway_tools.py`.
- **Evidence:** `progress.md` "Issue 2 — Orphaned root-level test."
- **Status:** Resolved (historical).

### PS-03 *(Historical)* — Phase-scope overlap in Policy Engine & Tool Manager
- **Symptom:** Phase 0 "pass-through" stubs already contained real
  risk-based ALLOW/CONFIRM/DENY logic and argument validation/timeouts — more
  than the phase intended, risking over-claiming.
- **Resolution:** retained the working logic; documented it as early Phase 1
  overlap **without** claiming Phase 1 completion.
- **Evidence:** `progress.md` "Issue 3 — Policy Engine scope overlap" and
  "Issue 5 — Tool Manager scope overlap."
- **Status:** Resolved (historical). This is a useful precedent for the
  "don't over-claim completion" rule used throughout this documentation set.

### PS-04 *(Historical)* — CI/runner failures for the PySide6 GUI tests
- **Symptom:** UI tests failed on runners: PySide6 could not import
  (`libEGL`), missing Qt/Mesa system libraries, and a Windows "trailing
  dot/period in path" checkout error.
- **Resolution:** run UI tests offscreen on `ubuntu-latest`; install
  `libegl1`, `libgl1`, `libxkbcommon-x11-0` and full Mesa/Qt runtime; make
  backend tests tolerate a missing PySide6 import.
- **Evidence:** commits `e8b43ed` (offscreen/Windows path workaround),
  `2e83d6a` (install Qt/egl libs), `f6a25c6` (Mesa/Qt runtime libs),
  `e8bfe60` (graceful import handling).
- **Status:** Resolved (historical) — **the CI was later deleted in the
  reset (031c27a)**, so none of this applies to the current tree. See PS-08.

### PS-05 *(Historical)* — The seven Phase 1 integration blockers
- **Symptom:** end-to-end 11-step loop broke on the 5 file-system tools: missing
  `move_file` integration, intent-parsing grammar gaps (`create_directory`,
  quoted paths), Planner/IntentManager schema mismatch, approval-gating not
  wired into dispatch, and **false `task.completed` on failed operations**.
- **Resolution:** all seven resolved; `IntentManager`/`Planner` schema
  harmonized, `ToolManager.dispatch()` wired to approvals, honest failure
  propagation added; verified **69/69 passing, 0 regression** by 2026-09-20.
- **Evidence:** `progress.md` 2026-09-20 "Seven Blockers Resolved"
  (numbered 1–7 with per-item detail).
- **Status:** Resolved (historical — code deleted in the reset).

---

## Current problems (post-reset project, evidence in current tree/commits)

### PS-07 — Root `README.md` documents the *deleted* architecture *(in progress)*
- **Symptom:** the repo-root `README.md` (unchanged since pre-reset) claims
  "Phase 0/1/2 Completed," 87 passing tests, `main.py`, `jarvis_ui.py`,
  `progress.md`, `uv.lock`, and a full file catalog — **none of which exist**
  after `031c27a`. A reader is badly misled about the current scope.
- **Root cause:** the reset removed all other files but left the old README.
- **Resolution:** **being applied by this documentation set** — root
  `README.md` is being rewritten to describe the current contract-based
  project and point to `brain/`.
- **Evidence:** `README.md` at `c5db884` vs `git ls-files` (no
  `main.py`/`jarvis_ui.py`/`uv.lock`/`progress.md` present); `031c27a`
  commit message ("Remove all previous implementation code").
- **Status:** **In progress / to be resolved** by the `README.md` rewrite.

### PS-08 — No CI in the current tree *(known gap, mitigated)*
- **Symptom:** the only test evidence is local; there is no workflow to run
  on push/PR.
- **Root cause:** `.github/workflows/test.yml` was deleted in `031c27a` and
  not re-added.
- **Resolution/workaround:** run `python -m pytest tests -q` locally and
  record counts (431 passing verified at `c5db884`). Re-adding CI is a
  decision **not yet documented** — tracked, not started.
- **Evidence:** `git log -- .github` shows deletion at `031c27a`; `ls .github`
  fails at `c5db884`.
- **Status:** **Unresolved** (intentional gap; no claim of CI should be made
  in any doc until a workflow exists).

### PS-09 — Phase 0/1 status not formally closed *(documentation gap)*
- **Symptom:** `CLAUDE.md` says `CURRENT_PHASE = 0` and "Do not begin Phase 1
  until Phase 0 is explicitly completed"; `docs/adr/13-development-roadmap.md`
  labels Phase 0 "Current phase" — yet Phase 1 contracts are delivered and
  frozen (`c5db884`).
- **Root cause:** the reset + contract work outpaced a status sign-off
  document. No ADR or note records that Phase 0/1 are closed.
- **Resolution:** not yet done. Recommended: a short decision record (new
  ADR or `brain/technical` note) closing Phase 0/1 and recording the reset as
  a deliberate scope decision. **Not authored here** to avoid changing an
  architectural decision for documentation's sake.
- **Evidence:** `CLAUDE.md` §Current Phase; `docs/adr/13` §Phase 0; `c5db884`.
- **Status:** **Unresolved** (a process/documentation gap, not a code bug).

### PS-10 — ADR 01 "technology stack unselected" is stale *(minor, known)*
- **Symptom:** ADR 01 §Unresolved Decisions lists the tech stack as
  unselected, but `pyproject.toml` already pins Python ≥3.11, Pydantic ≥2,
  jsonschema, pytest.
- **Root cause:** the ADR text predates the contract-layer tooling decision.
- **Resolution:** note the discrepancy (done in
  [ARCHITECTURE.md](ARCHITECTURE.md) §8); updating ADR 01 itself is out of
  scope for a docs-only pass. The **LLM provider** remains genuinely open.
- **Evidence:** ADR 01 §Unresolved Decisions vs `pyproject.toml` at `c5db884`.
- **Status:** **Unresolved** (minor staleness).
