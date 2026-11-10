Kind: shaped
Type: feature
Status: open
Depends on: 12, 13
Claimed by:

# Complete the conformance kit, so that anyone can check an execution backend against the contract

## Why

The owner requires that every adapter of the new runtime is optional, and that the abstraction matters more than the backends built on it. A person outside the project can check that requirement only if they can take an execution backend they wrote, run a set of tests against it, and learn whether it keeps the execution-backend contract. Ticket 07 defined the contracts and added a first set of conformance checks, which the inline backend and an out-of-process test backend pass. Since then Ticket 11 added mapped tasks, Ticket 12 the coroutine backend and Ticket 13 the thread backend. Ticket 07 asked for a first set only. Nothing so far required that the set covers the whole contract, that it runs from outside the repository, or that it fails a backend that is wrong. This Ticket grows it into a complete kit: one check for every obligation the execution-backend contract documents, importable from the installed package, documented for a third party, passed by four backends, and failed by three backends broken on purpose.

## Authority and intent

Dev-iL assigned this effort. The requirement this Ticket serves is Dev-iL's, in these words: "the adapters must be built in such a way that they're completely optional. The abstraction is more important than implementing the backends." Dev-iL accepted the runtime contracts when Ticket 07 closed. This Ticket checks those contracts; it does not redesign them. Declaring a capability for a clause that cannot hold across processes is part of this Ticket. Any other change to an accepted contract is Dev-iL's to accept: name it at the top of the pull request description. Every result in the definition of done is the plan's working reading of how to make the requirement checkable, and may be revised on evidence. Dev-iL merges the pull request. Yours to choose: the kit's module name and layout, how a third party hands its backend to the kit, how a backend states its capabilities in code, and the wording of the failure messages.

## Scope

A feature-sized change that stays inside four things: the kit, its docs page, test-only backends (the three broken ones included), and the capability declarations the contract needs. No new execution backend ships. The coordinator and the three backends change only to fix a defect the kit finds, each fix as its own commit with its own test. The 1.x paths are not touched.

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

- The owner's acceptance of the runtime contracts (Ticket 07) comes before any work here. Tickets 12 and 13 could not merge without it, so merged dependencies imply it.
- The out-of-process test backend runs each task in another process after serializing it. It lives in test files, uses only the public contracts, and stands in for a Dask, Ray or Spark port. It is a test fixture. Shipping it as a usable backend would break the rule below against a process-pool backend.
- The kit uses only the public contracts. A check that has to reach into the coordinator's internals shows that the contract is missing something; fix the contract's documentation or report the gap, do not reach in.
- Nothing in the runtime core may import the kit, and the kit must not add a required dependency to the core. Say in the docs what a third party installs to run it.
- The kit ships in the wheel. Files that work from the source checkout are often missing from a built wheel, so run the kit against an installed wheel in a directory outside the repository.
- Work from the contract to the kit, not from the kit to the contract. List the documented obligations first, then map each to a check. An obligation that the kit checks but the contract does not document means the contract's documentation is incomplete.
- A check never seen failing proves nothing. See each check fail on a scratch break of the clause it covers before you rely on it. The three broken backends are the minimum, not the whole of this.
- Ordering obligations (a task starts only after its prerequisites finished; an outcome is reported once) depend on the order of events. An example test may never reach the failing order. Use generated call sequences or a forced schedule where an example cannot reach it.
- A silent skip looks like a pass. A clause that does not apply to a backend must show in the kit's output as not applicable, with the capability the backend did not state.
- A capability is something the backend states and the contract documents. It is not a branch on the backend's identity, in the kit or in the runtime core.
- Use the definitions earlier Tickets fixed: Ticket 11 defines the identity of a mapped task (its node and its item position, the same across runs with the same input); Ticket 13 defines what "the caller's context reaches a task" means for threads.
- The kit's entry points are public API for callers outside `hamilton`, so the typing rule below applies to them.

## Suggested approach

This is advice; discard it if you find better. Write the table of obligations from the contract's documentation before touching the checks. Turn the first set from Ticket 07 into the kit's public form, then add one check per missing row. Build each broken backend by wrapping a correct one and breaking one clause, so that it fails for one reason only. Build a scratch package outside the repository with a small backend of its own, install the core wheel beside it, run the kit there, and keep the commands and output for the pull request.

## Definition of done

No part of this Ticket is fixed word for word by the owner. All three results are the plan's working reading of the owner's requirement quoted above. They may be revised on evidence, as long as a person outside the project can still check a backend against the contract.

- **A third party can run the kit against its own backend, and the kit covers the whole contract.** The kit is importable from the installed package. Its docs show how to run it against a backend defined outside `hamilton`. Every obligation the execution-backend contract documents has a check in the kit. Examples of such obligations: tasks start only after their prerequisites finished; every outcome is reported once with the right state; a task's failure reaches the coordinator as that task's error; cancellation stops work that has not started; the caller's context reaches tasks where the backend declares it can carry it; the compiled graph is unchanged after a run; mapped instances keep their identities. Show it with a one-to-one comparison of the contract's documented obligations and the kit's checks, and with a run of the kit from a scratch package outside the repository against a small backend.
- **Four backends pass, including one that shares no memory.** The inline backend, the thread backend, the coroutine backend and the out-of-process test backend pass the kit. Where a contract clause cannot hold across processes, the contract declares it as a capability the backend states, and the kit reports that clause as not applicable; it never skips it silently. Show it with the kit's results for the four backends.
- **The kit fails backends that are wrong.** Three backends broken on purpose each fail the kit with a message that names the broken clause: one drops a task, one reports success for a failed task, one starts a task before its prerequisite finished. Show it with the kit's results for the three broken backends.
