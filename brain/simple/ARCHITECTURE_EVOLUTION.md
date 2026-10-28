# Why the Project Looks Different Than It Used To

*Plain-English version of
[`../technical/ARCHITECTURE_HISTORY.md`](../technical/ARCHITECTURE_HISTORY.md),
which has the evidence and exact history.*

## The short story

In **September 2026** the team built a working version of the assistant:
it ran a fixed 11-step "do–check–loop", could actually read, write and move
real files on a computer, and showed all of that in a small desktop window.
By late September it passed 87 tests and was signed off as "ready".

In **October 2026 the team deliberately restarted the project.** They wiped
that working code from the repository and kept only the design documents.
The new direction is different: instead of starting with a fixed loop and
file tools, the new project starts from **agreed data contracts** and an
**AI-driven decision engine** that decides, at each step, what should
happen — doing, re-doing, re-planning, asking you, waiting, finishing or
giving up. Real actions (files, apps, browser) are intentionally postponed
and represented by placeholders, so the thinking core can be built and
tested first.

## What stayed, what went

- **Gone from the code:** the 11-step loop, the file tools, the desktop
  window, the recovery/approval machinery, the automatic test pipeline,
  and the old progress notes. (All recoverable from version history.)
- **Kept:** the 14 design documents. They were rewritten into a new form
  that now governs the project.
- **New:** the frozen set of data contracts (five groups, 48 schema files,
  431 tests) — the foundation everything else will be built on.

## One warning about "phases"

The old and new projects **use the same words for different things**.
Old "Phase 1" meant "file tools + window"; new "Phase 1" means "frozen
data contracts". Any time you see "Phase N", always ask *which* project it
refers to. (The technical document states this in more detail.)

## Why the restart happened

The repository records **what** changed but not a formal **why**. The
best-supported reading from the evidence is: the old version had repeated
integration problems (mismatched data formats between components, a
bug where failed work was reported as success), and its next steps had
moved toward operating desktop applications — a direction that didn't fit
the goal of a safe, AI-driven core. So the team chose to get the contracts
and the decision engine right first.
**This explanation is reconstructed from the evidence; no formal
decision record explaining the restart has been written.** (That gap is
itself tracked — see
[PROBLEMS_AND_SOLUTIONS.md](PROBLEMS_AND_SOLUTIONS.md).)

*Last verified: 2026-10-28.*
