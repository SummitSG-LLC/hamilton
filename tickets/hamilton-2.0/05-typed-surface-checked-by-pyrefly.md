Kind: shaped
Type: chore
Status: open
Depends on: 01, 04
Claimed by:

# Check the package with pyrefly on every pull request and ship a typed wheel

## Why

Hamilton's functions carry type annotations, but nothing checks them and nobody outside can rely on them. No type checker runs on the package, so a wrong annotation is never noticed. The wheel ships no `py.typed` marker, so a user's type checker does not treat Hamilton as a typed package. The new packages of this effort (`hamilton/compiler/` and `hamilton/runtime/`) define public contracts that code outside Hamilton can implement; they should be checked from their first commit. This Ticket makes pyrefly judge every pull request into `2.0`, records the errors the existing code already has so that only new errors fail, and makes the wheel declare itself typed, with a small consumer script that proves a user's code type-checks against it.

## Authority and intent

Dev-iL assigned this effort and ruled: "Use pyrefly for typing." That pyrefly is the type checker for `2.0`, that no other type checker is added, and that it judges pull requests into `2.0` is fixed by that ruling. mypy, pyright and ty were not weighed against it.

The plan reads the ruling as including a typed surface now. The other reading, to record the checker and leave typing for a later plan, was not taken; if the owner meant that, this Ticket shrinks to the configuration and the decision record.

Scope and strictness are the plan's choice and may be revised on evidence: the whole `hamilton/` package is checked with pyrefly's `default` preset, no error kind is disabled for the whole project, errors that already exist go into one baseline file, and the new packages have no baseline entries. The alternatives not taken were the lenient `basic` preset, which misses a wrong argument type, and checking only the new packages. The reason is that a baseline makes strict checking of old code free, and new code is then checked properly. The cost, if the choice is wrong, is a baseline of about 1,300 entries that is noisy to maintain; a later change would then narrow the scope.

The typed wheel follows the outline: "Ship `py.typed` with meaningful coverage of the advertised surface", with "checked public signatures/examples".

Dev-iL merges the pull request. Where the configuration and the baseline file live, how the check is wired into the static-checks job, and where the consumer script lives (outside the package) are yours.

## Scope

The pyrefly configuration; the pin in the development dependencies; the baseline file and the documented command that generates it; the check in the static-checks job; the `py.typed` marker; a consumer script and the CI job that checks it against the installed wheel; one decision record; one entry in the migration document.

Do not fix the errors that go into the baseline; that is not this Ticket's work, and the 1.x paths are kept as they are. Change an existing annotation only where the consumer script cannot pass without it, and say so in the pull request. Do not add a second type checker. Do not revive the commented-out `[tool.mypy]` table in `pyproject.toml`.

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

- Unconfigured, pyrefly uses its lenient `basic` preset. A configuration that fails to set the preset checks far less and still passes. The scratch check in the definition of done (a string passed where `int` is annotated) is what shows the `default` preset is on.
- The error count depends on the environment. At the branch point, pyrefly 1.4.1 in the project's base development environment reported 1,289 errors with `default` and 151 with `basic`. Of the 151, 123 were under `hamilton/plugins/`, 27 in the core and 1 under `hamilton/experimental/`; 132 were unresolved imports, most of them optional integrations that the environment does not install. Generate the baseline in the environment the static-checks job uses, or entries will not match there.
- The baseline is tied to the checker's version. Pin an exact version, and document how to regenerate the baseline when the pin moves.
- The baseline records the errors at the commit this Ticket branches from, which is after Ticket 04. The counts above are from before it.
- Read how pyrefly matches baseline entries at the pinned version. If entries are keyed by line number, an unrelated edit to a 1.x file makes old errors look new. Choose a matching that survives ordinary edits, or document the cost.
- The regenerate command can also hide new errors: whoever reruns it absorbs them. Document the policy beside the command. The rules below already forbid a baseline entry for code a Ticket writes and any entry under `hamilton/compiler/` or `hamilton/runtime/`; an entry for 1.x code that a Ticket moves may move with it.
- The static-checks job runs the project's hooks through `prek`. pyrefly must see the project's installed dependencies to resolve imports, which a hook in its own isolated environment does not. Whichever wiring you choose, the result must be one command that a contributor runs locally with the same outcome as CI, because the rules below tell every later Ticket to run the check "with the command and environment the static-checks job uses".
- The build backend is flit. The `[tool.setuptools.*]` tables in `pyproject.toml` are leftovers and do not decide what the wheel contains. Judge the marker by the built wheel's file list, not by the configuration.
- The consumer script must be checked against the installed wheel, not the source checkout. Run the check in a fresh environment from a directory outside the repository, as the installed-wheel job from Ticket 01 does; otherwise pyrefly resolves `hamilton` from the checkout and the marker proves nothing.
- `Driver.execute` is annotated to return `Any` at the branch point, and `Builder.build` returns `Driver`. The script asserts the types a user relies on as they are; it is not this Ticket's job to make them more precise.
- Later Tickets extend the consumer script: the rules below make each Ticket call every public function or class it adds for callers outside `hamilton`. Give the script a shape that grows without becoming one long file nobody reads.
- A typed wheel changes what users see: their type checkers now read Hamilton's annotations and may report errors in code that passed before. That is why the migration document gets an entry.
- Give the decision record the next free number in the current month's series under `writeups/adr/`, skipping `2611-02` to `2611-09`; the records proposed upstream in apache/hamilton pull request #1809 use those. Follow `writeups/adr/README.md`.
- Until this Ticket merges, no type checker is configured on `2.0`. Work done before then must say so instead of claiming that a type check passed.

## Suggested approach

This is advice; discard it if you find better. Add the pin and the configuration, run pyrefly in the static-checks environment, and generate the baseline with the command you then document. Wire the check into the static-checks job, open a scratch pull request with the wrong argument type to see it fail, and remove the break to see it pass. Add `hamilton/py.typed`, build the wheel and read its file list. Write the consumer script, check it against the installed wheel in a fresh environment, break the return annotation of `Builder.build` in scratch to see the check fail, then add the CI job. Write the decision record and the migration entry last.

## Definition of done

Fixed by the owner's ruling, "Use pyrefly for typing.":

- The type checker for `2.0` is pyrefly, no other type checker is added, and it judges pull requests into `2.0`. A scratch commit that passes a string where a core function's parameter is annotated `int` makes the pull request's checks fail, and removing it makes them pass. To show it, link the two CI runs of a scratch pull request.

The rest is the plan's working reading, and may be revised on evidence as long as the result above holds:

- Old errors are recorded and new code starts clean. All of these hold, shown by running the check in the static-checks environment and by the configuration, the baseline file and the record:
  - pyrefly is pinned in the development dependencies and runs in the static-checks job.
  - The whole `hamilton/` package is in its scope, with the `default` preset and no error kind disabled for the whole project.
  - The errors pyrefly reports on `2.0` at the commit this Ticket branches from are recorded in one baseline file, generated by a documented command.
  - An error that is not in that file fails the check.
  - A decision record under `writeups/adr/` states the checker, the preset, the baseline policy, and that mypy, pyright and ty were not weighed.
- The wheel is typed, and a user's code type-checks against it. All of these hold, shown by the wheel's file list and the CI job's log:
  - The built core wheel's file list contains `hamilton/py.typed`.
  - A consumer script kept outside the package builds a Driver with `Builder`, calls `execute`, and asserts with `assert_type` the types it relies on from each call.
  - That script passes pyrefly with no errors when checked against the installed wheel in a fresh environment, and a CI job runs that check.
  - A scratch change that makes the return annotation of `Builder.build` wrong is seen failing the script's check.
  - The migration document tells users that their type checkers now read Hamilton's own annotations.
