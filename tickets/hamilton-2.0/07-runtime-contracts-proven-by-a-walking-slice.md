Kind: shaped
Type: feature
Status: open
Depends on: 01, 03, 05, 06
Claimed by:

# Define the runtime contracts and prove them with a walking slice

## Why

The riskiest claim of the outline is that one runtime can replace today's three execution paths. That claim stands or falls with the contracts between the runtime core and everything that attaches to it. In 1.x those roles are tangled: a lifecycle "method" such as `do_node_execute` allows one implementer only, the task-based executor rewrites the callable of the Driver's own nodes during a run, and the graph object stores adapters and uses them for type checks. An execution backend, a cache and an observer cannot be told apart by what they are allowed to do.

This Ticket defines the public contracts of the new runtime under `hamilton/runtime/` and proves them with the smallest slice that runs: a minimal coordinator with the inline backend, an execution backend that shares no memory with the coordinator, and a node-call wrapper, where the last two exist only in the tests. If a graph runs through contracts that only test code implements, the abstraction holds without the real backends. The contracts are also the least-reviewed design of this effort, so the owner reviews them here, before Tickets 10 to 16 build on them.

## Authority and intent

Dev-iL assigned this effort and requires: "the adapters must be built in such a way that they're completely optional. The abstraction is more important than implementing the backends." That requirement is fixed; the rule below on the runtime core states what it demands of the code.

How the responsibilities are split between contracts is the plan's working reading of the outline's "Separate result builders, materializers, validators, execution backends, and observers". One author derived that split, with no independent second derivation. Dev-iL's review may change it, and you may propose a better split on evidence.

Building a coordinator, a first set of conformance checks and an out-of-process test backend before the review, instead of stubs, is also the plan's choice. Contracts that nothing runs can only be inspected; a slice that runs through them, across a process boundary too, is evidence for the review. If the review changes the contracts, the slice is rework, limited to this Ticket.

Dev-iL retains acceptance of the contracts. This Ticket stays open until Dev-iL accepts them, and Tickets 10 to 16 do not start before that. A merged pull request is not acceptance. Dev-iL also merges the pull request. This Ticket itself starts only after Ticket 06 is closed with Dev-iL's decisions on the outcome states recorded.

Names, the module layout inside `hamilton/runtime/`, the form of each contract, and the spelling of the switch (if this Ticket is the one that adds it) are yours. Record the spelling of the switch where later Tickets will find it.

## Scope

A new package `hamilton/runtime/` with the contracts, the task and outcome data, a plan, run state, a minimal coordinator and the inline backend. The switch on `Builder` and `Driver`, if it does not exist yet. Tests, which hold the out-of-process backend, the node-call wrapper and the first conformance checks. One decision record. Additions to the typed consumer script and to the migration document as the rules below require.

The slice runs static synchronous graphs only. Everything else belongs to later Tickets: parity with the existing suite and the bridge that runs 1.x hooks and result builders (Ticket 10), map and collect (Ticket 11), the coroutine backend (Ticket 12), the thread backend (Ticket 13), validation, materialization and caching (Ticket 14), and the importable conformance kit (Ticket 15). With the switch on, a graph or option outside the slice fails with an error that names what is unsupported.

The out-of-process backend lives in test files and is not shipped. The rules below exclude a process-pool backend from the new runtime; this test backend only stands in for a Dask, Ray or Spark port. Task identity tells attempts apart, but no retry, best-effort mode or fallback is implemented. With the switch off nothing changes.

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

- The switch. The front file describes one switch: a `Builder` option for one Driver, and an environment variable for a whole test run. If it already exists on `2.0` when you start (Ticket 09 may have added it), use it; if not, add it here. There is one switch; do not add a second. The compiler belongs to Ticket 09. If it is not merged when you work, the slice runs a graph built by the 1.x build path on the new runtime, and Ticket 09 later puts graph building behind the same switch. In either case a switch-on Driver never falls back to a 1.x execution path, and `AsyncDriver` ignores the switch.
- The outcome states come from the decision record of Ticket 06. Do not invent a state here. If the contracts need something that record does not settle, ask the owner.
- This design is likely to change in review. Keep the slice minimal: add no option, layer or cache without a case that exists today.
- All three 1.x execution paths call nodes through one recursive function, `execute_subdag`, and a linear chain of 1,500 nodes raises `RecursionError`. Do not build the coordinator on it or on recursion through dependencies. Ticket 10 tests such a chain.
- The task-based executor rewrites the callable of the Driver's own nodes during a run, and `GracefulErrorAdapter` depends on that rewrite. The new runtime must never change the graph it runs. The contract for wrapping or replacing a node call is what takes that role.
- A 1.x lifecycle "method" (`do_node_execute`, `do_remote_execute`, `do_validate_input`, `do_check_edge_types_match`, `do_build_result`) allows one implementer only, and the Driver's own default adapters implement the legacy `execute_node`. The wrapper contract must let several wrappers compose in a stated order.
- The 1.x graph object stores adapters and asks them whether edge types match while it is built. The compiled graph of Ticket 09 holds no adapter, so type comparison needs an owner among the contracts.
- `hamilton/lifecycle/base.py` registers hooks, methods and two validators, some with synchronous and asynchronous variants. At the branch point the hooks are `pre_do_anything`, `post_graph_construct`, `pre_graph_execute`, `post_task_group`, `post_task_expand`, `pre_task_submission`, `pre_task_execute`, `pre_node_execute`, `post_node_execute`, `post_task_execute`, `post_task_return` and `post_graph_execute`; the methods are the five named above; the validators are `validate_node` and `validate_graph`. Read the registries when you do the work instead of trusting this list, and check the record's mapping against them with a test or a script.
- The plan assumes that 1.x hooks and result builders will run on the new runtime through a bridge (Ticket 10), and that an adapter which takes over node execution is refused with a clear error when the switch is on. The mapping in the decision record must be consistent with that. If the review shows the bridge cannot work, hooks get migration instructions instead.
- The plan keeps validation and materialization as graph nodes produced when the graph is built, as on 1.x, so that the runtime core needs no knowledge of them. The outline adds that "a validator can reject a result; a tracking failure should follow the observer's failure policy". The record must say where each sits.
- A backend that shares no memory forces the task data to be serializable. A task must not carry the coordinator, the run state or the Driver. The outline warns that a qualified function reference identifies an importable function but "does not make generated functions or closures universally serializable"; say in the contract what a backend may assume.
- The outline lists what must be settled about lifetimes: "Hook concurrency, observer failure policy, per-run state ownership, and resource lifetime across repeated/concurrent calls". It also says that "Static node metadata and per-run metadata should not share mutable storage", and that a shared scheduling contract "does not require an event loop or thread hop for every synchronous function". The inline path must hop to no thread and start no event loop.
- `@config.when` renames the user's function in place when a 1.x graph is built, and building twice is not idempotent. The slice's test builds from the same module with the switch off and on; choose its graph with that in mind.
- The correctness of a coordinator depends on the order of events. Model the design in scratch and check the model before building. Use generated call sequences or a forced-schedule test where example tests cannot reach the failing order.
- Sketch one structurally different split of the contracts before you settle, and keep the better. The record must state the alternative rejected, and a real second sketch is the honest source for it.
- Screen each contract for what the next contributor would copy: two ways to do one task, a list kept in sync by hand, state with two writers, a call order the signature hides. Make illegal states unrepresentable where you can.
- Tests exercise `Builder`/`Driver` and the public contracts, not internals. A test that reaches into the coordinator proves nothing about the contracts.
- The contracts are public API for callers outside `hamilton`. The rules below make the typed consumer script call each of them and keep the pyrefly baseline free of entries under `hamilton/runtime/`.
- Each refusal with the switch on is a difference from 1.x. It belongs in the migration document's section for the day the new compiler and runtime become the default.
- The benchmark harness of Ticket 03 lets a scenario select a side of the switch. Once the switch exists, check that the harness's selector works with it. Make no speed claim here; Ticket 10 measures the synchronous path.
- Give the decision record the next free number in the current month's series under `writeups/adr/`, skipping `2611-02` to `2611-09`; the records proposed upstream in apache/hamilton pull request #1809 use those. Follow `writeups/adr/README.md`.

## Suggested approach

This is advice; discard it if you find better. Start from the registries in `hamilton/lifecycle/base.py` and write the table of responsibilities: who may do what, and what happens when it fails. Sketch two splits and choose. Write the tests first: the out-of-process backend, the wrapper that replaces a node's result, and the first conformance checks, all against the contracts as you want them to read. Then write the smallest coordinator that makes them pass. Python's `graphlib.TopologicalSorter` shows ready-work scheduling and is a good reference, though it cannot accept new nodes after preparation. Add a test that fails when a module of the runtime core imports a module that is not part of the core; it keeps the rule below true from the first commit. Write the decision record, then ask the owner for the review and name the commit.

## Definition of done

Fixed by the owner's requirement: "the adapters must be built in such a way that they're completely optional. The abstraction is more important than implementing the backends." Everything below serves that requirement, and the rule above on the runtime core holds for this Ticket's code.

The rest is the plan's working reading, and the owner's review may change the split:

- The contracts are defined. `hamilton/runtime/` defines public, documented contracts that between them give one owner to each of these responsibilities:
  - where a task runs;
  - what may wrap or replace a node call, with several wrappers composable in a stated order;
  - who observes a run, and what happens when an observer fails;
  - how the final result is built;
  - how edge and input types are compared;
  - the task and outcome data the contracts exchange, where a task's identity tells apart the node definition, a mapped instance and an attempt, and outcomes use the states in the decision record of Ticket 06.
- A decision record states the contracts and does all of the following. A reviewer reads the contracts and the record, and checks that the mapping covers every name registered in `hamilton/lifecycle/base.py`.
  - It maps every 1.x lifecycle hook and method registered in `hamilton/lifecycle/base.py` to the contract that replaces it, or says it has none.
  - It says where validation and materialization sit.
  - It settles on which thread or task each observer call runs and whether calls can overlap.
  - It settles who owns and closes pools, clients and other resources across repeated and concurrent runs.
  - It states the alternative rejected.
- A graph runs through contracts that only the tests implement, in process and out of process. With the switch on, a `Builder`-built Driver executes a static synchronous graph and returns the same results as with the switch off. The suite holds all of the following, defined in test files using only the public contracts:
  - an execution backend that runs each task in another process after serializing it, and that executes every node of that graph;
  - a node-call wrapper that replaces one node's result without the node function running;
  - a first set of conformance checks that both the inline backend and the out-of-process test backend pass.
- To show the previous point, give the tests, and a scratch change that makes the coordinator bypass the wrappers, seen failing.

The Ticket stays open until the owner accepts:

- The owner has read the decision record and the contract definitions and said they accept them, or the changes they requested are applied and accepted. The evidence is the owner's acceptance, naming the commit it applies to. Until then Tickets 10 to 16 do not start.
