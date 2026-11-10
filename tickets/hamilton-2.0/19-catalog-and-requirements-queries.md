Kind: shaped
Type: feature
Status: open
Depends on: 09, 17
Claimed by:

# Add a catalog, a requirements query and a versioned JSON artifact over the compiled graph

## Why

A person or an agent who wants to know what a Hamilton graph holds has to build a Driver today, with its adapters and its executor, and has to import the user's code every time. The questions are simple: which nodes exist once decorators and config are resolved, what a chosen output needs, and where each node came from. `list_available_variables()` and the upstream queries answer parts of them. `Driver.export_execution` writes JSON that has no schema version. The outline asks for a public read API of the graph: "a catalog of resolved nodes, including parameterized names, types, contracts, tags, docs, and provenance; requirements queries for selected outputs; and a versioned JSON artifact usable by docs, agents, and editors". It asks that these queries "work without constructing an executor", and notes that "reading an already-built catalog need not import" Python definitions. Ticket 09 produced the compiled graph, which holds what such an API needs. Ticket 17 recorded the owner's decision on the artifact's format. This Ticket adds the catalog, the requirements query and the JSON artifact, and measures what they cost at 1,000 nodes.

## Authority and intent

Dev-iL assigned this effort. No ruling of Dev-iL's fixes the wording of this Ticket's results; they are the plan's working reading of the outline passages quoted above and may be revised on evidence. One thing is not yours to revise: the artifact's format, its version field and the way it carries a value with no JSON form are Dev-iL's decision, held in the decision record Ticket 17 produced under `writeups/adr/`. Follow that record. If it leaves a case open, propose the extension at the top of the pull request description for Dev-iL to accept. Dev-iL merges the pull request. Yours to choose: the names and module layout of the read API, the result types of the queries, what the feature-library fixture computes, and which execution path records the run that the requirements query is compared with.

## Scope

A feature-sized, additive change: a read API over the compiled graph, a writer and a reader for the JSON artifact, one fixture shaped like a feature library, and harness scenarios for the 1,000-node fixture. The API reads the compiled graph and changes nothing in it. `list_available_variables()`, `HamiltonGraph` and `Driver.export_execution` stay as they are. Out of scope: renderers and a driver-script emitter; an index of config variants or providers (the catalog describes one compiled graph, compiled for one config); declared config with types and defaults (the catalog carries the config snapshot the graph was compiled for); any change to how `@check_output` nodes are named or exposed (the catalog lists them as the compiled graph holds them); and wiring the catalog into the CLI, the language server or the MCP server.

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

- Loading an artifact must not import user code. A reader that unpickles, or that imports an object by its qualified name, breaks this. The subprocess test with the fixture modules made unimportable is the proof.
- Many catalog values have no JSON form: Python types, `Annotated` metadata, tag values, config values. Carry each the way Ticket 17's decision record states, and mark it. A serializer fallback that quietly turns anything into a string is the silent drop this Ticket forbids.
- "Answers the same catalog queries" needs a definition of equal for marked values. State it in the tests.
- Proving "without constructing a Driver, an adapter or a backend" takes more than reading the import list. Make the test fail if one of them is constructed.
- Two consumers can expect different types for the same external input. The query reports the types the consumers expect, not one type per input.
- A node supplied as an input or an override does not run. Say what the query assumes about inputs and overrides, and record the comparison run under the same assumption.
- This Ticket does not depend on the new runtime. If Ticket 10 has merged, record the comparison run with the switch on. If it has not, record it on the 1.x default path and say so in the pull request. The node sets must agree either way, apart from differences that Ticket 09's agreement test already lists with their reasons.
- If Ticket 11 has merged, the runtime already infers which graphs need mapping. Use that inference for "capabilities needed"; a second inference beside it will drift.
- The fixture includes `@check_output`. On 1.x, and in the compiled graph, validation is extra nodes produced at compile time. The catalog and the requirements query list those nodes; they do not fold them into the node they validate.
- `HamiltonNode.as_dict()` embeds the source text of a node's function. The catalog needs the source location, not the text. Artifact size is one of the things measured.
- The artifact carries the config the graph was compiled for, and config can hold credentials. Say in the docs that the artifact holds config values, so that a user knows before sharing one.
- A reader given an artifact with a schema version it does not know fails with a clear error. It does not guess.
- The cost numbers here are measurements, not comparisons: there is no old side. Add the scenarios to the harness from Ticket 03. Do not change the scenarios Ticket 03 froze.
- The read API is public API for callers outside `hamilton`, so the typing rule below applies to it.

## Suggested approach

This is advice; discard it if you find better. Build the fixture first: a small feature library with parameterized nodes, two config variants and one `@check_output`. Write the catalog over the compiled graph, then the writer and the reader with the subprocess test, then the requirements query with the recorded-execution test, then the harness scenarios.

## Definition of done

No part of this Ticket is fixed word for word by the owner. All three results are the plan's working reading of the outline and may be revised on evidence, as long as a reader can learn what a compiled graph holds and what chosen outputs need without an executor and without importing user code. The artifact's format comes from the owner's decision recorded by Ticket 17 and is not revised here.

**The catalog describes the resolved graph and round-trips without importing user code.** All of these hold:

- The catalog of a compiled graph lists every resolved node with its name (parameterized names included), type, `Annotated` metadata, tags, documentation and source location, plus the edges and the config the graph was compiled for.
- It serializes to JSON in the format of Ticket 17's decision record, and the JSON carries a schema version.
- A value that has no JSON form is carried in the way that record states and is marked as such. It is never dropped silently.
- A process that never imports the user's modules loads the artifact and answers the same catalog queries.
- Show it with tests on a fixture that has parameterized nodes, config variants and `@check_output`, and with a subprocess test that loads the artifact while the fixture modules are unimportable.

**Requirements for chosen outputs need no executor.** All of these hold:

- For a set of requested outputs, a query on the compiled graph returns the nodes that will run, the external inputs with the types their consumers expect, the config keys used, and the capabilities needed (such as mapping).
- The query constructs no Driver, no adapter and no execution backend.
- For the fixture above, the nodes the query names equal the nodes that execute.
- Show it with tests that compare the query's result with a recorded execution.

**Cost at a thousand nodes is measured.** The harness reports, for the 1,000-node fixture, the compile time, the catalog build time, the time of one requirements query and the artifact's size, each with run count, range, noise floor, machine and Python build. Show it with the harness output file.
