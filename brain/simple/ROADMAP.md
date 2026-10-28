# Roadmap — What Comes Next

*Plans, not promises. Derived from
[`../technical/CURRENT_IMPLEMENTATION.md`](../technical/CURRENT_IMPLEMENTATION.md)
and the project's official roadmap
([`docs/adr/13-development-roadmap.md`](../../docs/adr/13-development-roadmap.md)).
Nothing below has started. Phases must not be skipped without explicit approval.*

## Where each phase stands

| Phase | What it is, in plain words | Status |
|---|---|---|
| 0 | Design and agreements | ✅ Done (not formally signed off yet) |
| 1 | Frozen data contracts + tests | ✅ Done & verified (431 tests) |
| 2 | **First pipeline piece: understanding your request** | ⏳ Next, not started |
| 3 | Figuring out what the task needs; drawing the plan | Not started |
| 4 | The "notebook" that tracks a task while it runs | Not started |
| 5 | Deciding what to do next (the AI's structured choices) | Not started |
| 6 | The execution loop that carries a task to the end | Not started |
| 7 | Practice tools ("mocks") so the loop can be tested safely | Not started |
| 8 | Real-world actions (files, apps, browser) | Not started; may be split up |

## The next step, spelled out (Phase 2)

1. **Input Processor** — turns your words into a clean, structured request.
2. **Laya** — figures out what kind of request it is and pulls out the key
   items (files, links, names, times). This will use an AI model through a
   *mock* at first, because **no AI provider has been chosen yet**.
3. **Intent Manager** — settles any vagueness and produces one canonical
   "this is what you asked for" record.
4. **Tests** — every output must match the frozen contracts; the whole 431-test
   suite must keep passing.

**Done means:** the understanding section works end-to-end, is tested
without any real outside program, and doesn't break the existing tests.

## Rules of the road

- Each phase starts only when the previous one is closed
  (no skipping without sign-off).
- AI is always kept behind the rules: it *proposes* structured decisions;
  checks and limits are enforced by the system, not the AI.
- Nothing here begins automatically — the next phase needs a clear "go".

*Last verified: 2026-10-28.*
