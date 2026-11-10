Kind: shaped
Type: feature
Status: open
Depends on: 09, 17
Claimed by:

# Make the compiler report every defect as a structured diagnostic

## Why

Graph construction in Hamilton stops at the first defect it meets. It raises `ValueError`, or a decorator's own exception, with a message that has no code and no source line. A user whose module has five unrelated mistakes finds them one build at a time. A tool can tell one kind of defect from another only by matching message text. The outline asks the compiler to "Return stable diagnostic codes, source ranges, affected nodes, missing requirements", and names this contract as one "used by Driver construction". Ticket 09 added the compiler: it returns a compiled graph, records each node's source file and line, and reports a cycle at compile time. Ticket 17 recorded the owner's decision on the diagnostic format and the code scheme. This Ticket makes the compiler report defects as data: every independent defect in one pass, each with a code, a severity, a message, the node names involved and a source location. With the switch on, building a Driver from defective sources then fails with all of those diagnostics attached.

## Authority and intent

Dev-iL assigned this effort. No ruling of Dev-iL's fixes the wording of this Ticket's results; they are the plan's working reading of the outline passages quoted above and may be revised on evidence. One thing is not yours to revise: the code scheme, the severities and the diagnostic format are Dev-iL's decision, held in the decision record Ticket 17 produced under `writeups/adr/`. Follow that record. If it leaves a case open, propose the extension at the top of the pull request description for Dev-iL to accept. Dev-iL merges the pull request. Yours to choose: the names of the diagnostic types and of the exception, which code each defect gets within the scheme, the message texts, the order rule, and how the reference table is generated.

## Scope

A feature-sized change in four places: diagnostics in the compiler, the failure of Driver construction with the switch on, a generated reference table of codes in the docs, and tests with their fixtures. With the switch off, construction raises exactly what it raises on 1.x. The CLI, the language server and the MCP server are not touched here; Ticket 20 makes them report these diagnostics. No static analysis that avoids importing user code. No diagnostics for run-time failures.

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

- The compiler reuses the decorator pipeline, `resolve_nodes`, and that pipeline raises at the first defect in a function. Reporting every independent defect means the compiler goes on to the other functions after one fails.
- One defect can hide others or cause follow-on noise. A function that cannot become a node leaves edges pointing at nothing. Decide what "independent" means, write it in the docs, and do not report the follow-on of a defect as a second defect.
- 1.x raises several unrelated exception types for these defects: `ValueError` for a missing type hint, for two functions producing the same node and for mismatched edge types; `InvalidDecoratorException` and `MissingConfigParametersException` from decorators. A third-party decorator can raise anything. Whatever has no specific code gets the general code. An exception that escapes the compiler on user input is a failure of this Ticket.
- Two functions producing the same node is a defect only when module overrides are off. With `allow_module_overrides()` the later module wins by design, and no diagnostic is due.
- With the switch on, the exception type from Driver construction changes. Code that catches `ValueError` or `InvalidDecoratorException` around `Builder().build()` behaves differently. That is a difference that applies with the switch on, so its migration instructions go in the migration document's section for the day the new compiler and runtime become the default.
- If the core suite already runs with the switch on (Ticket 10 adds that run), tests that expect the 1.x exception types from construction will meet the new exception. Each such test either keeps passing or gets an entry in the exclusion file with its reason.
- With the switch on, a failed build never retries on a 1.x path.
- The same sources must give the same diagnostics in the same order on every run. Order by something stable, such as file, line and code. Iteration order of a set, and anything derived from memory addresses, is not stable.
- The exception message must hold no data values from inputs or config, only their keys and types. Some 1.x messages print values. Check every message text you carry over. The outline's words: "Avoid implicitly printing whole data values or query plans in type/contract errors."
- An unresolved annotation is a warning, not an error. Ticket 08's boundary keeps an unresolved name with its namespace and reports it as unknown without stopping the build; a node that depends on it still fails when it executes. Do not promote it to an error here.
- A node generated by a decorator can come from more than one function. Its diagnostic needs a location a user can act on.
- The reference table is generated from the code. A second list of codes kept by hand in the docs will drift. The docs build treats warnings as errors.
- A code is a promise once it ships: users filter and search on it. Follow what the decision record says about keeping codes stable.
- Ticket 20 feeds these diagnostics to three tools. Make a diagnostic plain data that turns into JSON without loss, so that no tool has to parse a message.
- The diagnostic types, the exception and the accessor for warnings on the Driver are public API for callers outside `hamilton`, so the typing rule below applies to them.

## Suggested approach

This is advice; discard it if you find better. Start with the fixture and a characterization test that records what 1.x does with each of the seven defects alone. Define the diagnostic type and the collector next, then convert one defect class at a time, each with its test first. Generate the reference table once two or three codes exist, so that the generator is exercised early. Wire Driver construction last.

## Definition of done

No part of this Ticket is fixed word for word by the owner. Both results are the plan's working reading of the outline and may be revised on evidence, as long as a user with several unrelated defects learns of all of them in one build, each with a code and a location. The code scheme and the severities come from the owner's decision recorded by Ticket 17 and are not revised here.

**One pass reports every independent defect with a code and a location.** All of these hold:

- Every defect in the user's sources or config that the compiler can meet is reported as a diagnostic with a code in the scheme of Ticket 17's decision record, a severity, a message, the node names involved, and a source file and line.
- A defect with no specific code gets a general code. It never surfaces as an uncaught exception.
- Independent defects are all reported in one pass.
- The same sources give the same diagnostics in the same order on every run.
- A reference table of codes in the docs is generated from the code.
- An unresolved annotation is a warning. The other six defect classes below are errors.
- The evidence set is one fixture with one defect of each of seven classes: a missing type hint; two functions producing the same node; an edge whose types do not match; a decorator missing a config key it requires; an invalid decorator use; a cycle; an unresolved annotation.
- Show it with the result of compiling the seven-defect fixture, a comparison of two runs, the generated table, and a search of the compiler for exceptions raised on user input that bypass diagnostics.

**With the switch on, Driver construction fails with the diagnostics attached.** All of these hold:

- Building a Driver from sources with at least one error-severity diagnostic raises an exception that carries all diagnostics as data.
- The exception's message lists the diagnostics with code and location.
- The exception includes no data values from inputs or config beyond their keys and types.
- Sources with only warnings build, and the warnings are reachable from the Driver.
- Show it with tests on the seven-defect fixture and on a warnings-only fixture.
