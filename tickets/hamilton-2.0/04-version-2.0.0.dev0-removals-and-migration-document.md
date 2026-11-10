Kind: shaped
Type: chore
Status: open
Depends on: 01
Claimed by:

# Set the version to `2.0.0.dev0`, honor the removals 1.x promised, and start the migration document

## Why

The `2.0` branch still reports version 1.90.0. The 1.x line has told users that certain APIs stop working in 2.0: through the deprecation decorator with `fail_starting=(2, 0, 0)`, and through warnings, log messages, docstrings and comments that name 2.0. While the branch reports 1.90, none of those promises takes effect. The breaking changes of 2.0 stay invisible, and tests, examples and in-repository packages that still call the old APIs keep passing. There is also no place that tells a user how to move from 1.x to 2.0. This Ticket makes the branch declare itself 2.0, lets every promised change take effect with an error that says what to use instead, and creates the "Migration to 2.0" document that every later Ticket adds to.

## Authority and intent

Dev-iL assigned this effort and requires: "Incrementally build a 'Migration to 2.0' document. Whenever introducing a breaking change, add migration instructions." That the document exists from this Ticket on, and that each breaking change arrives with its instructions in the same pull request, is fixed by that requirement.

The rest is the plan's working reading and may be revised on evidence: the version string `2.0.0.dev0`; that each promise the 1.x line made is honored now; and the form of the document (its two parts and what each entry states).

Dev-iL merges the pull request. For each promised removal you choose between keeping the name as one that raises an error and deleting the name. Prefer keeping the name where a clear message can reach the caller that way: a user who skipped the warnings then learns the replacement from the error. Whether a softly worded sentence is a promise is your call; record the call.

## Scope

The version in its two places; the sweep of promised removals and default changes under `hamilton/`; the fixes that tests, examples run by CI and in-repository packages need because they call a removed API; one new docs page and its link in the table of contents; a rerunnable script or test that enumerates the promises.

Not in this Ticket: removing pandas and numpy from the core and changing the Driver's default result (Ticket 21 owns the pandas default); removing `typing_inspect` (Ticket 08); any part of the new compiler or runtime; any change to `requires-python`; publishing a package. Do not remove an API that the 1.x line did not schedule for 2.0.

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

- The deprecation mechanism in `hamilton/dev_utils/deprecation.py` compares only the first three parts of the version and ignores a pre-release part. The moment the version reads `2.0.0.dev0`, every API decorated with `fail_starting=(2, 0, 0)` raises. This is intended here. Expect the suite to fail right after the version change and treat each failure as an item of the sweep.
- The version lives in two places: the `VERSION` tuple in `hamilton/version.py`, and a literal in `pyproject.toml` whose comment says to keep the two in sync. `hamilton.__version__` is that tuple. Search for code that reads it and assumes three integers.
- `2.0.0.dev0` is a pre-release, and a resolver takes a pre-release only when asked. The in-repository packages (`ui/sdk`, `ui/backend`, `dev_tools/language_server`, `contrib`) require `apache-hamilton`, three of them with a lower bound. Confirm that each still resolves to the checkout in CI.
- At the branch point the decorator marks these for failure at 2.0.0: `telemetry.disable_telemetry`, `telemetry.is_telemetry_enabled`, `Driver.raw_execute`, and the decorators `parametrized`, `parametrized_input`, `parameterized_inputs`, `dynamic_transform`, `model` and `pipe`. This list is a starting point; the enumeration is yours and must be made by a script, not from this list.
- At the branch point, promises made in prose include: `FunctionGraph.get_impacted_nodes`; `display_graph=True` on the Driver's execute methods; the `PrintLnHook` alias in `hamilton/lifecycle/`; importing `hamilton.function_modifiers_base`; the module `hamilton.experimental.h_async`; the deprecated names in `hamilton.experimental.h_cache`; `CacheAdapter` in `hamilton/lifecycle/default.py`; `DiskCacheAdapter` in `hamilton/plugins/h_diskcache.py`; the Driver's private `_use_legacy_adapter` parameter; and a comment in `hamilton/models.py`. Some sentences are softer ("will likely be deprecating this in 2.0" in `hamilton/function_modifiers/configuration.py`; "In Hamilton 2.0, we will be using an asynchronous constructor" in `hamilton/async_driver.py`). List each in the enumeration with how you treated it, so that a reviewer sees nothing was dropped silently.
- `CacheAdapter` in `hamilton/lifecycle/default.py` is the old cache. The caching package under `hamilton/caching/` is a different thing and stays.
- The Driver's `_use_legacy_adapter` parameter decides whether a Driver without a result builder gets the pandas result builder. That is the pandas default, which Ticket 21 owns. List it with Ticket 21's number instead of changing it here.
- `Driver.raw_execute` has relatives. `AsyncDriver` defines its own `raw_execute`, and its `execute` calls it. `hamilton_sdk.driver.Driver` in `ui/sdk` overrides `raw_execute` and calls the parent's. `Driver.execute` itself uses a private method. Decide what happens to each relative, and remember that `AsyncDriver` is a 1.x path that must keep working.
- `tests/test_deprecation_schedules.py` already finds every use of the deprecation decorator in the syntax trees of the package, and asserts that deprecated APIs warn. Build the enumeration on it, and expect to change what it asserts.
- Several existing deprecations carry a `migration_guide` that points to a page on GitHub or on the published docs site. The errors must now name the migration instructions in the new document. The published site does not carry that page while `2.0` lives on a fork, so choose a reference that is right both now and after publication, and use the same form everywhere.
- For each removed name, search separately for calls, type references, string literals, dynamic imports, re-exports, tests, test resources, examples and docs. One search does not find them all. At the branch point, names due for removal appear in `tests/`, in `examples/` (for example `PrintLnHook` in `examples/hamilton_ui/run.py`), in `docs/reference/decorators/` and in `ui/sdk`.
- Before you remove a guard or a flag, read what it was for in its commit and pull-request thread.
- `2.0` takes `main` by merge. Each merge can bring a version change that conflicts with yours, and new deprecations that fail at once because of the version. Keep the enumeration as a check someone can rerun after every merge.
- `docs/` is excluded from the license hook. Add the ASF header to the new page by hand. The docs build runs Sphinx with warnings as errors (`.github/workflows/sphinx-docs.yml`), and the table of contents is in `docs/index.md`.
- An API that warned on 1.x and raises now is a breaking change under the rules below, as is a changed default and a changed error type. Each gets an entry in the document's main part, because each applies with the switch off.

## Suggested approach

This is advice; discard it if you find better. Run the project's checks before changing anything. Write the enumeration first and keep its output. Change the version, run the suite, and work through the failures one item at a time: decide raise or delete, migrate the callers in the repository, add a test that exercises the item, and write its entry in the document. Create the document with its two parts before the first entry, and put the point of each part in its first sentence.

## Definition of done

Fixed by the owner's requirement, "Incrementally build a 'Migration to 2.0' document. Whenever introducing a breaking change, add migration instructions.":

- `docs/migration-to-2.0.md` exists, and every breaking change this Ticket introduces has its migration instructions there, added by this Ticket's pull request.

The rest is the plan's working reading, and may be revised on evidence as long as the result above holds:

- `hamilton/version.py` and `pyproject.toml` both say `2.0.0.dev0`.
- No test, no example run by CI, and no in-repository package (`ui/sdk` included) calls an API whose removal is due at 2.0. To show it, run the project's checks from the rules above at the new version, and search the repository for each removed name.
- Every change promised for 2.0 took effect and says what to use instead. Enumerate the promises with a script when you do the work: every use of the deprecation decorator with `fail_starting=(2, 0, 0)` under `hamilton/`, and every warning, log message, docstring or comment under `hamilton/` that promises a removal or a changed default in 2.0. For each item:
  - A promised removal either raises an error that names the replacement and the migration instructions, or the name is gone.
  - A promised default change has taken effect.
  - The item has its migration instructions.
  - An item that another Ticket owns is listed with that Ticket's number. The pandas default belongs to Ticket 21.
- To show the previous point, give the enumeration script's output beside one test per item that exercises the item.
- The migration document is usable. `docs/migration-to-2.0.md` is linked from the docs table of contents. The Sphinx build with warnings as errors passes. The page has a main part, and a section for the day the new compiler and runtime become the default. Each entry states what changed, who is affected, the code before and after where code must change, and the error or warning that tells a user they hit it. This Ticket's removals are the first entries. To show it, give the docs build log; a reader then judges the page.
