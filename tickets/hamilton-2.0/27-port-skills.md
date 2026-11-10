Kind: shaped
Type: docs
Status: open
Depends on: 02, 09, 10
Claimed by:

# Write the forward-port and back-port skills for moving fixes between the 1.x line and `2.0`

## Why

Two lines receive changes at the same time: `main` upstream, which is the 1.x line, and `2.0` on the fork. `2.0` moves and replaces code that `main` still changes. Hint reads go into one boundary module (Ticket 08). The pandas and numpy pieces move to plugin modules (Ticket 21). APIs scheduled for removal start to fail (Ticket 04). The compiler and the runtime are new packages that sit beside the 1.x paths (Tickets 09 and 10). So a merge of `main` into `2.0` can apply without a conflict and still leave a fix in code that `2.0` no longer runs, or miss the place where that code now lives. In the other direction, a fix written on `2.0` may or may not be valid on 1.x, and preparing it for upstream must not publish anything without the owner's go. Without a shared method, each contributor's agent would handle these cases differently, and some would rewrite a shared branch. This Ticket adds two contributor skills, one for bringing `main` into `2.0` and one for taking a `2.0` change back to `main`, each good enough that an agent following only the skill carries a real port to a correct result.

## Authority and intent

Dev-iL assigned this effort and required: "Once the new architecture becomes clear, add developer-facing SKILLs for forward-/back- porting of fixes between 1.x and 2.0." That requirement fixes that both skills exist, where contributors' agents find them, and that they are written only once the architecture is in place, which the plan reads as after Tickets 09 and 10 are merged into `2.0`.

The rest is the plan's working reading and may be revised on evidence: that each skill is judged by a real port, and that each is a sound prompt. The fix flow the skills teach is also a planning choice the owner did not make personally: a fix valid on 1.x goes to `main` as its own pull request and is cherry-picked into `2.0`; `2.0` takes `main` by merge, never by rebase; a back-port is a cherry-pick or a re-implementation on a branch off `main`. Ticket 01 puts that flow on record under `writeups/adr/`. If the owner changes it, these skills are re-cut.

The owner retains the merge and the go for every act on `apache/hamilton`. The skills' names, structure and wording are yours to choose.

## Scope

Two skill files under `.claude/skills/` and one edit to the root `AGENTS.md` that points to both. No change to Hamilton's code, tests or packaging. The trial ports that prove the skills run on scratch copies; their branches are evidence to link from the pull request and are not merged. Do not restate the roadmap skill's rules or the fix-flow decision record in the new skills, and do not edit the roadmap skill to make room.

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

- Do not write the skills before Tickets 09 and 10 are merged into `2.0`. The commit that adds them must be later than both merge commits, and the pull request must show that.
- The roadmap skill (`.claude/skills/hamilton-roadmap/SKILL.md`) and the root `AGENTS.md` come from Ticket 02, which this Ticket depends on. This Ticket adds a pointer to `AGENTS.md` and must not repeat the roadmap skill, so it needs both files.
- `.claude/skills/` and `AGENTS.md` exist on `2.0` only; `main` has neither. A back-port moves the agent onto a branch off `upstream/main`, where the skill file is not in the working tree. The back-port skill must still work after that switch.
- The back-port skill must end at a prepared state: a local branch off `upstream/main` with its tests passing, and a drafted pull request description. It must make no call that writes to `apache/hamilton`, and it must report that the owner's go is waiting.
- The forward-port skill works on a shared, long-lived branch. `2.0` takes `main` by merge, never by rebase; no force-push; no push to a base branch. The merge happens on a work branch off `2.0` and reaches `2.0` through a pull request the owner merges.
- Check the rules of both skills for conflicts when two agents port at the same time: two merges of `main` on two work branches, a forward-port that brings in a fix another agent is cherry-picking, a back-port of a change that a forward-port is about to bring the other way. Each skill must say how an agent sees that a port is already under way.
- A clean merge is not a correct port. The forward-port skill must make the agent find, for each change `main` brings, whether `2.0` moved or replaced the code it touches, and carry the change to its new home. With the switch, one behavior can have two implementations on `2.0`, the 1.x path and the new compiler or runtime; a fix to one may be owed to the other.
- Where the merge brings a breaking change, the forward-port adds migration instructions in the same pull request. Where `main` and `2.0` differ on purpose, such as an old import path that warns on `main` and raises on `2.0`, `2.0` keeps its own state.
- A change is valid on 1.x only if it needs nothing that exists on `2.0` alone: the compiler and runtime packages, the hint boundary, a removed dependency, a removed API. The back-port skill must make the agent check this before it starts, and allow a re-implementation where a cherry-pick does not apply.
- Do not put a table of moved files into a skill. A list kept in sync by hand goes stale with the next Ticket. Tell the agent how to find where code went: the history of the file, the migration document, the decision records.
- Keep a line in a skill only where it carries an owner's ruling, a fact the agent cannot reach from the repository, or a default it must counteract. State the skill's goal. Say what the skill does when called with no arguments. Keep the tone calm. State one rule in one place. Keep configuration out of the skill folder.
- A port spans several steps and can be interrupted in the middle of a merge. Have each skill write its state out as it goes, so that a later session can resume.
- Judge the trial sessions on what they did, their branches, files and test runs, and not on their own account of it. Run each in a fresh agent context that has only the repository and the skill, on a scratch copy whose remotes cannot write to `apache/hamilton`.
- Skill files and `AGENTS.md` must be accurate: each factual claim traces to code or a named source. Their wording is judged as a prompt, by the last item of the definition of done.
- Before `2.0` merges upstream, the project decides whether `.claude/skills/` and `AGENTS.md` stay. Do not make the skills depend on anything else that will be removed before that merge, such as `tickets/`, without saying so in the skill.

## Suggested approach

This is advice; discard it if you find better. Once Tickets 09 and 10 are merged, compare `2.0` with `upstream/main` and note the kinds of difference a port meets: code moved, code replaced, code with a second implementation behind the switch, names that warn on one line and fail on the other. Write each skill around those kinds, not around today's file list. For the forward trial, good candidates are a change on `main` to hint resolution in `hamilton/node.py` (Ticket 22 is one) or to a pandas result builder in `hamilton/base.py`; if `main` holds no such change, construct a commit on a copy of `main`. For the back trial, pick a small fix on `2.0` that touches only code both lines share. Run both trials, read what the agents did, and cut every line of the skills that did not change what they did.

## Definition of done

Fixed by the owner's requirement, "Once the new architecture becomes clear, add developer-facing SKILLs for forward-/back- porting of fixes between 1.x and 2.0":

- `.claude/skills/` holds a forward-port skill, from the 1.x line into `2.0`, and a back-port skill, from `2.0` to the 1.x line.
- `AGENTS.md` points to both.
- Both were written after Tickets 09 and 10 were merged into `2.0`. Show this by comparing the commit that adds the skills with those two merge commits.

The rest is the plan's working reading, and may be revised on evidence as long as the result above holds:

- Forward: following only the forward-port skill, a fresh agent merges `upstream/main` into a branch off `2.0`, where `main` holds at least one change to code that `2.0` moved or replaced (a constructed commit on a copy of `main` if no such change exists). The change reaches its new home on `2.0`, the suite passes with the switch off and with the switch on, and migration instructions are added where the merge brought a breaking change.
- Back: following only the back-port skill, a fresh agent takes one change from `2.0` that is valid on 1.x, prepares it on a branch off `upstream/main` with its tests passing there, and makes no call that writes to `apache/hamilton`.
- Both sessions run in isolated contexts, and the result is judged from the resulting branches and test runs.
- Each skill is a sound prompt: it states its goal, says what it does with no arguments, gives rules that do not conflict when two agents port at the same time, repeats no rule the roadmap skill states, and holds no line an agent would derive from the repository. The pull request holds nothing beyond what this Ticket asks for.
