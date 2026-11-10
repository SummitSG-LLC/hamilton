Kind: shaped
Type: feature
Status: open
Depends on: 11
Claimed by:

# Add an optional coroutine backend and `Driver.aexecute`, with cancel-on-failure and cleanup

## Why

On 1.x a graph with coroutine nodes needs a separate `AsyncDriver`. Its `Builder` rejects `enable_dynamic_execution` and `with_materializers`, so async work cannot be combined with mapping or materialization. When one node fails, work beside it keeps going: in the outline's probe, ten runs out of ten per build, an independent sibling finished after the graph had reported failure. Nothing defines what is cancelled, what is cleaned up, or what a hook is told.

This Ticket adds an optional execution backend that runs coroutine nodes on the new runtime, and an explicit async entry point on the ordinary `Driver`: `await dr.aexecute(...)`. One graph can then mix synchronous nodes, coroutine nodes and map/collect. When a node fails, unfinished siblings are cancelled and fully unwound before the caller sees the error, and nothing the run created is left behind.

## Authority and intent

Dev-iL assigned this effort and chose the runtime set the prototype must prove: "Sync, async, map/collect, `@check_output` validation, materialization, cache reuse, cancel-on-failure with resource cleanup." The cancel-on-failure part of the definition of done is fixed by that ruling. Dev-iL also ruled that "the adapters must be built in such a way that they're completely optional", which is why the coroutine backend is a module outside the runtime core. The entry point is the plan's working reading of the outline, which shows `result = await dr.aexecute(["output"], inputs=inputs)`, calls it "a proposed API, not a current method", and says to "Avoid a return type that changes with the surrounding event loop." That reading may be revised on evidence. Dev-iL merges the pull request. How a user attaches the coroutine backend, where synchronous nodes run during `aexecute`, and the structure of the backend are yours to decide and report, within the contracts Dev-iL accepted in Ticket 07.

## Scope

One optional backend module outside the runtime core, the `aexecute` method on `Driver`, tests, and migration instructions. `AsyncDriver` is a 1.x path and stays untouched. No timeouts, no retry, no best-effort mode: the owner ruled those out for the new runtime, so one failure fails the run. Do not move coroutine work onto threads; the thread backend is Ticket 13. Async validators are Ticket 14's to prove.

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

- The runtime core must not import this module, and the inline path must stay free of an event loop. The rule that every adapter is removable is checked two ways: an import-graph test in the suite that fails when a runtime core module imports an adapter module, and a test run with the adapter module made unimportable, in which the runtime tests that do not use it still pass. Add this module to both, and see the import-graph test fail on a scratch import.
- `asyncio.TaskGroup` exists on Python 3.11 and cancels siblings after a failure, but it raises an exception group. The caller must see the node's own error. The outline notes the same translation need.
- Cancelling is a request. "Finished unwinding" means the run waits for each cancelled sibling to end, with its `finally` blocks and context managers run, before it raises. A sibling that takes long to clean up delays the error; that is the meaning asked for.
- A synchronous node that is already running cannot be interrupted. For it, cancel-on-failure means work that has not started does not start.
- The outline: "`asyncio.run()` cannot be nested in a running loop in the same thread, so a sync wrapper alone does not settle notebook and server behavior." Do not make `execute` hide an event loop to run coroutine nodes. With no backend able to run them, `execute` fails and names `aexecute`.
- What `aexecute` does with the switch off is not settled by the plan. Failing with a clear error that names the switch leaves the 1.x paths untouched. Say what you chose.
- With the switch on, `execute` on a graph with coroutine nodes becomes an error. Check what 1.x `Driver.execute` returns for such a graph, and add migration instructions to the section for the day the new compiler and runtime become the default.
- 1.x has async variants of some lifecycle hooks, which `AsyncDriver` separates from the synchronous ones. Ticket 07's decision record maps every 1.x hook to a contract or says it has none; follow it for hooks under `aexecute`. A 1.x post-node hook receives a success flag and an error. How a cancelled outcome reaches such a hook follows the outcome states of Ticket 06's decision record.
- "Tasks, pools and clients the backend created for the run" are the backend's to close. Ticket 07's decision record says who owns and closes resources across repeated and concurrent runs. Do not close what the user passed in.
- The in-flight bound for mapped tasks from Ticket 11 applies to coroutine tasks too.
- Correctness here depends on the order of events. Model the cancellation design in scratch and check the model before you build. Use a forced schedule where example tests cannot reach the failing order, such as a failure that arrives while a sibling is inside its cleanup.
- The outline's stress runs saw deprecation warnings for `asyncio.iscoroutinefunction` from existing code. The newest Python in the CI matrix is 3.15; use `inspect.iscoroutinefunction` in new code.
- The typed consumer script must call `aexecute` and still pass pyrefly.
- Tests of `AsyncDriver` stay in the exclusion file as 1.x-only. Entries that name this Ticket are yours to remove.

## Suggested approach

This is advice; discard it if you find better. Write the failure test first: a graph with a failing node and a slow sibling that records whether it completed and whether its cleanup ran, an observer that records outcomes, and a check of `asyncio.all_tasks()` after the call. Then build the backend so that each ready coroutine node becomes one task owned by the run, the coordinator awaits completions, and a failure cancels the rest, awaits them, reports outcomes to observers, closes what the run created, and re-raises the node's error. Add `aexecute` last, as a thin entry point over the same plan and run state that `execute` uses.

## Definition of done

Fixed by the owner's ruling that the runtime set includes "cancel-on-failure with resource cleanup". After one node fails during `aexecute`:

- Sibling work that had not finished is cancelled and has finished unwinding, its own `finally` blocks and context managers included, before the error reaches the caller.
- No task created by the run is pending afterwards.
- Tasks, pools and clients the backend created for the run are closed.
- Post-node and post-graph observers are called for the failed and for the cancelled work, with an outcome that says which.
- The error the caller sees is the node's error.
- Tests show this with a slow sibling that records whether it completed and whether its cleanup ran, an observer that records outcomes, and a check of `asyncio.all_tasks()` after the call.

The rest is the plan's working reading of the outline, and may be revised on evidence as long as the result above holds. With the switch on:

- `await dr.aexecute(outputs, inputs=...)` on a `Builder`-built Driver returns correct results for graphs that mix synchronous nodes, coroutine nodes and map/collect.
- `dr.execute(...)` always returns a plain result and never an awaitable.
- `execute` on a graph with coroutine nodes and no backend able to run them fails with an error that says so and names `aexecute`.
- A test shows each of the three.
