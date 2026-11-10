Kind: shaped
Type: feature
Status: open
Depends on: 18
Claimed by:

# Make the CLI, the language server and the MCP server report the compiler's diagnostics

## Why

Three tools tell a user whether their Hamilton code builds: the CLI's `validate` command, the MCP tool `hamilton_validate_dag`, and the language server. Each builds the graph in its own way and reports a failure in its own shape. The CLI logs a record with the exception's type and message text and exits. The MCP tool returns a list with the exception's type, message and traceback text. The language server catches every exception when a document changes and tells the editor nothing. None of them gives a code or a source line, and each stops at the first defect. The MCP tool's description says it checks the code "without executing the code", yet it builds a module from the code string, which runs that module's top-level code. The outline asks that "The same input/configuration should produce the same graph and diagnostics across tools", and that "An agent-facing validation tool must state which mode it used". Ticket 18 made the compiler report every defect as a diagnostic with a code and a location. This Ticket makes the three tools report those diagnostics, and makes each say how it compiled.

## Authority and intent

Dev-iL assigned this effort. No ruling of Dev-iL's fixes the wording of this Ticket's results; they are the plan's working reading of the outline passages quoted above and may be revised on evidence. The plan also reads the outline as saying that the three tools call the compiler directly, in place of building a Driver and reporting whatever it raises; that reading may be revised on evidence too. The diagnostic format and the code scheme are Dev-iL's decision, held in the decision record Ticket 17 produced, and are not revised here. Dev-iL merges the pull request. Publishing a new version of the language server package, or of any package, is an outward-facing act that needs Dev-iL's go. Yours to choose: the layout of the CLI's text output, how the MCP result carries the diagnostics, how each tool words its statement of the mode, and whether the three tools share one helper.

## Scope

Changes to the validation path of three tools: `hamilton/cli`, `hamilton/plugins/h_mcp` and `dev_tools/language_server`, with a test per tool on the seven-defect fixture that Ticket 18 added. Other CLI commands and other MCP tools change only where they share the validation path; if one still reports failures in the old shape afterwards, list it as debt in the pull request. Out of scope: an analysis mode that does not import user code (this Ticket states the mode used, it does not add a second mode); the editor extension's own interface; catalog or requirements queries through any tool.

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

- The CLI's `--json-out` is a global option today, given before the command name. Its `validate` command needs a context file, builds a Driver first, then checks an execution request from that file with `Driver.validate_execution`. That request check is a different thing from compile diagnostics. Keep it working.
- When a CLI command fails today, the error record goes to the logger and the process exits with status 1. Nothing is printed as JSON on failure, with or without `--json-out`.
- The CLI has tests for `build`, `view` and `version`, and none for `validate`. Add a characterization test for what `validate` does today before you change it.
- The MCP tool receives code as a string and builds a temporary module from it with `exec`. Its description is what an agent reads to decide whether to call it, so the claim that nothing is executed must go from the description as well as the output.
- The MCP helper that builds the Driver also turns on dynamic execution in experimental mode. Read why before you remove or keep it.
- Agents and tests read the MCP result's keys (`valid`, `node_count`, `nodes`, `inputs`, `errors`). A changed shape of `errors` is a breaking change and needs migration instructions.
- The language server builds a temporary module from the document's text on every change and keeps the last graph that built, which its graph view uses. Keep that. Publish diagnostics when compiling fails, and publish an empty set when the document is clean again; otherwise stale diagnostics stay in the editor.
- The language server is a separate distribution with its own `pyproject.toml`, tests and CI workflow. That workflow runs only when a file under `dev_tools/language_server/` changes. The package declares the core version it needs; once it calls the compiler, that floor no longer says what it needs.
- If the tools call the compiler directly, their output changes whether the switch is on or off. Those are breaking changes for today's users of the tools, so their migration instructions go in the main part of the migration document. If you tie a tool to the switch, say why in the pull request, and put its instructions in the section for the day the new compiler and runtime become the default.
- "The same locations" needs care. The CLI reads a file, the MCP tool a string and the language server an editor document, so the file identity differs by tool. The position within the source must agree. A module built from a string must report lines of that string. LSP positions count from zero and Python lines from one: convert at the tool's edge, and compare in one convention. Say in each test what is compared.
- No tool parses a message text. Each takes the code, severity, location and node names from the diagnostic data.
- Ticket 18 lets sources with only warnings build. Decide what each tool does for warnings only, say it in the tool's help or docs, and test it.
- The tools print diagnostics, never data values from inputs or config.
- Three tools that each compile in their own way are three places to fix the next bug. If the step is the same, give it one home.

## Suggested approach

This is advice; discard it if you find better. Write one small function that takes sources and config, calls the compiler, and returns the diagnostics with the mode used. Give each tool a thin layer from that result to its own output: text and JSON for the CLI, a result dictionary for the MCP tool, LSP diagnostics for the language server. Write the three tests against the same fixture and the same expected set of codes and positions, taken from the fixture's own annotations of where each defect sits and not from the compiler's output.

## Definition of done

No part of this Ticket is fixed word for word by the owner. Both results are the plan's working reading of the outline and may be revised on evidence, as long as one defective source gives a user the same findings whichever tool they use.

**The same source gives the same diagnostics in all three tools.** All of these hold:

- The seven-defect fixture from Ticket 18, given to the CLI's `validate` command, to the MCP tool `hamilton_validate_dag` and to the language server, yields the same diagnostic codes and locations from each.
- The CLI exits non-zero and prints the diagnostics as text and, with `--json-out`, as JSON.
- The language server publishes them as LSP diagnostics. It no longer discards the failure.
- Show it with a test per tool on the fixture that compares the sets of codes and locations.

**Each tool says which mode it used.** Each tool's output for a validation states that it compiled by importing or executing the module's top-level code. Show it with the three tools' outputs on the fixture.
