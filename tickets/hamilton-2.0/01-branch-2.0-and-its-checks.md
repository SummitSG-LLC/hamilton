Kind: shaped
Type: chore
Status: open
Depends on:
Claimed by:

# Create the `2.0` branch on the fork and give it the checks `main` has

## Why

Work on Hamilton 2.0 needs a branch where every pull request is judged the way a pull request into `main` is judged. Today the core workflow (`.github/workflows/hamilton-main.yml`) runs only for pull requests into `main`, so a pull request into a `2.0` branch would run the contrib, LSP and SDK workflows but no core tests and no lint. Nothing checks free-threaded Python, and nothing checks that an installed wheel works outside the source checkout. This Ticket creates the branch and its checks, and puts the decisions this effort starts from on record, so that every later Ticket has something to be judged by.

## Authority and intent

Dev-iL assigned this effort and chose that `2.0` lives on the fork `SummitSG-LLC/hamilton` now and moves upstream later. GitHub Actions is enabled on the fork. Pushing the branch `2.0` to the fork is Dev-iL's act to approve: prepare the branch locally and ask before the push. The decisions to record are already made; this Ticket writes them down and does not reopen them. Which CI steps a free-threaded build can run is yours to find out and report.

## Scope

A branch, CI workflow changes, and five decision records. No change to Hamilton's code or packaging, apart from what a CI job needs to run. The first commit on `2.0` after the branch point is the planning commit that adds `tickets/`.

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

- Scheduled runs and the Slack notification in the core workflow must stay limited to `main`; a schedule runs only on the default branch, and a failure report for `2.0` would go to the wrong audience.
- The docs workflow and the UI backend workflow also filter on `main`.
- The pre-commit hook that inserts license headers runs on Markdown files. Ticket files begin with `Kind:` lines that tools read; either exclude `tickets/` from that hook or confirm the header does not break the reading of those lines.
- A free-threaded build may not be able to install every test dependency. A native extension that is not free-threading-safe turns the GIL back on at import, which is exactly what the job must detect.
- Number the new decision records with the next free numbers in the current month's series under `writeups/adr/`, skipping `2611-02` to `2611-09`: the records proposed upstream in apache/hamilton pull request #1809 use those. Follow `writeups/adr/README.md`.
- The project has no context file and no type checker on `main`. Ticket 05 adds the type checker.

## Suggested approach

This is advice; discard it if you find better. Cut `2.0` from `upstream/main`, add the planning commit, and ask the owner for the go to push. Add `2.0` to the branch filters of the core, docs and UI backend workflows. Add the free-threaded job and the installed-wheel job to the core workflow. Open a scratch pull request into `2.0` with one broken test to see red, then remove the break to see green, and link both runs.

## Definition of done

Fixed by the owner's choice: the prototype includes CI for the `2.0` branch.

- A pull request into `2.0` on the fork runs the static-checks job, every step of the test job on every Python version in the matrix (the integration and plugin steps included), and the docs build, as a pull request into `main` does. A scratch commit that breaks one core test makes the run fail, and removing it makes the run pass. Scheduled runs and Slack notification stay limited to `main`.

The rest is the plan's working reading of the outline, and may be revised on evidence as long as the result above holds:

- CI on `2.0` runs the core suite on a free-threaded CPython 3.14 build. The job fails if `sys._is_gil_enabled()` is true after the suite's imports; a scratch run with the GIL forced on is seen failing. Every test skipped because a dependency cannot be installed on that build is listed in one file, with the dependency named.
- A CI job builds the core wheel, installs it into a fresh environment in a directory outside the repository, and there builds and executes a small pure-Python graph through `Builder`.
- `writeups/adr/` holds one record each, in the project's format and listed in its index, for these five decisions, each with the alternatives rejected:
  - Python 3.11 stays the floor for 2.0. The record gives the download shares and their window from the effort's front file, the table of newer-Python features and their backports from the outline's section "Features usable without raising the minimum" as the benefit side, and both rejected alternatives (3.12, which would drop the 6.0% of installs on 3.11, and 3.14, which would drop about 85%).
  - No native code until a benchmark shows a bottleneck. The record gives the build, execute and import measurements from the front file, and notes that the release tooling assumes a pure-Python wheel.
  - The prototype is an end-to-end skeleton behind an opt-in switch, with the 1.x paths kept as the reference. Alternatives: foundations only; a standalone runtime proof.
  - The fix flow between the lines: a fix valid on 1.x goes to `main` as its own pull request and is cherry-picked into `2.0`; `2.0` takes `main` by merge, never by rebase; a back-port is a cherry-pick or a re-implementation on a branch off `main`.
  - The move to a `src/` layout is deferred to just before the 2.0 release, because the move changes every core path while both lines still receive changes.
