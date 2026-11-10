Kind: shaped
Type: chore
Status: open
Depends on: 01
Claimed by:

# Build the benchmark harness and record reference results for the 1.x paths

## Why

This effort promises that a reader can compare speed between the 1.x paths and the new compiler and runtime. Nothing in the repository can make that comparison today. The numbers in the effort's front file came from throwaway scripts on one machine, and the outline says of its own probes that they "are not checked into upstream CI". Later Tickets will claim that the new synchronous path is not slower, that import is faster, and that free-threaded Python keeps its speedup. Each of those claims needs a measure that existed before the attempt, was shown to detect a slowdown, and was then frozen so that nobody can tune the measure to the result. This Ticket builds that measure: one command under `benchmarks/`, proof that it catches a known slowdown, and a record of what the 1.x paths measured at the branch point.

## Authority and intent

Dev-iL assigned this effort and ruled that the 1.x paths "stay as the reference for behavior and speed comparisons". No ruling fixes the harness itself. Its scenarios, the proof that it detects a slowdown, and the reference record are the plan's working reading of what a speed comparison needs. The scenarios are the ones the outline and the plan's own measurements used. All of it may be revised on evidence, as long as later Tickets can still state performance verdicts the way the rules below require.

Dev-iL merges the pull request. The layout under `benchmarks/`, the command's name, the result file's format, the number of runs per scenario and the way each probe measures are yours. Fix the number of runs before you read a result.

## Scope

A new `benchmarks/` folder: the harness, a fixture generator, a short document for the command, and result files. Nothing under `hamilton/` changes. The delay that proves the measure is a scratch change; do not merge it. A dependency that only the harness needs goes into a development dependency group, not into the core's required dependencies. Do not add a CI job that fails on a timing threshold; no Ticket asks for one, and later Tickets judge speed from harness runs on one machine.

## Rules that must hold

These rules bind every Ticket of the Hamilton 2.0 effort. "The owner" is Dev-iL.

- **Start only when dependencies are merged.** Begin this Ticket only after the owner has merged every Ticket it depends on into `2.0`. Never merge a pull request yourself.
- **The 1.x paths stay.** With the switch off, graph building, the default execution path, the task-based path and `AsyncDriver` exist and behave as on `upstream/main`. The only allowed differences are changes that have migration instructions and fixes that are also proposed for `main`. (Owner's ruling: the old paths are the reference for behavior and speed comparisons.)
- **Ruled out by the owner for this plan.** No move to a `src/` layout. No Dask, Ray or Spark adapter ported to the new runtime. No process-pool backend. No best-effort mode, retry policy or fallback policy in the new runtime. A survey Ticket adds only its report, its proposal and the decision record that holds the owner's decisions.
- **Left out by the plan; the owner may revise on evidence.** `requires-python` stays `>=3.11`. No compiled or native code. No entry-point plugin discovery and no new provider distribution. No declared-config or default-producer rules. No change to how `@check_output` nodes are named or exposed. No driver-script emitter and no new renderers. No runtime branching or loops.
- **Outward-facing acts wait for the owner's go, each time.** Do not push a branch named `2.0` to the fork, do not push, open a pull request, or write an issue, comment or discussion post on `apache/hamilton`, and do not publish a package, unless the owner said go for that specific act. Stop at the prepared state (a local branch, a drafted description) and report what is waiting. Pull requests from a work branch into `2.0` on the fork need no separate go once `2.0` exists there.
- **The project's checks pass.** `uv run prek run --all-files --hook-stage pre-merge-commit` exits 0. `uv run pytest tests/ --ignore tests/integrations` exits 0 on Python 3.11 and on the newest Python in the CI matrix. On a branch that carries the pyrefly configuration, the pyrefly check exits 0 when run with the command and environment the static-checks job uses. Every CI job and step on the pull request passes, the integration and plugin steps included.
- **Every breaking change gets migration instructions in the same pull request.** A breaking change is any change after which code that works on Hamilton 1.90 fails, warns differently or returns a different result. Add the instructions to `docs/migration-to-2.0.md`: in its main part when the change applies with the switch off, in its section for the day the new compiler and runtime become the default when it applies only with the switch on. (Owner's requirement.)
- **The runtime core names no adapter, and every adapter is removable.** The coordinator, plan, run state, contracts and inline backend import no thread backend, coroutine backend, caching module or integration, and do not branch on the identity of one. Each attaches only through a public contract that code outside the `hamilton` package could implement. A test in the suite fails when a core module imports an adapter module, and with any one adapter module made unimportable, the runtime tests that do not use it still pass. (Owner's requirement: the abstraction matters more than the backends.)
- **Code holds up for its users and maintainers.** Correct results for supported inputs; a clear error for each new failure mode; a bound or cleanup path for anything that grows per run or per item; tests that would fail on a plausible wrong implementation and take expected values from a source independent of the code under test; accurate type hints on new public functions; correct documentation; the ASF license header on each new file (added by hand under `docs/`).
- **Typing, on a branch that carries the pyrefly configuration.** The typed consumer script calls each public function or class this Ticket adds for callers outside `hamilton`, and still passes pyrefly. The pyrefly baseline gains no entry for code this Ticket writes, and has no entry under `hamilton/compiler/` or `hamilton/runtime/`. pyrefly's scope and preset stay as they are. Each inline suppression carries its reason.
- **One pull request per Ticket, and it shows the change working.** The description's top reads in about a minute: what changed and why, how it was shown working, decisions made, debt left. It carries, or links to, the commands and output of the runs that prove the change, and for a behavior change one short before-and-after from the user's side.
- **Performance claims are measured verdicts.** Any statement that something is faster, slower or unchanged gives the verdict, the scenario from the `benchmarks/` harness, run count and range on each side, the noise floor, the machine and Python build, and the limiter named from a profile. Both sides run alternately on the same machine. A gap smaller than the noise floor is "no measurable difference".
- **Written material is accurate and not hard-wrapped.** Each factual claim traces to code, a measurement or a named source. In `.md` files, each paragraph and each list item is one physical line.

## Watch out for

- The switch does not exist yet; Ticket 07 adds it. Give each scenario a way to select a side now. Until the new side exists, selecting it must fail with a clear message. It must never measure the 1.x path under the new side's name.
- A stored result file is a reference record. It is never one side of a comparison: the rules below require both sides to run alternately on the same machine. Say so in the harness document, and build the harness so that it can run two sides alternately in one invocation. One later comparison has its old side in another commit (Ticket 21 measures import time against the commit before its change), so the harness must also be able to measure a second checkout.
- Later Tickets use these scenarios by name: Ticket 10 the default-path execute scenarios and the tiny-node scenario, Ticket 13 the 32-kernel workload with four workers against the 1.x multithreading path, Ticket 19 the 1,000-node fixture, Ticket 21 the import-time scenario. Keep the scenarios separately addressable.
- The front file's numbers are starting evidence, not targets. Your machine will give other numbers. Do not tune scenarios until they reproduce those.
- Measure run-to-run variation first. A gap smaller than the variation is no measurable difference. When a result looks good, ask why it is not twice as good, and name the limiter from a profile. Treat a gain larger than the changed piece's share of the whole as a measurement fault until it is explained.
- Import time must be measured in a fresh interpreter for every sample; a second import in one process is served from `sys.modules`. At the branch point `import hamilton.driver` took 431 ms, of which pandas was 287 ms and numpy 78 ms.
- The task-based path needs `Builder.enable_dynamic_execution(allow_experimental_mode=True)`. For the synchronous-executor scenario, set `SynchronousLocalTaskExecutor` as both the local and the remote executor.
- All 1.x paths call nodes through one recursive function, and a linear chain of 1,500 nodes raises `RecursionError`. Shape the generated graphs so that the 1.x paths can run them. If the harness raises the recursion limit, that is part of the setup: record it in the result file. The planning measurements used a layered graph of integer nodes in which each node depends on up to three nodes of the previous layer.
- Coordinator CPU time means CPU time of the thread that calls `execute`, not of the process. Process CPU time includes the workers and hides what the probe is for: the 1.x coordinator polls while workers run, and the outline measured 168 ms of main-thread CPU in a 169 ms run, against 2.70 ms in 140 ms for a plain `ThreadPoolExecutor`.
- The mapped four-worker run is faster than the sequential run only on a free-threaded build: the outline measured 3.04 times faster on free-threaded 3.14 and 0.36 times on conventional 3.14. On a free-threaded build, record `sys._is_gil_enabled()` after imports in the result file. An extension that is not free-threading-safe turns the GIL back on at import, and the result then describes a different interpreter than its label says.
- Check every scenario's outputs against values computed independently of Hamilton. A scenario that returns wrong results fast is not a measurement.
- Record with each result what a reader needs to judge it: machine, operating system, Python build, GIL state, versions of the installed packages, the commit measured, run count, and the setup.
- The reference results describe the code under `hamilton/` as it was at the `2.0` branch point. If `hamilton/` has changed on `2.0` by the time you measure (Ticket 04 may merge first), measure from the branch-point commit and record that commit.
- The effort's decision to write no native code rests on the measurements in the front file, which show build time going to `typing.get_type_hints` and `inspect.signature`. This harness is the instrument that would overturn that decision. Make sure a profile of the build scenario can name where the time goes.

The outline defines the CPU workload as 32 identical pure-Python integer kernels with distinct item inputs and 262,144 iterations per kernel. The sequential graph has one function per item and collects the outputs; the mapped graph expands the item IDs, applies the kernel and collects the same outputs. The kernel and its independent oracle are:

```python
def kernel(item, iterations):
    total = 0
    for i in range(iterations):
        total += (i ^ item) & 255
    return total + item


def reference(item, iterations):
    blocks, tail = divmod(iterations, 256)
    return blocks * 32640 + sum((i ^ item) & 255 for i in range(tail)) + item
```

## Suggested approach

This is advice; discard it if you find better. Write the fixture generator first and check its graphs against a plain-Python evaluation of the same functions. Add one scenario at a time and run each twice before adding the next. Decide the run count from the variation you see, write it down, and only then read results. Prove the measure with the deliberate delay, then freeze scenarios, inputs and setup in the repository. Take the reference results last, on one conventional and one free-threaded build.

## Definition of done

No part of this Ticket is fixed by a ruling of the owner beyond the rules above. All of it is the plan's working reading of what the speed comparison needs, and may be revised on evidence as long as later Tickets can still state measured verdicts.

- One documented command, with a checked-in fixture generator, measures the following and writes them to a machine-readable file, with the run count and the range for each scenario. To show it, run the command and read the file.
  - Import time of `hamilton.driver`.
  - Build time for generated layered graphs of 1,000 and of 10,000 nodes.
  - Execute time on the default path for both graphs.
  - Execute time on the task-based path with the synchronous executor.
  - The 32-kernel CPU workload, sequential and mapped with four workers, with wall time and coordinator main-thread CPU time, beside the same workload on a plain `ThreadPoolExecutor`.
  - Per-execution overhead for a graph of tiny nodes.
- Each scenario can be pointed at either side of the switch once the new side exists.
- The measure is proven, then frozen. The harness records its run-to-run variation. A run with a delay inserted on purpose into node execution is reported as slower by more than that variation. The scenarios, inputs and setup are then fixed in the repository. To show it, give the two result files and the comparison output.
- The repository holds a result file for the 1.x paths at the `2.0` branch point, with the machine and the Python builds named, including one conventional build and one free-threaded build.
