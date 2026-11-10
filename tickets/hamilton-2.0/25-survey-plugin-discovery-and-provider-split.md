Kind: question
Status: open
Depends on: 01
Claimed by:

# Survey: how should Hamilton discover its plugins, and which integrations earn their own distribution?

## The question

Two linked questions, answered in one written report that ends in a proposal and in decisions for the owner. It builds nothing.

1. Which rules should Hamilton use to discover and load integrations through entry points: what happens when two plugins claim one name (collision), how a plugin and the core state and check which versions of each other they work with (compatibility), and how a plugin is loaded only when it is used (lazy loading)? The report answers this by comparing how pytest, Airflow providers and stevedore do it.
2. Which of Hamilton's integrations earn their own distribution, and which stay an extra of `apache-hamilton`?

## Why it matters

Today the core tries to import every integration it knows. Importing the decorator package calls `registry.initialize()`, which walks a fixed list of 21 names (`ExtensionName` in `hamilton/registry.py`) and imports `hamilton.plugins.<name>_extensions` for each, unless the environment variable `HAMILTON_AUTOLOAD_EXTENSIONS` is `0`. A third party cannot add an integration without a change to that list in the core, and a user pays at import time for integrations they do not use. The outline says: "Replace the eager attempts to import every known integration with discovery and explicit loading. Entry points supply the standard discovery mechanism; Hamilton still needs collision, compatibility, and registration rules." It adds that discovery should not need to import every heavy provider. The outline also lists, among the items to settle before implementation scope is fixed, "Which integrations need independent distributions/releases, and their supported core/Python ranges."

This effort's prototype leaves both out on purpose: the rules below exclude entry-point plugin discovery and any new provider distribution until the owner decides from this survey. The answer shapes later work: what the registry becomes, how the repository and its releases are split, and what a plugin author must write.

## What's already known

- The 21 names in `ExtensionName` at the branch point are: `yaml`, `matplotlib`, `numpy`, `pandas`, `plotly`, `polars`, `polars_lazyframe`, `pyspark_pandas`, `spark`, `dask`, `geopandas`, `xgboost`, `lightgbm`, `sklearn_plot`, `vaex`, `ibis`, `dlt`, `kedro`, `huggingface`, `mlflow`, `pydantic`.
- `load_extension` treats an extension as a dataframe extension unless the module sets `COLUMN_FRIENDLY_DF_TYPE` to false, and then requires `register_types`, `get_column_<name>` and `fill_with_scalar_<name>` in it. A failed import is logged at debug level and skipped.
- `hamilton/plugins/` holds more than the registry names. At the branch point it has 51 modules and two packages (`h_experiments`, `h_mcp`). Beside the `*_extensions` modules there are the `h_*` modules (adapters, hooks and integrations such as `h_dask`, `h_ray`, `h_spark`, `h_pandera`, `h_openlineage`, `h_opentelemetry`, `h_threadpool`), `jupyter_magic`, and Polars modules split by Polars major version.
- `pyproject.toml` already declares extras for some integrations and not for others. Four distributions besides the core are built from this repository: `apache-hamilton-ui`, `apache-hamilton-sdk`, `apache-hamilton-lsp` and `apache-hamilton-contrib`. The outline calls them "useful boundaries to retain".
- Conflicts already visible in `pyproject.toml` and the CI workflow: the `pyspark` extra caps pandas below 3.1; vaex ships wheels only up to Python 3.12 and pins older dask and pandas, so CI installs it outside the lock; ray has no wheels for Python 3.15; the Polars 1.x readers are tested in a separate CI step because the test group resolves Polars 2.x.
- The outline's position, to be tested and not assumed: "Keep `apache-hamilton` as the small core distribution"; "Separate providers when dependency conflicts, ownership, or release cadence justify a distribution; an optional extra alone can be enough for a small integration"; "Provider splits that do not earn independent dependency/release boundaries should remain extras"; "Separately released providers should declare and test supported core ranges"; "Catalog inspection should not require installing every provider."
- The outline points to Airflow as an example: per-package `pyproject.toml` files, provider dependencies and discovery entry points, generated metadata, and a root package that is a metapackage. It adds that Hamilton "does not need to copy that split if `apache-hamilton` itself can be the small core". It also points to the PyPA entry points specification.
- Measured at the branch point: `import hamilton.driver` takes 431 ms, of which pandas is 287 ms and numpy 78 ms. Ticket 21 removes pandas and numpy from the core on `2.0` and moves their pieces to plugin modules behind extras; it does not change discovery.

## Authority and intent

Dev-iL assigned this effort and chose this survey from this description: "Entry-point discovery rules (collision, compatibility, lazy loading) as pytest, Airflow providers and stevedore do it, and which integrations earn their own distribution." Each survey was offered and chosen as one that "ends with a written proposal and a decision for you to make; it builds nothing." Those words fix the topic, the three systems, the two outputs (discovery rules and the distribution verdicts), and that the survey ends in decisions and changes no code.

The rest is the plan's working reading and may be revised on evidence: that the proposal is grounded in each of Hamilton's own integrations, the standard of scrutiny the report must survive, and that the decisions are written into a decision record.

The owner retains every decision the report lists, and the merge. You choose the method, the report's structure, any further system you add to the three (give it the same depth), and where the report file lives, outside `hamilton/`, `tests/` and `pyproject.toml`. Your recommendation proposes later work; it does not assign it.

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

- The survey adds only its report, its proposal and the decision record. It changes no file under `hamilton/` or `tests/`, and it does not change `pyproject.toml`. A prototype of entry-point loading, however small, is outside this Ticket.
- State each question with its counter-hypothesis and look for evidence for it. For discovery: the fixed list with an opt-out is enough, and entry points add cost without a present need. For distributions: every integration stays an extra.
- Cite each system's own documentation or source at a stated version. The outline's links to Airflow point at its `main` branch, which moves; replace them with a tagged version. Prefer stable or versioned pages, and check a niche citation harder than a well-known one.
- Go beyond the first satisfying source on the claims the proposal turns on. Seed follow-up searches with terms from the sources you find. Judge a source by what it is and not by its search rank. Trace sources that agree back to their origin: several that repeat one origin count as one.
- Where sources or maintainers really disagree, keep the disagreement open in the report; do not force a consensus.
- Give each of the three systems comparable depth. A long section on the system you know best and a paragraph on the others fails the bar.
- Look at the question as the plugin author, as the maintainer and as the operator who installs and runs Hamilton. They want different things from discovery.
- "Dependency weight", "release cadence need" and "known conflicts" must be facts for each integration. Say how you measured or found each one, and give the date and versions.
- The registry names and the modules under `hamilton/plugins/` are two lists that only partly overlap. The report must cover both in full. Derive both from the code when you write, since either may have changed since this Ticket was written.
- The plan treats this survey as a comparison of documented systems that ends in a decision, and not as novel research. If you find the decision needs more than that, say so in the report.
- Reading that splits cleanly by system can be handed to separate helpers; the comparison and the proposal need one author who has read all of it.
- Give the decision record the next free number in the current month's series under `writeups/adr/`, skipping `2611-02` to `2611-09`, which the records proposed upstream in apache/hamilton pull request #1809 use. Follow `writeups/adr/README.md`.
- Do not post a question on the upstream discussion or on an issue of `apache/hamilton` without the owner's go for that act.
- The pull request for this Ticket carries the report in place of proof runs.

## Definition of done

Fixed by the owner's choice of this survey, described as "Entry-point discovery rules (collision, compatibility, lazy loading) as pytest, Airflow providers and stevedore do it, and which integrations earn their own distribution", ending in "a written proposal and a decision for you to make":

- The report compares how pytest, Airflow providers and stevedore handle discovery, collision, compatibility and lazy loading.
- It proposes discovery rules for Hamilton.
- It says which integrations earn their own distribution.
- It lists the decisions the owner must make, each with a recommendation.

The rest is the plan's working reading, and may be revised on evidence as long as the result above holds:

- The report lists every name in `registry.ExtensionName` and every module under `hamilton/plugins/`, with each one's dependency weight, release cadence need and known conflicts, and says for each whether an extra or a separate distribution fits and why. A reader checks this against `hamilton/registry.py`, `hamilton/plugins/` and `pyproject.toml`.
- The report's conclusions survive scrutiny. Every key claim about another system cites that system's own documentation or source at a stated version, and the citation exists and says what it is credited with. A claim that rests only on a blog, a forum or an outdated page is flagged as such. Each facet was searched with more than one query formulation. Each system compared gets comparable depth. The question is examined from more than one frame: the plugin author, the maintainer, the operator. Evidence against the proposal is sought, presented and engaged, with the strongest counter-argument stated. The reasoning that connects each piece of evidence to the proposal is written out and can be walked step by step. Confidence is stated plainly where evidence is strong and limited where it is weak. Gaps and assumptions are stated. Terms are defined once and used the same way for every option. The proposal is ranked against at least one alternative with explicit criteria. A reader checks this by opening every citation behind the claims the proposal turns on, and a sample of the rest, and by reading the report for symmetry, counter-evidence and gaps.
- The owner has decided each question the report lists, and a decision record under `writeups/adr/` states the decisions. The Ticket stays open until then. The owner must state a decision on each listed question; you then write the record from the owner's statement, and the record and that statement together are the evidence.
