Kind: shaped
Type: feature
Status: open
Depends on: 12, 13, 14
Claimed by:

# Run one graph that combines the whole runtime set, and write the old/new report

## Why

The outline is a discussion post, and nobody can run it. Its riskiest claim is that one runtime can replace today's three execution paths. The outline names the proof it still lacks: "one graph combining async work, dynamic mapping, synchronous work, validation, cache reuse, materialization, and cancellation, with scoped resource cleanup". It adds that its own stress tests "do not constitute that combined proof". By now each capability runs on the new runtime by itself: static synchronous graphs (Ticket 10), map and collect (Ticket 11), coroutine nodes and `aexecute` (Ticket 12), threads (Ticket 13), and validation, materialization and caching (Ticket 14). Nothing yet shows them working together in one graph. Nothing yet tells a maintainer or user who did not follow the work how to try the prototype, what it does, where it differs from 1.x, and how fast it is. This Ticket adds both: the combined proof, and the report people give feedback on. The effort exists to reach this point.

## Authority and intent

Dev-iL assigned this effort and chose the runtime set "The outline's combined proof", in these words: "Sync, async, map/collect, `@check_output` validation, materialization, cache reuse, cancel-on-failure with resource cleanup." That list is fixed. Dev-iL also ruled what stays off the new runtime: "Dask/Ray/Spark adapters, process pools, best-effort, retry and fallback stay on the old path until feedback settles their semantics." The contents of the report are the plan's working reading of the effort's purpose, which is feedback on something people can run; they may be revised on evidence. Dev-iL retains three things: the merge; the decision whether the prototype is ready to show for feedback; and the go for every outward-facing act. Posting the report, or a link to it, on `apache/hamilton` is such an act. Yours to choose: what the graph computes, its node names, where the test module and the report live, and the report's structure.

## Scope

One test module with its fixture graph, and one report in the repository (the plan expects a docs page). No new runtime capability. If the combined graph exposes a defect in an earlier Ticket's work, fix it in its own commit with its own test; if the fix would be a project of its own, report it and leave it. The report summarizes and links what code and result files own (the exclusion file, the harness outputs); it does not copy them.

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

- The owner's acceptance of the runtime contracts (Ticket 07) comes before any work here. The Tickets this one depends on could not merge without it.
- The proof is the combination. Each capability already has its own tests, so a graph whose capabilities sit in unconnected parts proves nothing new. Make them depend on each other.
- The failure case is cancel-on-failure and nothing else. The rules below keep best-effort, retry and fallback out of the new runtime, so the injected failure must fail the run. Ticket 11 settled that one failed item fails the run and cancels unfinished items.
- Cancellation and cleanup depend on the order of events. If the sibling work has already finished when the failure is injected, the test passes without testing anything. Hold the unfinished work with an event the test controls, not with a sleep, and assert that it had started and had not finished.
- On 1.x the cache adapter always recomputes a `Parallelizable` node, so that the items it yields are versioned one by one, and it has separate default behaviors for loader and saver nodes. Find out what the cache module from Ticket 14 does with the expanding node and with the materializer on a warm run. A node that the cache recomputes by documented design is the one allowed exception to "a warm run recomputes nothing": name each such node and its reason in the test and at the top of the pull request.
- Count recomputation from a source the cache does not own, such as a counter the node functions increment. An assertion that reads the cache's own records would pass on a cache that reports wrongly.
- Caching in the combined proof is the cache module from Ticket 14, attached through the public contracts. The coroutine backend, the thread backend and the cache module are optional modules; the graph's test attaches them the way a user would, and the runtime core still names none of them.
- A performance verdict in the report must come from runs of both sides taken alternately on the same machine. The stored 1.x result file from Ticket 03 is a reference record. It is never one side of a comparison. A gain larger than the changed piece's share of the whole is a measurement fault until explained.
- The report covers the verdicts that exist when you write it. Tickets 19 and 21 measure things too and are not dependencies of this Ticket; if they have not merged, say that their measurements are not in the report.
- The outline says a combined runtime proof "that cannot preserve useful existing semantics or acceptable synchronous overhead would require revisiting the design". A long exclusion list for ordinary `Driver` use is that signal. If the evidence points that way, the report says so plainly. The report is for people deciding whether the direction is right, not a case for it.
- The reader has not followed the work. Fix the term for each concept before drafting and use it the same way throughout (compiled graph, plan, run state, execution backend, observer, the switch). Put the point of each section in its first sentence. State each fact once.
- "A reader following its instructions in a fresh environment" means just that. Follow your own instructions in a new environment, from the install to the run of the combined proof, before you call the report done.

## Suggested approach

This is advice; discard it if you find better. Design the graph so the capabilities meet: synchronous nodes feed an expanding node, the mapped items include coroutine nodes, a collect feeds a node with `@check_output`, a materializer saves the result, and cached nodes sit on both sides of the map/collect block. For the failure test, give one mapped item a failure the test triggers and give its siblings a context manager that records entry and exit. Write the report last, from the exclusion file and the harness output files, then hand the instructions to a fresh environment.

## Definition of done

Fixed by the owner's choice of the runtime set ("Sync, async, map/collect, `@check_output` validation, materialization, cache reuse, cancel-on-failure with resource cleanup"):

- One graph in the suite, run with the switch on through `Builder` and `aexecute`, contains synchronous nodes, coroutine nodes, a map/collect block, a validated node, a materializer and cached nodes.
- Tests on that graph assert correct results.
- Tests assert that a warm run recomputes nothing, except nodes the cache module from Ticket 14 recomputes by documented design, each named in the test.
- Tests assert that an injected failure in one mapped item does all four of these: it cancels unfinished work; it unwinds a context manager that a node holds; it closes what the execution backend created for the run; and it reaches observers as failed and cancelled outcomes.
- The evidence is the run of that test module.

The rest is the plan's working reading, and may be revised on evidence as long as a person who has not followed the work can still try the prototype and judge it:

- A report in the repository tells a maintainer or user who has not followed the work: how to install from `2.0` and turn the switch on; what the new compiler and the new runtime do today and what they do not; where behavior differs from the 1.x paths, summarizing the exclusion file; each performance verdict, stated the way the rule below on performance claims requires; the limits of the evidence; and the open questions on which feedback is wanted.
- A reader who follows the report's instructions in a fresh environment runs the combined proof. Show it by doing so and keeping the commands and output.
- The report agrees with the exclusion file and with the harness output files it cites.

The Ticket closes when the owner merges the pull request. Whether the prototype is then shown for feedback, and where, is the owner's decision and is not part of this Ticket.
