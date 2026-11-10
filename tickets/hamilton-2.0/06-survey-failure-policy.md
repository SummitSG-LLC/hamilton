Kind: question
Status: open
Depends on: 01
Claimed by:

# Survey: which failure policy should Hamilton 2.0 have?

## The question

Which outcome states can a task end in on Hamilton's new runtime, how does one state lead to another, and which of best-effort execution, retry and fallback belong in the first 2.0 release?

Answer it with a written report that compares how Dask, Prefect, Dagster, Airflow and the structured-concurrency libraries (`asyncio`, Trio and AnyIO) define these things, and that ends in a proposal for Hamilton and a list of decisions for the owner. The survey builds nothing.

## Why it matters

Ticket 07 defines the public contracts of the new runtime, and those contracts include the outcome data that execution backends, observers and the coordinator exchange. The outcome states in those contracts come from this survey's decision record. Every backend, every observer, the cache module and the conformance checks of Tickets 10 to 16 are then built on those states. A wrong or incomplete set is cheap to fix in a report and expensive to fix after the contracts are in use.

The outline says why the states cannot be added one feature at a time: "Sync/async nodes, dynamic map/collect, cancellation, retries, and graceful failure share task identity and state transitions. Design them together." This plan's prototype implements no best-effort mode, no retry policy and no fallback policy. Its contracts must still leave room for them, so the vocabulary has to be settled first.

## What's already known

- The outline names the contract each capability needs. Best-effort execution: "Successful, failed, blocked, skipped, and cancelled outcomes; partial-result reporting". Retry: "Attempt identity, limits, cleanup, and side-effect policy". Fallback: "Explicit substitution rules".
- The outline separates these from durable recovery: "Best-effort execution and in-process retries do not require durable execution-state persistence. Crash recovery does." Crash recovery is not part of this survey.
- The outline requires that runtime identity "distinguish a node definition from mapped task instances, retry attempts, and possible loop iterations".
- The outline warns that an optional function argument "means an input can be absent; it should not silently mean that an upstream failure is acceptable", and that runtime failure fallback is a different rule from build-time selection of a default producer and from input overrides.
- On structured concurrency the outline notes: "TaskGroup cancels siblings after an uncaught task failure, so best-effort execution must translate failures according to Hamilton's policy."
- Hamilton 1.x has one best-effort mechanism, `GracefulErrorAdapter` in `hamilton/lifecycle/default.py`. It catches one chosen exception type, puts a sentinel value in place of a failed node's result, and turns nodes downstream of a failure into no-ops. Its documentation says it is only compatible with the dict-based result builder. It depends on the task-based executor rewriting the callable of the Driver's own nodes during a run, which the new runtime will not do. Only this adapter was checked when this Ticket was written; look for retry or fallback behavior elsewhere in 1.x before you propose.
- The outline measured that on 1.x, when an async graph fails, an independent sibling still finishes after the graph reported failure (ten runs per build). It records this as current behavior, not as a promise.
- Later Tickets already rely on two states. Ticket 12 makes a failure cancel sibling work and leave nothing running, and Ticket 16's proof expects observers to see failed and cancelled outcomes.
- The outline lists "skipped" among the best-effort outcomes and also among the things runtime branching must define. Ticket 26 surveys runtime branching.

## Authority and intent

Dev-iL assigned this effort and chose this survey from this description: "Best-effort outcomes (failed, blocked, skipped, cancelled), retry, and fallback: how Dask, Prefect, Dagster, Airflow and structured-concurrency libraries define them, and a proposal for Hamilton." Each survey was offered and chosen as one that "ends with a written proposal and a decision for you to make; it builds nothing." The topic, the systems, the proposal, the decisions left to the owner, and that nothing is built are fixed by that choice.

The plan's working reading, which may be revised on evidence: `asyncio`, Trio and AnyIO stand for the structured-concurrency libraries; the six questions asked of each system are the ones Ticket 07 needs answered to define task outcomes; and the proposal gives states, transitions and a statement of which policies belong in the first 2.0 release.

Dev-iL decides every question the report lists; you recommend. This Ticket stays open until Dev-iL has decided and the decisions are written in a decision record. Dev-iL merges the pull request. The report may propose later work, but it does not assign that work. Where the report lives (the project keeps design write-ups under `writeups/`), its structure, the versions you compare, and the criteria you rank by are yours.

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
- **A survey's conclusions survive scrutiny.** Every key claim about another system cites that system's own documentation or source at a stated version, and the citation exists and says what it is credited with. A claim that rests only on a blog, forum or outdated page is flagged. Each facet is searched with more than one query formulation. Each system compared gets comparable depth. The question is examined from more than one frame (the plugin or pipeline author, the maintainer, the operator). Confidence is stated plainly where evidence is strong and limited where it is weak. Terms are defined once and used the same way for every option. Evidence against the proposal is sought and engaged, with the strongest counter-argument stated. The reasoning from evidence to proposal can be walked step by step. Gaps and assumptions are stated. The proposal is ranked against at least one alternative with explicit criteria. The pull request carries the report in place of proof runs.

## Watch out for

- The pull request changes no file under `hamilton/` or `tests/`, and does not change `pyproject.toml`. It adds the report with its proposal, and the decision record. It carries the report in place of the runs that a code change would show.
- The proposal is about the 2.0 release. This plan's prototype implements none of the three policies whatever the proposal says. Keep the two apart in the text, so that a reader does not take "belongs in the first 2.0 release" for "is built on the `2.0` branch now".
- The systems are different kinds of thing. Airflow, Prefect and Dagster are orchestrators with stored state and schedulers; Dask is a task scheduler; `asyncio`, Trio and AnyIO are concurrency libraries. The coordinator of Hamilton's new runtime runs in one process, and nothing keeps a run's state after the run. Words such as "skipped", "blocked" and "retry" mean different things in each. Define each term once, map every system's vocabulary to it, and use it the same way for every option.
- Several of these systems changed their state model between major versions. State the version for every claim, and cite the system's own documentation or source at that version.
- Do not let a proposal lean on stored state. Anything that needs state to survive the process is crash recovery, which is outside this survey.
- Retry is about side effects as much as about counting attempts. Hamilton graphs write through materializers, and the outline notes that reusing node outputs "does not by itself make external writes safe to resume". Say what each system assumes, and what Hamilton can assume.
- Say which meaning of "skipped" the report covers: a task not run because of a failure upstream, or a task on a branch that was not selected. Leave the semantics of branches to Ticket 26, and say what the two reports must agree on.
- Frame each question together with its counter-hypothesis, for example "Hamilton needs no blocked state because failed dependents can be derived". Look for evidence against your proposal and engage it.
- Go beyond the first satisfying source on the claims the proposal turns on. Seed follow-up searches with terms from the sources you found. Judge a source by what it is, not by its search rank. Trace corroborating sources upstream: several that repeat one origin count as one. Prefer stable or versioned pages, and verify niche citations harder.
- Keep real disagreement between systems open instead of forcing a consensus. Match the rigor to how novel the question is, and aim for a report the owner can decide from, not for a completed checklist.
- The survey was scoped as a comparison of documented systems that ends in a decision, not as novel research. If a decision needs more depth than that gives, state the gap in the report instead of widening the survey silently.
- Statements about Hamilton in the report must trace to the code, the same as statements about other systems trace to their sources.
- Each decision must be answerable: state the options, your recommendation, and what changes in Ticket 07's contracts with each answer.
- Give the decision record the next free number in the current month's series under `writeups/adr/`, skipping `2611-02` to `2611-09`; the records proposed upstream in apache/hamilton pull request #1809 use those. Follow `writeups/adr/README.md`.
- Do not post the proposal to the upstream discussion or anywhere on `apache/hamilton`. That is an outward-facing act that needs the owner's go.

## Definition of done

Fixed by the owner's choice of this survey, "Best-effort outcomes (failed, blocked, skipped, cancelled), retry, and fallback: how Dask, Prefect, Dagster, Airflow and structured-concurrency libraries define them, and a proposal for Hamilton", which "ends with a written proposal and a decision for you to make; it builds nothing":

- The report compares Dask, Prefect, Dagster, Airflow and structured-concurrency libraries on best-effort outcomes, retry and fallback. It proposes a failure policy for Hamilton. It lists the decisions the owner must make, each with a recommendation.
- The work adds only the report, its proposal and the decision record.

The rest is the plan's working reading, and may be revised on evidence as long as the result above holds:

- For each system compared, taking `asyncio`, Trio and AnyIO as the structured-concurrency libraries, the report states:
  - the outcome states a task can end in;
  - what happens to dependents of a failed task;
  - how partial results are reported;
  - how retries are identified and limited, and what they assume about side effects;
  - how fallback values are substituted;
  - how cancellation reaches running work.
- The proposal gives outcome states and their transitions for Hamilton, and says which policies belong in the first 2.0 release.
- The report's sources hold up, as the rule above on a survey's conclusions requires, and in addition: each facet was searched with more than one query formulation; the question is examined from more than one frame (the pipeline author, the maintainer, the operator); confidence is stated plainly where evidence is strong and limited where it is weak. A reviewer checks this by opening every citation behind the claims the proposal turns on, and a sample of the rest, and comparing each with its source.

The Ticket stays open until the owner decides:

- The owner has decided each question the report lists, and a decision record under `writeups/adr/` states those decisions. The owner must read the report and state a decision for each listed question; you then write the decisions into the record. The evidence is the record together with the owner's statement of the decisions it holds. When you close the Ticket, write on it where the report and the record are.
