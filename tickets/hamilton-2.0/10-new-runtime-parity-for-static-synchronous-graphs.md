Kind: shaped
Type: feature
Status: open
Depends on: 07, 09
Claimed by:

# Run every static synchronous graph on the new runtime that the 1.x default path runs

## Why

The outline's riskiest claim is that one runtime can replace today's three execution paths. Nobody can judge that claim until the new runtime runs what most users run: a static graph of synchronous functions, executed with `Driver.execute`. On 1.x that path calls nodes through one recursive function, so a linear chain of 1,500 nodes raises `RecursionError`. It also sets a low cost to match: 13 to 22 µs per node at the branch point.

Ticket 07 left a minimal coordinator that runs one graph through the public contracts. This Ticket grows it to parity with the 1.x default path. With the switch on, the ordinary `Builder`/`Driver` API runs every static synchronous graph on the new runtime with the same results, the same hooks and result builders, no recursion limit, state owned by each run, and no measurable slowdown. The measure is the existing core test suite, run a second time with the switch on.

## Authority and intent

Dev-iL assigned this effort and ruled that the new compiler and runtime are "reached through the existing Builder/Driver behind an opt-in switch. Old paths stay as the reference for behavior and speed comparisons." Dev-iL also ruled that "the adapters must be built in such a way that they're completely optional. The abstraction is more important than implementing the backends." Both rulings are in the rules below. Every item in this Ticket's definition of done is the plan's working reading of the outline, which names the existing test corpus as the baseline for comparing old and new and says "Keep a synchronous fast path". That reading may be revised on evidence.

Dev-iL retains three things. Dev-iL must have accepted the runtime contracts of Ticket 07 before this Ticket starts; a merged Ticket 07 without that acceptance is not enough. Dev-iL alone can accept a synchronous path that measures slower than the 1.x default path. Dev-iL merges the pull request. The format of the exclusion file, how the switch-on run counts its tests, and the design of the bridge for 1.x hooks are yours to decide and report.

## Scope

Work inside `hamilton/runtime/`, the bridge that lets 1.x lifecycle hooks and result builders run on the new runtime, the switch-on branch of `Driver.execute`, a second run of the core suite in CI, one exclusion file, and migration instructions for each difference. Static synchronous graphs only. Leave to their own Tickets: `Parallelizable` and `Collect` (Ticket 11), coroutine nodes and `aexecute` (Ticket 12), the thread backend (Ticket 13), and making validation, materialization and caching tests pass (Ticket 14). Do not change the 1.x paths, and do not port any adapter that takes over node execution.

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

- The plan assumes the right bar for the new runtime is the existing core suite with the switch on, plus one exclusion file. The alternative, new tests only, was not taken. If the exclusion file grows long for ordinary `Driver` use, stop and report: the outline says a runtime that "cannot preserve useful existing semantics or acceptable synchronous overhead would require revisiting the design."
- The plan assumes 1.x lifecycle hooks and result builders run through a bridge, and that an adapter which takes over node execution is refused. The alternative was to require hooks to be rewritten. If the bridge cannot hold, report it; the fallback is to remove the bridge and give hooks migration instructions, and that is the owner's call.
- A silent fallback makes the whole comparison meaningless. With the switch on, a Driver runs on the new compiler and runtime or fails; no code path may quietly use `execute_subdag` or a 1.x executor. The count of tests that executed on the new runtime is the proof. See the count drop on a scratch change that ignores the switch before you trust it.
- The Driver's own default adapters in `hamilton/base.py` implement the legacy `execute_node` and only call the node directly. They must be accepted, with their result builder and type checks applied. Any other implementer of `do_node_execute`, `do_remote_execute` or `execute_node` must be refused. That test of who the adapter is belongs in the bridge; the runtime core must not branch on an adapter's identity.
- On 1.x, `do_validate_input`, `do_check_edge_types_match` and `do_build_result` allow one implementer each. The bridge has to keep that meaning for the adapters it accepts.
- Adapters in this repository that take over node execution include the cache adapter that `Builder.with_cache` attaches, `GracefulErrorAdapter`, `PDBDebugger`, the `CacheAdapter` in `hamilton/lifecycle/default.py`, and test adapters under `tests/lifecycle/`. Core tests that use them fail at build with the switch on and need entries. Caching entries name Ticket 14. `GracefulErrorAdapter` is best-effort execution, which the owner ruled out for the new runtime. The others are refused by design: list each with the reason "takes over node execution; refused by the new runtime", and make sure the migration document's switch-on section tells their users what to use instead.
- 1.x hooks receive 1.x objects: the node object, the function graph, the run's inputs and overrides. "The same arguments" means the bridge hands a hook values it can use the same way. State in the lifecycle tests how arguments are compared between the switch-off and switch-on runs.
- Every refusal and every exclusion entry is a difference a 1.x user would meet with the switch on. Each needs migration instructions in the document's section for the day the new compiler and runtime become the default, in this pull request.
- Static synchronous graphs take an inline path: no thread hop and no event loop. At 13 to 22 µs per node there is little room. Profile before you add a layer.
- The coordinator's correctness depends on the order of events. Model its design in scratch and check the model before you build. For two threads calling `execute` on one Driver, use a forced schedule where example tests cannot reach the failing order.
- Values can stay alive through places that are easy to miss: a last-result attribute, a stored exception's traceback, a per-run entry in a dictionary keyed by run id. The weak-reference test is there to catch them.
- Only the core suite runs twice. CI's integration and plugin steps keep running on the 1.x paths with the switch off. `AsyncDriver` ignores the switch; its tests are 1.x-only entries.
- For the speed comparison, fix the number of runs before you read a result, run both sides alternately, and ask of any gain why it is not double. A gain larger than the changed piece's share of the whole is a measurement fault until explained.
- The switch is the rollback for this work. Old and new run side by side, so nothing here needs a change to a 1.x path.

## Suggested approach

This is advice; discard it if you find better. Add the second CI run and the exclusion file first, with the whole suite listed, and shrink the file as tests pass. Replace recursion with a ready-work loop over the plan (the standard library's `graphlib` is a reference for releasing work when its prerequisites are done). Build the bridge next, driven by the lifecycle end-to-end tests run with the switch off and on. Take the measurements last, with the harness's execute scenarios pointed at each side of the switch.

## Definition of done

Nothing here is fixed by an owner ruling made for this Ticket alone; the owner's rulings on the switch and on optional adapters bind it through the rules. All items are the plan's working reading of the outline and may be revised on evidence.

The existing core suite passes with the switch on, except a listed set, and nothing falls back:

- CI on `2.0` runs the core suite twice, with the switch off and with it on.
- With the switch on, a `Driver` or `Builder` either runs on the new compiler and runtime or fails with an error that names what is unsupported. It never runs a 1.x path.
- The switch-on run reports how many tests executed on the new runtime.
- Every test passes except those in one exclusion file. Each entry names the test, the reason, and one of three things: the Ticket of this effort that will remove the entry; the rule that covers it (something the owner ruled out, or something the plan left out); or, for a test of an adapter that takes over node execution, that the new runtime refuses that adapter by design.
- Tests of `AsyncDriver` and of 1.x-only options (1.x executors and grouping strategies) are listed there as 1.x-only.
- No entry is for ordinary synchronous `Driver.execute` on a static graph, with or without a result builder, hooks, or the Driver's own default adapters.
- The pull request links the two CI runs and gives the reported count.

Existing hooks and result builders work unchanged, and node-execution takeovers are refused clearly. With the switch on:

- A Driver given 1.x node, graph and task lifecycle hooks and a 1.x result builder calls each hook with the same arguments as with the switch off. Each node's pre hook runs before the node and its post hook after it. Graph hooks run around the whole run. Nodes may run in any order that respects dependencies.
- The Driver's own simple adapters in `hamilton/base.py`, which call the node directly, are accepted, and their result builder and type checks apply.
- A Driver given any other adapter that implements `do_node_execute`, `do_remote_execute` or the legacy `execute_node` fails at build time with an error that names the adapter and the contract that replaces that method.
- The lifecycle end-to-end tests run with the switch off and on, and there are tests for the acceptance and for the refusal.

No recursion limit, no shared run state, no graph mutation. With the switch on, a test shows each of these:

- A linear chain of 1,500 nodes executes.
- Two threads calling `execute` on one Driver at the same time both get correct results.
- The compiled graph compares equal before and after any run.
- After `execute` returns, the Driver and the runtime hold no reference to that run's values or state. The test uses weak references to run values.

The synchronous path is not slower than the 1.x default path:

- The harness's default-path execute scenarios (1,000 nodes, 10,000 nodes, and tiny nodes) are measured for the 1.x default path and for the new runtime, as the rule on performance claims requires, and the pull request cites the harness output files.
- The verdict for each scenario is faster or no measurable difference.
- If one is slower, the pull request names the limiter, and this Ticket stays open until the gap is removed or the owner states that they accept it.
