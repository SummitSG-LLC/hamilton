Kind: shaped
Type: feature
Status: open
Depends on: 11
Claimed by:

# Add an optional thread backend whose coordinator blocks while workers run

## Why

On 1.x, mapped tasks run on threads through the task-based path, and that path has four measured problems. Its coordinator loop keeps polling while workers run: the outline measured 168 ms of main-thread CPU in a 169 ms run, against 2.70 ms in 140 ms for a plain `ThreadPoolExecutor` doing the same work. Its pool is created when a run starts and shut down when it ends, so two concurrent `execute` calls on one task-based Driver collide. Whether a task sees the caller's `ContextVar` depends on the Python build: unset in 16 of 16 worker observations on conventional builds, inherited in 16 of 16 on free-threaded builds. What works well must be kept: on free-threaded 3.14 the 1.x thread executor ran a 32-kernel CPU workload 3.04 times faster with four workers than sequentially.

This Ticket adds an optional execution backend for the new runtime that runs tasks on a thread pool. The coordinator blocks while nothing is ready. Every task sees the caller's context on every build. The pool belongs to the backend object, survives across runs and serves concurrent runs. The free-threaded speedup stays.

## Authority and intent

Dev-iL assigned this effort and ruled that "the adapters must be built in such a way that they're completely optional. The abstraction is more important than implementing the backends." That is why this backend is a module outside the runtime core and attaches only through the public contracts. Dev-iL also ruled that process pools stay on the old path; build no process backend. Every item in this Ticket's definition of done is the plan's working reading of the outline, which asks for "Completion signaling or blocking waits when no useful work is ready", "per-submission context propagation", and clear lifetimes for executor pools. That reading may be revised on evidence.

Dev-iL retains two things: only Dev-iL can accept a result on free-threaded Python that is slower than the 1.x multithreading path, and Dev-iL merges the pull request. How a user attaches the backend, how the pool is sized, and the backend's structure are yours to decide and report, within the contracts Dev-iL accepted in Ticket 07.

## Scope

One optional backend module outside the runtime core, tests that run on a conventional and a free-threaded build in CI, harness scenarios pointed at the new side, and migration instructions for any difference a user meets. The thread backend is something a user chooses; this Ticket does not make threads the default for any graph. The outline says "Keep threaded execution explicit." Leave the 1.x `MultiThreadingExecutor` and the plugin `hamilton/plugins/h_threadpool.py` as they are; neither is the new backend. No process pool.

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

- The runtime core must not import this module. The rule that every adapter is removable is checked two ways: an import-graph test in the suite that fails when a runtime core module imports an adapter module, and a test run with the adapter module made unimportable, in which the runtime tests that do not use it still pass. Add this module to both, and see the import-graph test fail on a scratch import.
- A coordinator that sleeps and polls still burns CPU and adds latency. Wait on completion signals. The harness's main-thread CPU probe is the measure; it comes from Ticket 03.
- On a conventional build, four workers on CPU work are slower than sequential: the outline measured 0.36 times on 3.14. So "faster than sequential" is asked only on a free-threaded build. The coordinator CPU comparison is a separate item and is not a wall-time claim.
- A native extension that is not free-threading-safe turns the GIL back on at import. "Confirmed disabled during the run" means the measured process checks `sys._is_gil_enabled()` after its imports and records the answer with the result.
- Do not rely on what a new thread inherits; that is what differs between builds. Give each task its own copy of the caller's context when it is submitted. Its own copy is also what keeps a value set in one task out of the others and out of the caller.
- Pool ownership and closing across repeated and concurrent runs are settled in Ticket 07's decision record. Follow it. The coordinator of a run must not occupy a worker of the pool it is waiting on, or two concurrent runs on a small pool can wait on each other forever.
- The in-flight bound for mapped tasks from Ticket 11 and the pool's size are two limits. Say in the docstrings how they combine.
- A thread count taken after close also counts threads other tests started. Compare with the count before the backend was created, or count the backend's own named threads.
- "Each structure the runtime shares between threads" needs a list. Write the list in the pull request and give each entry a forced-schedule test. Fewer shared structures is the better design: the outline has workers return outcomes while the coordinator owns readiness and task transitions.
- A forced schedule is a controlled interleaving, not a stress loop. The outline's stress runs passed while its forced schedule found a lost update in 80 of 80 attempts.
- On which thread an observer call runs, and whether calls can overlap, is settled in Ticket 07's decision record. 1.x hooks that run through the bridge were not written for overlapping calls.
- Free-threading does not make a user's shared objects safe. Two branches can still mutate the same object. That stays the user's contract; say so where the backend is documented.
- Model the design in scratch and check the model before you build: submission, completion, failure and close, with two runs interleaved.
- For every measurement, fix the number of runs before you read a result, run the sides alternately, and ask why the gain is not double: four workers gave 3.04 times, so name the limiter from a profile. A gain larger than the changed piece's share of the whole is a measurement fault until explained.

## Suggested approach

This is advice; discard it if you find better. Write the context tests and the concurrent-run test first, and run them on both builds. Build the backend as an object that owns a `ThreadPoolExecutor`, submits each task inside a copy of the caller's context, and reports each outcome to the coordinator through a queue or condition the coordinator blocks on. Make the backend closable and usable as a context manager. Then point the harness's four-worker CPU workload at it and take the three-way measurement.

## Definition of done

Nothing here is fixed by an owner ruling made for this Ticket alone; the owner's rulings on optional adapters and against process pools bind it through the rules. All items are the plan's working reading of the outline and may be revised on evidence.

The coordinator blocks while workers run:

- The harness's four-worker CPU workload is measured, as the rule on performance claims requires, for the 1.x task-based path, the new runtime's thread backend and a plain `ThreadPoolExecutor`, with coordinator main-thread CPU time reported for each. The pull request cites the harness output files.
- The new runtime's coordinator CPU time is lower than the 1.x path's by more than the noise floor.
- The pull request says where the new runtime falls between the two references.

Each task sees the caller's context:

- A `ContextVar` set by the caller of `execute` has that value inside every task on the thread backend, on both a conventional and a free-threaded build.
- A value set inside one task is not visible in another task or in the caller.
- The tests for both run on both builds in CI.

Concurrent runs and pool lifetime are defined:

- Two threads calling `execute` at the same time on one Driver with the thread backend both get correct results.
- The pool belongs to the backend object and survives across runs.
- Closing the backend releases its threads. A test checks the thread count after close.

Free-threaded Python keeps its speedup. On a free-threaded build, with the GIL confirmed disabled during the run:

- The 32-kernel workload with four workers on the new runtime is measured, as the rule on performance claims requires, against sequential execution and against the 1.x multithreading path on the same build. The pull request cites the harness output.
- The verdict against sequential execution is faster.
- The verdict against the 1.x path is faster or no measurable difference. If it is slower, this Ticket stays open until the owner states that they accept the slower result.
- A forced-schedule test covers each structure the runtime shares between threads.
