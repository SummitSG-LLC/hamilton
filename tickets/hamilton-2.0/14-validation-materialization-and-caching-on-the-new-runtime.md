Kind: shaped
Type: feature
Status: open
Depends on: 11, 12, 13
Claimed by:

# Make validation, materialization and caching work on the new runtime, with caching as an optional module

## Why

The proof the owner chose for the prototype needs three things the new runtime does not yet show: `@check_output` validation, materialization, and cache reuse. Until they work with the switch on, the core tests that use them sit in the exclusion file, and the combined proof of Ticket 16 cannot be built.

Caching is the hard one. On 1.x the cache is an adapter that takes over node execution, and the new runtime refuses such adapters, so `Builder.with_cache` cannot work with the switch on as it stands. The 1.x cache adapter also has measured defects. Two mapped tasks that write version entries for the same node can lose one: a forced schedule lost an entry in 80 of 80 attempts. It has no locks. It keeps a set of dictionaries per run that are never pruned.

This Ticket makes graphs with validators and materializers run on the new runtime as they do on 1.x, and adds caching for the new runtime as a separate module that attaches through the public contracts, reuses results across runs, invalidates correctly, loses nothing under threads, and releases what it keeps per run.

## Authority and intent

Dev-iL assigned this effort and chose the runtime set the prototype must prove: "Sync, async, map/collect, `@check_output` validation, materialization, cache reuse, cancel-on-failure with resource cleanup." Dev-iL also ruled that "the adapters must be built in such a way that they're completely optional. The abstraction is more important than implementing the backends." Those two rulings fix the first part of the definition of done: validation and materialization behave as on 1.x, and cache reuse works as an optional module. The rest (invalidation on a changed source, the forced-schedule result under threads, bounded per-run records) is the plan's working reading of the outline's findings, and may be revised on evidence. Dev-iL merges the pull request. How the cache module is structured, how `Builder.with_cache` attaches it with the switch on, and whether per-run records are released or bounded are yours to decide and report, within the contracts Dev-iL accepted in Ticket 07.

## Scope

For validation and materialization: whatever the compiler and the switch-on branch of `Driver` and `Builder` need so that the existing tests pass. They stay graph nodes produced at compile time, as on 1.x, and the runtime core gains no knowledge of them. For caching: one optional module outside the runtime core, attached through the public contracts, with tests and migration instructions. The 1.x cache adapter stays in place for the switch-off side; do not fix it here, its lost update is Ticket 23's. The plan leaves out any change to how `@check_output` nodes are named or exposed. Caching stays opt-in. No checkpointing, resume or recovery after a crash: the outline keeps cache reuse separate from those. No new fingerprinting or source-validity rules.

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

- Async validators. The definition of done says "sync and async". The core suite's async validator tests run through `AsyncDriver`, which is a 1.x path and ignores the switch, so those tests cannot show the new runtime. Ticket 12, which this Ticket depends on, adds `aexecute`: show async validators on the new runtime through it, with one `aexecute` test for each async-validator scenario the `AsyncDriver` tests cover.
- The same tests are in two lists. Ticket 10 lists `AsyncDriver` tests in the exclusion file as 1.x-only, and this Ticket says no test of its region remains there. Ticket 10's rule holds: a test that drives `AsyncDriver` stays listed as 1.x-only, and "none remains in the exclusion file" means every other test of this Ticket's region. Do not delete an entry for a test that never runs on the new runtime; give its scenario an `aexecute` counterpart instead.
- Build the list of region tests from a search over the core suite, not from memory. The search reaches files under `tests/plugins/` that need optional dependencies, and resource modules that tests import.
- On 1.x, materializers given to `Builder.with_materializers` or to `Driver.materialize` become nodes added to the graph after it is built. A compiled graph cannot change, so adding them means compiling a new graph.
- A failing validator raises and a warning validator logs. Validation can be switched off through the config when the graph is built. All of that happens in nodes the decorator pipeline produces, which is why the runtime core needs no knowledge of it.
- The 1.x cache adapter implements `do_node_execute`. The new module must do its work through the contract for wrapping a node call and the contract for observing a run, both from Ticket 07. `Builder.with_cache` and the Driver's `cache` property are written against the 1.x adapter class. Deciding which cache to attach belongs to the `Driver` and `Builder` code; the runtime core must not know that caching exists.
- The rule that every adapter is removable is checked two ways: an import-graph test in the suite that fails when a runtime core module imports an adapter module, and a test run with the adapter module made unimportable, in which the runtime tests that do not use it still pass. Add the cache module to both, and see the import-graph test fail on a scratch import.
- The outline says to "Reuse fingerprints/stores and fix concurrent updates." The stores, the fingerprinting and the cache keys under `hamilton/caching/` can serve the new module; the adapter cannot.
- The lost update on 1.x happens like this: both writers see that the node's dictionary is missing, one creates it and records its entry, then the other replaces it and records its own. The test here is against the new module on the thread backend from Ticket 13. It is a forced schedule, a controlled interleaving, not a stress loop: the outline's ordinary stress runs did not trigger the race. Ticket 23 fixes the 1.x adapter separately; do not depend on its fix being in `2.0`.
- Users read the cache after a run: its logs, versions and cache keys, by run. Releasing per-run records when the run ends can break that reading. A bound, such as keeping the most recent runs, may serve better. Whatever you choose, a reading that works on 1.x and not with the switch on needs migration instructions in the section for the day the new compiler and runtime become the default.
- Reuse for mapped tasks depends on the mapped-task identity from Ticket 11 being the same across runs with the same input. One fixture under `tests/resources/dynamic_parallelism/` combines mapping and the `@cache` decorator.
- "Its dependents recompute when its output changed" has a second half: when a node's source changes and its output does not, dependents need not recompute. Test both.
- Whether a cache directory written with the switch off is reused with the switch on is not settled by the plan. Say what happens.
- Take the expected values in the cache tests from counting node calls, not from the cache module's own records.
- Exclusion-file entries that name this Ticket are yours to remove.

## Suggested approach

This is advice; discard it if you find better. Start with validation and materialization: run the region's tests with the switch on, and fix what fails in the compiler or the Driver branch, not in the runtime core. Then build the cache module as a node-call wrapper that looks a result up by cache key and returns it without the node function running, plus an observer that records versions, with one lock or a per-run structure that makes the lost update impossible by construction. Wire `Builder.with_cache` to it for the switch-on side. Write the forced-schedule test before the fix for it, and see it fail on a version of the module that creates the per-node entry without protection.

## Definition of done

Fixed by the owner's rulings that the runtime set includes "`@check_output` validation", "materialization" and "cache reuse", and that adapters are "completely optional":

- Validation and materialization behave as on 1.x. They stay graph nodes produced at compile time, and the runtime core needs no knowledge of them. The region is every test in the core suite that uses `@check_output`, `materialize` or `with_materializers`. With the switch on, each of those tests passes, for failing and warning validators, sync and async, and none remains in the exclusion file. The pull request gives the list of those tests from a search and their run with the switch on.
- Cache reuse works on the new runtime as an optional module. With the switch on and caching attached through the public contracts, a cold run computes every node, and a warm run recomputes none except nodes the cache recomputes by documented design (on 1.x, a `Parallelizable` node, so that the items it yields are versioned one by one), each named in the test. The caching integration tests, run with the switch on, show it.

The rest is the plan's working reading of the outline's findings, and may be revised on evidence as long as the result above holds. With the switch on, a test shows each of these:

- Changing a node's source makes that node recompute, and its dependents recompute when its output changed.
- With the thread backend, a forced schedule of two mapped tasks writing versions for the same node keeps both entries in every one of 80 attempts.
- What the cache module keeps per run is released or bounded when the run ends.
