# Progress — What Has Been Done

*Derived from
[`../technical/CHANGELOG.md`](../technical/CHANGELOG.md) and
[`../technical/IMPLEMENTATION_STATUS.md`](../technical/IMPLEMENTATION_STATUS.md).
"Verified" always means the team's local test run; there is no CI.*

## Completed and verified (current project)

1. **Design phase.** 14 design documents ("ADRs") covering the whole
   architecture, and the project rules ("how we build this").
2. **Contract freeze.** Every data format the system will use is defined in
   Python, frozen, and has machine-checkable schema files. Grouped into five
   sets: *understanding your request*, *planning*, *the runtime/decisions*,
   *the execution boundary*, and *talking back to the user*.
3. **Test suite.** 431 tests that check the contracts behave correctly.
   **All passing** as of 2026-10-28 (local run).
4. **This documentation system** (`brain/`) — new; that is this effort.

## Completed but no longer present (previous version of the project)

Before the October 2026 restart, the team had built and verified a working
desktop assistant: it could read/write/move real files, plan multi-step
tasks, ask the user for approval on risky steps, and show everything in a
small window — with 87 passing tests. **That code was intentionally removed**
when the project was restarted on a contracts-first foundation. It is fully
recoverable from the version history, and its lessons are recorded in
[ARCHITECTURE_EVOLUTION.md](ARCHITECTURE_EVOLUTION.md) and
[PROBLEMS_AND_SOLUTIONS.md](PROBLEMS_AND_SOLUTIONS.md).

## Not started yet

The pipeline components that turn a real request into a real, safe task —
understanding, profiling, planning, the execution loop, and mock tools.
All planned; none begun. (See [ROADMAP.md](ROADMAP.md).)

## What is still open

- Turn this knowledge base into a normal part of how the team works
  (the update routine lives in
  [`../technical/README.md`](../technical/README.md)).
- Write the short sign-off that officially closes the design + contract
  phases (currently implied by the work, not written down).
- Decide whether to bring back automated checking (CI).

*Last verified: 2026-10-28.*
