# Real Problems We Hit, and How They Were Solved

*Plain-English version of
[`../technical/PROBLEMS_AND_SOLUTIONS.md`](../technical/PROBLEMS_AND_SOLUTIONS.md).
Only problems that actually happened, each with its status. No speculative
"risks that might happen." "Old project" = the September 2026 version that
was later reset.*

## Old project (before the restart)

1. **The written-up numbers didn't match the tests.** Docs said 10 tests
   but the real suite had grown to 29. *Fixed by correcting the docs.*
   This same slip happened again later (see #5 below).
2. **A stray test file that never ran.** A test sat outside the folder the
   runner looked in, so it silently never executed. *Fixed by removing the
   stray copy.*
3. **Components doing more than their stage allowed.** Early "stub"
   pieces already contained real logic. *Handled by keeping the working
   code but being explicit that it didn't mean that stage was finished.*
4. **The desktop-window tests wouldn't run on the servers.** The test
   environment was missing the graphics libraries a window needs. *Fixed by
   running the window tests "off-screen" and installing the needed
   libraries.* (No longer relevant — the window and its test pipeline were
   removed in the restart.)
5. **Five file tools didn't fit together.** Parsing gaps, mismatched data
   formats between the planner and the understander, the approval step not
   actually being checked, and — worst of all — **the system reporting a
   task as "done" even when it had failed.** All seven issues were fixed
   and the 69-test suite passed with no regressions. *(All of this code was
   later removed in the restart; recorded for lessons.)*

## Current project

6. **The top-level `README.md` still describes the old, now-deleted
   project** (87 tests, a desktop app, files that no longer exist).
   *Being fixed right now* by rewriting it to match the current
   contracts-based project. **Status: in progress.**
7. **There is no automatic test-running (CI) in the current project.** It
   was removed during the restart and not put back. *Workaround: run the
   431 tests by hand and record the result.* **Status: open decision.**
8. **The design + contract phases were never formally "signed off".** The
   rules say Phase 1 can't start until Phase 0 is closed, but no document
   records that they're closed — even though the work is plainly done.
   *Recommended: a one-page sign-off.* **Status: open (not written yet).**
9. **One design document says the programming stack is "not chosen", but
   the contracts already use Python + a couple of libraries.** *Noted; the
   document needs a small update, which is out of scope for this doc pass.*
   **Status: open (minor).**
10. **The written-up reason for the restart does not exist in the repo.**
    This knowledge base gives the best-supported explanation and marks it
    clearly as a reconstruction. *Recommended: capture the team's real
    rationale as a short decision note.* **Status: open.**

*Every item above is backed by a specific commit, test count, or the old
progress log (recoverable from version history). The technical document
lists those references. Last verified: 2026-10-28.*
