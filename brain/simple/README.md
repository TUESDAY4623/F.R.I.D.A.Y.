# What is FRIDAY / Jarvis? (for a non-technical reader)

FRIDAY's codebase is called **Jarvis**. It is the foundation for a
**desktop AI assistant that gets things done for you** — you describe what
you want in ordinary language, and the system plans and carries out the work
in small, checkable steps, adapting as it goes.

## How it works, in one paragraph

You type a request. The system figures out what you actually want
("understand"), decides what the task involves ("profile"), and draws up a
short plan of steps ("plan"). Then it works through the plan in a loop: do a
step, check the result, update its notes about where it is, and decide what
to do next — including "do that step again", "make a new plan", or "check
with the user". The loop ends when the task is finished or genuinely cannot
be done.

A key safety rule: the AI only ever *proposes* structured next steps. A set
of formally-defined "contracts" (formats the system must use, like a
contract on paper) is checked every time. The AI cannot act outside the
rules, and right now no real-world actions happen — everything downstream is
designed but deliberately left as placeholders, so the core thinking engine
can be built and tested safely first.

## Where the project stands right now

The **thinking-and-planning foundation** is done and verified: 14 design
documents, a frozen set of data contracts, and **431 passing tests**
(ran locally on the team's machine — this project currently has no
automated "continuous integration" checking). The next step is building the
first piece of the pipeline (turning your words into structured
understanding), which is planned but not yet started.

Two important things to know:

1. **This project was restarted once.** An earlier version (September 2026)
   was a working desktop app that actually moved real files around on a
   computer. The team deliberately reset the repository in October 2026 and
   rebuilt it from the design documents down, to get the foundations right
   before writing more code. The old version is gone from the code but its
   history is fully recoverable.
2. The plain status snapshot is in [PROJECT_STATUS.md](PROJECT_STATUS.md).

## Where to look next

| If you want to… | Read |
|---|---|
| See current status at a glance | [PROJECT_STATUS.md](PROJECT_STATUS.md) |
| See what has been done | [PROGRESS.md](PROGRESS.md) |
| See what is planned next | [ROADMAP.md](ROADMAP.md) |
| Understand the restart of the project | [ARCHITECTURE_EVOLUTION.md](ARCHITECTURE_EVOLUTION.md) |
| See real problems the team hit and how they were solved | [PROBLEMS_AND_SOLUTIONS.md](PROBLEMS_AND_SOLUTIONS.md) |
| Read the detailed engineering version | [`../technical/README.md`](../technical/README.md) |

*Last verified: 2026-10-28 (project state at that date). For the
engineering-level detail and evidence, each document here links to the
corresponding technical document — facts are written down in the technical
layer first, and this layer is a plain-language summary of it.*
