Kind: shaped
Type: feature
Status: open
Depends on: 10
Claimed by:

# Run `Parallelizable` and `Collect` graphs on the new runtime without the experimental flag

## Why

On 1.x a graph that uses `Parallelizable` and `Collect` runs only on the task-based path. The user must call `enable_dynamic_execution(allow_experimental_mode=True)` on the `Builder`, which swaps in a different executor. That path costs more for the same work: with the synchronous executor it measured 206 ms against 12.5 ms on the default path for 1,000 nodes. It rewrites the callables of the Driver's own nodes during a run. And the 1.x concept page for parallel tasks does not say what a `Collect[T]` parameter receives, in what order, what an empty expansion gives, or what one failed item does to the rest.

This Ticket makes mapping an ordinary capability of the new runtime. With the switch on, a `Builder` that never mentions dynamic execution builds and runs these graphs, the runtime works out from the graph that it needs to map, and the collection semantics are written in the docs and held by tests. Async work, threads and caching are later Tickets that build on the mapped-task identity and the in-flight bound defined here.

## Authority and intent

Dev-iL assigned this effort and chose the runtime set the prototype must prove, which includes "map/collect". Dev-iL also ruled that "best-effort, retry and fallback stay on the old path until feedback settles their semantics", which is why one failed item fails the whole run here. How mapping must behave is the plan's working reading of the outline: "Infer required execution capabilities from `Parallelizable`/`Collect` … Ordinary use should not require an experimental-mode flag", and "Specify the collection container, ordering, empty input, and failed-item behavior; use a documented list result for ordinary `Collect[T]`", with bounded fan-out and stable instance identity. That reading may be revised on evidence. Dev-iL merges the pull request. The form of a mapped task's identity, the name and default of the in-flight bound, and where the docs page sits are yours to decide and report, within the contracts Dev-iL accepted in Ticket 07.

## Scope

Mapping and collection in `hamilton/runtime/`, on the inline backend, behind the switch; a docs page for the semantics; tests; migration instructions. No thread or coroutine backend here (Tickets 13 and 12). No caching of mapped tasks (Ticket 14). Leave the 1.x task-based path, its executors and its grouping strategies as they are. The 1.x docs list three limits: one level of mapping, one `Collect` input per function, and one collect downstream of a mapping. This Ticket does not ask you to lift them; the outline says nested mapping "needs its own proof."

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

- On 1.x, a `Parallelizable` function may return a generator, and the executor replaces the node's callable with one that turns the generator into a list. The compiled graph cannot change, so the new runtime has to handle the generator without touching the node definition.
- No shipped backend lacks the mapping capability at this point: the inline backend must run mapped tasks itself. The message for a backend that cannot map therefore needs a backend defined in a test, through the public contracts only.
- `with_remote_executor`, `with_local_executor`, `with_execution_manager` and `with_grouping_strategy` are 1.x-only options. With the switch on they fail with an error that names what is unsupported, and their tests stay in the exclusion file as 1.x-only. They are not the "explicit backend choice" the definition of done speaks of; that means an execution backend of the new runtime.
- 1.x task hooks describe tasks as a 1.x grouping strategy cut them. The new runtime has no grouping strategy. The plan does not say what those hooks receive for a mapped graph. Follow Ticket 07's decision record, which maps every 1.x hook to a contract or says it has none, and report what the task-based lifecycle tests do with the switch on.
- Ticket 07's contracts give a task an identity that tells apart the node definition, a mapped instance and an attempt, and take their outcome states from Ticket 06's decision record. Use those; a failed item ends as failed and unfinished items as cancelled, in whatever words that record chose. Do not add an outcome state here.
- "The same across runs with the same input" rules out identities made from a counter shared between runs, a random value or an object's address.
- A bound on mapped tasks in flight is not a bound on memory: the collected list still holds every result. On the inline backend only one task is ever in flight, so testing the bound needs a test backend that can hold several.
- Cancelling unfinished items is an order-of-events problem. Model it in scratch and check the model before you build, and use a forced schedule where example tests cannot reach the failing order.
- Check what 1.x hands a `Collect` parameter, and in what order, before you write the docs. Any difference a 1.x user would see with the switch on needs migration instructions in the section for the day the new compiler and runtime become the default. So does `enable_dynamic_execution` having no effect.
- One fixture under `tests/resources/dynamic_parallelism/` uses the `@cache` decorator. Here it runs with no cache attached; caching on the new runtime is Ticket 14.
- Exclusion-file entries that name this Ticket are yours to remove. An entry you cannot remove gets a new reason that follows the file's rule from Ticket 10.
- The existing page `docs/concepts/parallel-task.rst` describes the 1.x path. Make each statement in the docs say which side of the switch it is about. Add the license header by hand to a new file under `docs/`.

## Suggested approach

This is advice; discard it if you find better. Have the compiler mark expanding and collecting nodes, and let the plan carry a map template instead of concrete tasks; the runtime expands it when the expanding node's value exists. Give each instance an identity built from the node name and the item's position. Release instances through the same ready-work loop as static nodes, with a counter that holds new instances back at the bound. Write the five semantics tests before the docs page, then write the page from the tests.

## Definition of done

Nothing here is fixed by an owner ruling made for this Ticket alone; the owner's ruling against best-effort execution binds it through the rules. All items are the plan's working reading of the outline and may be revised on evidence.

Mapping needs no experimental flag. With the switch on:

- A `Builder` that never calls `enable_dynamic_execution` builds and executes graphs that use `Parallelizable` and `Collect`.
- A `Builder` that does call it behaves the same; the call has no effect.
- An explicit backend choice that cannot run mapped tasks is reported at build or validation time, with a message that names the missing capability.
- The fixtures under `tests/resources/dynamic_parallelism/` run through `Builder`, and a test covers the message.

Collection semantics are documented and hold. A docs page states each of these, and a test confirms each:

- `Collect[T]` receives a list, in expansion order.
- An empty expansion gives an empty list, and downstream nodes run.
- One failed item fails the run and cancels unfinished items.
- Each mapped task has an identity that names its node and its item position, and the identity is the same across runs with the same input.
- The number of mapped tasks in flight never exceeds a configurable bound.
