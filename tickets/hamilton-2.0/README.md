# Effort: Hamilton 2.0 — a runnable end-to-end skeleton on the `2.0` branch

**Destination:** A maintainer or user can check out the branch `2.0` of the fork `SummitSG-LLC/hamilton`, install the core without pandas or numpy, and turn on one opt-in switch that makes the ordinary `Builder`/`Driver` API build graphs through a new compiler and run them on a new runtime, while the 1.x build and execution paths stay in place as the reference. They can compare behavior and speed between the two, read a "Migration to 2.0" document with instructions for every breaking change, and read written proposals for four areas the 2.0 outline leaves undefined. The purpose is a prototype that people can run and give feedback on, in place of a plan that nobody can run.

**Owner:** Dev-iL. The owner merges every pull request, accepts the runtime contracts, decides each survey, and gives the go for every outward-facing act.

**Order:** Ticket numbers give the planned order. The only hard order is each Ticket's `Depends on:` line. A Ticket is ready when every Ticket it depends on is merged into `2.0` by the owner.

## Context pointers

- The 2.0 outline: apache/hamilton discussion #1645, "Hamilton 2.0: Architecture and Roadmap Reassessment". Tickets quote it as "the outline".
- Decision records: `writeups/adr/`. Ticket 01 adds the records for this effort's starting decisions; later Tickets add theirs.
- The migration document: `docs/migration-to-2.0.md`, created by Ticket 04.
- The benchmark harness: `benchmarks/`, created by Ticket 03.
- Survey reports: `writeups/surveys/`, one file per survey Ticket (06, 17, 25, 26). The decision record that holds the owner's decisions goes in `writeups/adr/`.
- The contributor skills: `.claude/skills/`, with a pointer in the root `AGENTS.md`, created by Ticket 02.
- The plan's full acceptance contract and investigation log are on the owner's machine. Each Ticket carries everything a contributor needs; nothing here depends on those files.

## The switch

One switch selects the new compiler and the new runtime together: a `Builder` option for one Driver, and an environment variable for a whole test run. With the switch off, `Driver` and `Builder` build and execute exactly as on 1.x. With it on, a Driver either builds through the compiler and runs on the new runtime, or fails with an error that names what is unsupported. It never falls back to a 1.x path. `AsyncDriver` is a 1.x path and ignores the switch.

## Terms

- **Compiled graph:** the immutable result of compiling modules or functions with a config. It holds node definitions, edges, tags, a config snapshot and source locations. It holds no adapter.
- **Plan:** what one run will do: requested outputs, input bindings and task templates.
- **Run state:** values, task instances, outcomes and timing for one run. Each run owns its state.
- **Execution backend:** the thing that runs tasks: inline, threads, coroutines, or a system outside the process.
- **Observer:** code that is told about a run and does not change its results.
- **Runtime core:** the coordinator, plan, run state, contracts and the inline backend.
- **1.x paths:** today's graph building, default execution path, task-based execution path and `AsyncDriver`.

## Facts measured at the branch point

These were measured at commit `ef88b1e9` of `upstream/main`, on one machine with CPython 3.15.0 and a generated layered graph of integer nodes. They are starting evidence, not targets.

- Build: 103 ms per 1,000 nodes. The time goes to `typing.get_type_hints` and `inspect.signature`.
- Default-path execute: 13 to 22 µs per node. The task-based path with the synchronous executor: 206 ms against 12.5 ms on the default path for 1,000 nodes.
- `import hamilton.driver`: 431 ms; pandas is 287 ms and numpy 78 ms of it.
- A linear chain of 1,500 nodes raises `RecursionError` on execution. A cyclic graph builds without error.
- pyrefly 1.4.1 over `hamilton/`: 1,289 errors with its `default` preset, 151 with the lenient `basic` preset it uses when unconfigured.
- PyPI downloads of `apache-hamilton` by Python version, 2026-10-11 to 2026-11-09 (168,380 with a known version): 3.10 11.9%, 3.11 6.0%, 3.12 60.0%, 3.13 7.0%, 3.14 14.6%, 3.15 0.5%.
- From the outline's own measurements: on free-threaded 3.14, four-worker mapped execution of a 32-kernel CPU workload ran 3.04 times faster than sequential; the task-based coordinator used 168 ms of main-thread CPU in a 169 ms run, against 2.70 ms in 140 ms for a plain `ThreadPoolExecutor`; a forced schedule loses one of two cache version entries in 80 of 80 attempts.

## Traps in the current code

- All three execution paths call nodes through one recursive function, `execute_subdag`.
- The task-based executor rewrites the callable of the Driver's own nodes during a run, and `GracefulErrorAdapter` depends on that rewrite.
- A lifecycle "method" (`do_node_execute`, `do_remote_execute`, `do_validate_input`, `do_check_edge_types_match`, `do_build_result`) allows one implementer only. The Driver's own default adapters implement the legacy `execute_node`.
- `@config.when` renames the user's function in place when a graph is built, and building twice is not idempotent.
- The graph object stores adapters and uses them for edge type checks at build time.
- The deprecation mechanism ignores the pre-release part of the version, so version `2.0.0.dev0` makes every API scheduled to fail at 2.0.0 raise.
- Importing the decorator package imports every known extension, and the validation decorator imports the pandas validators at the top of its module.
- The cache adapter keeps per-run dictionaries that are never pruned, and it has no locks.
- CI's core workflow runs only for pull requests into `main`.

## Before `2.0` merges upstream

Remove `tickets/` from the branch. Decide with the PPMC whether `.claude/skills/` and `AGENTS.md` stay.
