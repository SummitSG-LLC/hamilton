Kind: question
Status: open
Depends on: 01
Claimed by:

# Survey: do runtime branching and bounded loops fit Hamilton, or do they stay with Apache Burr?

## The question

For each of two features, should Hamilton adopt it, defer it, or decline it and leave it to Apache Burr, and under which semantics if it is adopted?

1. Runtime branching: a value computed during a run decides which part of the graph executes. This needs a definition of an unselected branch, a skipped node, a join, and a requested output that lies on an unselected path.
2. A bounded loop: a subgraph repeats a limited number of times. This needs a definition of the state carried between iterations, of termination, and of the identity of each iteration.

The answer is one written report that compares skip, join and loop semantics in comparable systems and ends in a proposal and in decisions for the owner. It builds nothing.

## Why it matters

A Hamilton graph is a static directed acyclic graph: every node that will run is known before the run starts. `@config.when` chooses between implementations when the graph is built, and `Parallelizable` with `Collect` maps a block over items; neither chooses a path at run time. The project's README sends users who need loops or conditional logic to its sister library Apache Burr. A maintainer asked on the outline whether conditional path execution and a loop syntax in the function signature are possible, and added: "These would both require some API UX iteration and thinking before deciding they're worthwhile." The outline answers: "Branch and loop syntax should follow concrete examples and agreed semantics. Neither feature is an automatic 2.0 commitment". It lists "Runtime branch selection, skipping, joins, and requested outputs on unselected branches" and "Whether bounded loops or nested mapping belong in the first 2.0 release, and the carried-state/collection contracts if they do" among the items to settle before implementation scope is fixed.

This effort's new runtime implements neither feature on purpose: the rules below exclude runtime branching and loops until the owner decides from this survey. The answer reaches into the runtime's contracts whichever way it goes. The outline says runtime identity "must distinguish a node definition from mapped task instances, retry attempts, and possible loop iterations", and that branching needs rules for "cache behavior, and tracking" as well as for execution. A decision to decline is as useful as a decision to adopt, because it lets the contracts stay simpler.

## What's already known

- The outline on branching: "Branching needs explicit rules for unselected branches, skipped nodes, joins, requested outputs on unselected paths, cache behavior, and tracking. Keep configuration-time selection such as `@config.when` distinct from runtime branch decisions."
- The outline on loops: "Prototype a bounded loop over a subgraph, with explicit carried state, termination, cancellation, and iteration identity. An acyclic outer graph can retain a structured loop as one operation. Arbitrary cycles would change substantially more of Hamilton's dataflow model."
- The outline on scheduling: "Traversal order alone neither creates nor prevents conditional execution." The maintainer's comment suggested conditional paths are hard with depth-first traversal and possible with breadth-first; the outline's revision notes reply that breadth-first traversal alone does not supply those semantics. It also notes that Python's `graphlib.TopologicalSorter` cannot accept new nodes after preparation, so it is not a complete engine for dynamic mapping or branching.
- The README's Burr note reads, with its link markup removed: "Apache Hamilton is great for DAGs, but if you need loops or conditional logic to create an LLM agent or a simulation, take a look at our sister library Burr".
- The outline preserves a comparison of Burr and Hamilton from its June 2026 source, and says its statements about Burr "have not been re-verified for current Burr". Its points that bear on this question: Hamilton is a DAG whose full execution path is known up front, while Burr allows cycles, with unknown termination; Hamilton has no conditional transitions, so all executed nodes are known beforehand, while Burr allows conditional execution; Hamilton's model is dataflow with implicit state per node, while Burr's is a state machine with explicit state.
- On the 1.x paths every node is called through one recursive function, `execute_subdag`, depth first. The new runtime of this effort has one coordinator that releases work when its prerequisites are done, a plan that says what one run will do, and run state owned by each run.
- Ticket 06 surveys failure policy, and "skipped" is one of the task outcomes it covers. The outline's list of outcomes for best-effort execution is "Successful, failed, blocked, skipped, and cancelled".
- The owner's reply on the outline calls branch and join examples and the scope of bounded loops "the main control-flow questions left to settle".

## Authority and intent

Dev-iL assigned this effort and chose this survey from this description: "Skip, join and loop semantics in comparable systems, and whether they fit Hamilton or stay with Burr." Each survey was offered and chosen as one that "ends with a written proposal and a decision for you to make; it builds nothing." Those words fix the topic, the question of fit against Burr, and that the survey ends in decisions and changes no code.

The rest is the plan's working reading and may be revised on evidence: the list of semantics the report must state, that each is worked through a concrete Hamilton example, that the README's position is weighed both ways, the standard of scrutiny, and that the decisions are written into a decision record.

The owner retains every decision the report lists, and the merge. The owner's description does not name the systems, so which systems count as comparable is yours to choose and to justify, as are the method, the report's structure, and where the report file lives, outside `hamilton/`, `tests/` and `pyproject.toml`. Your recommendation proposes later work; it does not assign it.

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

- The survey adds only its report, its proposal and the decision record. It changes no file under `hamilton/` or `tests/`, and it does not change `pyproject.toml`. The outline speaks of prototyping a bounded loop; that prototype is outside this Ticket.
- State each question with its counter-hypothesis and look for evidence for it. The counter-hypothesis to adopting is the README's position: the two libraries are split on purpose, and a second way to branch or loop inside Hamilton would blur that split and cost every user a harder model.
- Burr's own semantics belong in the comparison, since the question is whether these features stay with it. The outline's statements about Burr come from its June 2026 source and are unverified since. Check each against current Burr at a stated version before you rely on it.
- Say why each system you chose is comparable to Hamilton, and give each comparable depth. A workflow orchestrator that schedules whole jobs and a dataflow library that calls functions in one process may use the same word for different things.
- Define each term once, such as skipped, unselected, join and iteration, and use it the same way for every system. If Ticket 06 has recorded its decisions when you write, use its outcome terms; if it has not, say which meaning of "skipped" you assumed.
- The Hamilton examples must be concrete: functions a user could write, the outputs requested, and what each node does under the proposed rule. An example that only names nodes A, B and C does not show whether the semantics fit Hamilton's authoring model, where a parameter name is a dependency.
- Keep build-time selection (`@config.when`) and mapping (`Parallelizable`, `Collect`) apart from runtime branching and loops in the report. Say for each example why the existing feature does or does not already cover it.
- Cite each system's own documentation or source at a stated version. Prefer stable or versioned pages, and check a niche citation harder than a well-known one. Go beyond the first satisfying source on the claims the proposal turns on, seed follow-up searches with terms from the sources you find, judge a source by what it is and not by its search rank, and trace sources that agree back to their origin: several that repeat one origin count as one.
- Where sources or maintainers really disagree, keep the disagreement open in the report; do not force a consensus.
- Look at the question as the pipeline author, as the maintainer and as the operator who runs and observes a graph.
- The plan treats this survey as a comparison of documented systems that ends in a decision, and not as novel research. If you find the decision needs more than that, say so in the report.
- Reading that splits cleanly by system can be handed to separate helpers; the comparison and the proposal need one author who has read all of it.
- Give the decision record the next free number in the current month's series under `writeups/adr/`, skipping `2611-02` to `2611-09`, which the records proposed upstream in apache/hamilton pull request #1809 use. Follow `writeups/adr/README.md`.
- Do not post a question on the upstream discussion, on an issue of `apache/hamilton`, or in the Burr project without the owner's go for that act.
- The pull request for this Ticket carries the report in place of proof runs.

## Definition of done

Fixed by the owner's choice of this survey, described as "Skip, join and loop semantics in comparable systems, and whether they fit Hamilton or stay with Burr", ending in "a written proposal and a decision for you to make":

- The report compares skip, join and loop semantics in comparable systems.
- It says, for each of branching and bounded loops, whether it fits Hamilton or stays with Apache Burr.
- It lists the decisions the owner must make, each with a recommendation to adopt, defer or decline.

The rest is the plan's working reading of the outline, which says "Branch and loop syntax should follow concrete examples and agreed semantics", and may be revised on evidence as long as the result above holds:

- The report states how the systems compared define each of these: an unselected branch, a skipped node, a join, a requested output on an unselected path, and a bounded loop's carried state, termination and iteration identity.
- It works each of them through a concrete Hamilton example.
- It weighs the project's stated position, that loops and conditional logic belong to Apache Burr (the README's Burr note), as grounds for and as grounds against.
- The report's conclusions survive scrutiny. Every key claim about another system cites that system's own documentation or source at a stated version, and the citation exists and says what it is credited with. A claim that rests only on a blog, a forum or an outdated page is flagged as such. Each facet was searched with more than one query formulation. Each system compared gets comparable depth. The question is examined from more than one frame: the pipeline author, the maintainer, the operator. Evidence against the proposal is sought, presented and engaged, with the strongest counter-argument stated. The reasoning that connects each piece of evidence to the proposal is written out and can be walked step by step. Confidence is stated plainly where evidence is strong and limited where it is weak. Gaps and assumptions are stated. Terms are defined once and used the same way for every option. The proposal is ranked against at least one alternative with explicit criteria. A reader checks this by opening every citation behind the claims the proposal turns on, and a sample of the rest, and by reading the report for symmetry, counter-evidence and gaps.
- The owner has decided each question the report lists, and a decision record under `writeups/adr/` states the decisions. The Ticket stays open until then. The owner must state a decision on each listed question; you then write the record from the owner's statement, and the record and that statement together are the evidence.
