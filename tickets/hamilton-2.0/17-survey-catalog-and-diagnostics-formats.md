Kind: question
Status: open
Depends on: 01
Claimed by:

# Survey: which catalog format and which diagnostic format should Hamilton 2.0 use?

## The question

Which versioned format should Hamilton 2.0 use for the catalog of a compiled graph, and which format should it use for the compiler's diagnostics, including how diagnostic codes are named and kept stable? Answer it by comparing how established systems solved the same two problems, proposing a format for each, and listing the decisions the owner must make. The survey builds nothing.

## Why it matters

Build errors in Hamilton carry no code and no source line today, and the CLI, the language server and the MCP server each report them in a different shape. The outline asks the compiler to "Return stable diagnostic codes, source ranges, affected nodes, missing requirements, and useful correction information", and asks for "a versioned JSON artifact usable by docs, agents, and editors". Both formats become promises the day they ship: users filter and search on a diagnostic code, and other tools read the artifact. A format chosen without looking at systems that have lived with theirs for years repeats their early mistakes. Two Tickets wait for the answer. Ticket 18 gives every compiler defect a code in the scheme decided here. Ticket 19 writes the catalog as JSON in the format decided here. Neither can start until the owner has decided and the decisions are on record.

## What's already known

From the code at the branch point:

- Graph construction stops at the first defect. It raises `ValueError`, or a decorator's own exception, with a message and nothing else. A cyclic graph builds without error.
- The CLI logs a record with the exception's type and its message text, and exits with status 1. The MCP tool `hamilton_validate_dag` returns an `errors` list whose entries hold `type`, `message`, `detail` and the traceback text. The language server catches every exception when a document changes and reports nothing.
- Two descriptive outputs exist. `HamiltonNode.as_dict()` gives a node's name, tags, output type as a string, required and optional dependencies, the source text of its first originating function, its documentation and a version hash. `Driver.export_execution` returns JSON of the form `{"nodes": [...]}` built from it, with no schema version.
- Hamilton already emits OpenLineage events through `hamilton/plugins/h_openlineage.py`. That shows one existing mapping from Hamilton runs to one of the systems to compare.

From the outline:

- The public `HamiltonGraph` "is an inspection view, not a settled executable graph contract", and "A descriptive JSON graph also does not make its Python callables portable to another process or framework."
- "Loading Python definitions can execute module-level code; reading an already-built catalog need not import them."
- "Catalog inspection should not require installing every provider."
- Diagnostics should "Use bounded summaries of expected/actual types and contract differences" and "Avoid implicitly printing whole data values or query plans in type/contract errors."

What the two waiting Tickets need from the decision:

- Ticket 18 needs a code-naming scheme, the severities (it reports an unresolved annotation as a warning and other defects as errors), a general code for a defect that has no specific code, and the fields of one diagnostic: code, severity, message, node names involved, source file and line.
- Ticket 19 needs a catalog schema with a version field, and a stated way to carry and mark a value that has no JSON form. Python types, `Annotated` metadata, tag values and config values can all be such values.

Bounds this effort already set:

- The catalog describes one compiled graph, compiled for one config. A compiled graph holds node definitions, edges, tags, a config snapshot and source locations, and no adapter. An index of config variants or of available providers is not part of it.
- This plan leaves out declared config, a change to how `@check_output` nodes are named or exposed, a driver-script emitter and new renderers. The proposal may say how the format would grow to carry them. It must not depend on them.

## Authority and intent

Dev-iL assigned this effort and chose this survey from this description: "Versioned graph artifact and diagnostic codes: dbt manifest, OpenLineage, Dagster asset graph, SARIF, LSP diagnostics, ruff and rustc code conventions." Dev-iL chose each survey as one that "ends with a written proposal and a decision for you to make; it builds nothing." The topic, the seven systems and the shape of the result are therefore fixed. Adding a system is your call, provided it gets the same depth as the others. The list of questions the report must answer about each system is the plan's working reading of what Tickets 18 and 19 need, and may be revised on evidence. Dev-iL retains the decisions: the report recommends, Dev-iL decides each listed question. Dev-iL merges the pull request. Yours to choose: the proposal itself, each recommendation, the report's structure, and where the report lives in the repository.

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

- This is a comparison of documented systems that ends in a decision, not novel research. Match the depth to the decision. If a claim the proposal turns on proves harder to establish than expected, go deeper on that claim; do not widen the whole survey.
- Frame each question with its counter-hypothesis. For example: "Hamilton should adopt an existing format" against "Hamilton should define its own and map to others".
- Say for each system what job its format does before comparing. A format that records a run after it happened answers a different question from a format that describes a graph before it runs. The catalog describes a compiled graph before any run.
- Cite each system's own documentation or source at a stated version. These schemas change between versions, so prefer stable or versioned pages. Judge a source by what it is, not by its search rank. Flag any claim that rests only on a blog, a forum or an outdated page.
- Go beyond the first satisfying source on the claims the proposal turns on. Seed follow-up searches with terms from the sources you found. Trace corroborating sources upstream: several that repeat one origin count as one. Verify niche citations harder.
- Keep real disagreement open. Do not force a consensus the sources do not hold.
- Hamilton has needs the other systems may not share. Node names can be parameterized. A node generated by a decorator can come from more than one function. Types are Python objects. Reading an artifact must not import user code.
- Decide the terms before drafting (catalog, artifact, diagnostic, code, severity, location) and use each with one meaning for every option compared.
- Number the decision record with the next free number in the current month's series under `writeups/adr/`, skipping `2611-02` to `2611-09`: the records proposed upstream in apache/hamilton pull request #1809 use those. Follow `writeups/adr/README.md`.
- The decision record states what the owner decided. Do not write it as decided before the owner has said so; a draft that awaits the decisions must say that it awaits them.

## Definition of done

The question is answered when the report exists, the owner has decided each question it lists, and a decision record holds those decisions.

Fixed by the owner's choice of this survey ("Versioned graph artifact and diagnostic codes: dbt manifest, OpenLineage, Dagster asset graph, SARIF, LSP diagnostics, ruff and rustc code conventions", ending "with a written proposal and a decision for you to make; it builds nothing"):

- The report compares the dbt manifest, OpenLineage and the Dagster asset graph as graph artifacts.
- The report compares SARIF, LSP diagnostics and the ruff and rustc code conventions as diagnostic formats.
- The report proposes a versioned catalog format and a diagnostic format for Hamilton.
- The report lists the decisions the owner must make, each with a recommendation.
- The pull request adds only the report, the proposal and the decision record. It changes no file under `hamilton/` or `tests/`, and it does not change `pyproject.toml`.

The rest is the plan's working reading, and may be revised on evidence as long as the owner can still decide both formats from the report:

- For each artifact system, the report states how it versions its artifact, identifies nodes, represents edges, types and provenance, carries values that have no JSON form, and evolves its schema.
- For each diagnostic system, the report states how it assigns and stabilizes codes, represents locations and severity, and attaches fixes.
- The proposal gives a catalog schema with a version field, and a diagnostic schema with a code-naming scheme and severities.
- The report's conclusions survive scrutiny. A reviewer opens every citation behind the claims the proposal turns on, and a sample of the rest, and checks each against its source. All of these hold:
  - Every key claim about another system cites that system's own documentation or source at a stated version, and the citation exists and says what it is credited with.
  - A claim that rests only on a blog, a forum or an outdated page is flagged as such.
  - Each facet was searched with more than one query formulation.
  - Each system compared gets comparable depth.
  - The question is examined from more than one frame: the plugin or pipeline author, the maintainer, the operator.
  - Evidence against the proposal is sought, presented and engaged, and the strongest counter-argument is stated.
  - The reasoning that connects each piece of evidence to the proposal is written out and can be walked step by step.
  - Confidence is stated plainly where evidence is strong and limited where it is weak. Gaps and assumptions are stated.
  - Terms are defined once and used the same way for every option.
  - The proposal is ranked against at least one alternative with explicit criteria.
- The pull request description carries the report, or links to it, in place of proof runs.

Open until the owner decides:

- The owner has decided each question the report lists, and a decision record under `writeups/adr/` states the catalog format and the diagnostic code scheme decided. The evidence is the record and the owner's statement of the decisions it holds. Until the owner has read the report and decided, this Ticket stays open, and Tickets 18 and 19 do not start.
