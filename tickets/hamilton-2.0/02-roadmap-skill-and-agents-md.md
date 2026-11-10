Kind: shaped
Type: docs
Status: open
Depends on: 01
Claimed by:

# Write the roadmap skill for 2.0 work and point `AGENTS.md` to it

## Why

Work on Hamilton 2.0 is split into Tickets under `tickets/hamilton-2.0/`, and contributors will hand those Tickets to their own agents. Today such an agent has no shared method. The repository has no `AGENTS.md`, no `.claude/` folder and no other context file, so each agent starts from the code alone. Left to itself, one agent bases 2.0 work on `main`, another removes a public name without telling users what to use instead, a third puts a backend inside the runtime core, and a fourth opens a pull request on `apache/hamilton`. This Ticket writes one skill that gives every contributor's agent the same method for picking, doing and handing over a 2.0 Ticket, and a root `AGENTS.md` that leads an agent to that skill.

## Authority and intent

Dev-iL assigned this effort and ruled on this Ticket in these words: "Generate a SKILL for working with the roadmap so that contributor's agents are aligned in their methodology", placed in "`.claude/skills/` plus AGENTS.md pointer". The skill, its place and the pointer are fixed by that ruling.

What "aligned in their methodology" means is the plan's working reading: the agent follows the rules this effort sets for all 2.0 work, which are the rules below, and shows it in the behaviors listed in the definition of done. That reading may be revised on evidence, for example when a trial shows that a different behavior matters more.

Dev-iL merges the pull request. Before `2.0` merges upstream, Dev-iL and the PPMC decide whether `.claude/skills/` and `AGENTS.md` stay; that decision is not yours. The wording and structure of the skill, what else `AGENTS.md` says, and how you build the scratch copy for the trial are yours.

## Scope

Two new files: `.claude/skills/hamilton-roadmap/SKILL.md` and a root `AGENTS.md`. Change the pre-commit configuration only if the license hook needs it (see below). No change to code, to tests, to the Tickets or to the front file. The seeded Tickets and everything else the trial creates live in a scratch copy and are not committed.

The two skills for moving changes between `main` and `2.0` belong to Ticket 27; do not write them here. The skills under `.claude-plugin/skills/` are for people who build dataflows with Hamilton; leave them as they are.

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

- The license hook for Markdown files inserts the full ASF header at the top of a file. A skill file must begin with its front matter. The project already exempts `.claude-plugin/**/SKILL.md` from the full header and gives those files a one-line SPDX comment after the front matter instead. A skill under `.claude/skills/` is not covered by that exemption. Extend the exemption to it, and confirm that the skill still loads after the hooks ran.
- When this Ticket runs, `docs/migration-to-2.0.md` (Ticket 04) and `hamilton/runtime/` (Ticket 07) may not exist yet, but the trial below asks for migration instructions and for a backend that attaches through a public contract. Seed the scratch copy with what the trial needs (a stub migration document and a stub contract are enough), and say in the pull request what you seeded.
- Every Ticket carries the effort's rules in full. The skill points an agent to the Ticket's own rules and does not restate them. A rule that lives in two places goes stale in one of them.
- Keep a line in the skill only when it carries a ruling of the owner, a fact the agent cannot get from the repository, or a default it has to counteract. A line the agent would derive from the Tickets or the code is noise in every session that loads the skill.
- Say what the skill does when it is called with no arguments. Keep the tone calm. Keep configuration out of the skill folder.
- The method spans several steps (pick, claim, branch, work, hand over). Have the skill make the agent write its state out as it goes, on the Ticket and in the branch, so that a session that stops halfway can be resumed by another.
- A `Claimed by:` line is visible only in the working copy and branch that holds it. `tickets/store-config.md` says how contributors agree on claims: through the pull request that changes the line, or by working from one shared checkout. The skill must not treat an unclaimed line in a stale checkout as proof that a Ticket is free.
- A Ticket is ready only when the owner has merged every Ticket it depends on into `2.0`. A finished Ticket moves to the `done` folder beside the open Tickets. The skill must make the agent read this from an up-to-date `2.0`, not guess it from Ticket numbers.
- Tickets 22 to 24 are 1.x work: their branches start from `main` of `apache/hamilton`, and their pull requests go there only after the owner's go. All other Tickets branch from `2.0` on the fork `SummitSG-LLC/hamilton`. Remote names differ between clones (`origin` and `upstream` in the owner's checkout); have the agent identify a remote by its URL.
- The flow of fixes between the lines is the plan's choice, recorded by Ticket 01 in `writeups/adr/`: a fix valid on 1.x goes to `main` as its own pull request and is cherry-picked into `2.0`; `2.0` takes `main` by merge, never by rebase. Link to that record. If the owner changes the flow, the skill changes with it.
- The Tickets live in the repository by the owner's permission and are removed before `2.0` merges upstream. If they move elsewhere, the skill's pointer to them must change in one place only.
- The trial agent must not be able to write to `apache/hamilton`. Run it in an isolated context on a scratch copy with no credentials for that repository, and judge the trial from the files and branches it left, not from its own account of what it did.

## Suggested approach

This is advice; discard it if you find better. Read the front file and three or four Tickets as a stranger would, and note each point where you had to guess. Write the smallest skill that removes those guesses. Run the trial. Cut every line the trial agent did not need, add what it lacked, and run the trial again with a fresh session.

## Definition of done

Fixed by the owner's requirement, "Generate a SKILL for working with the roadmap so that contributor's agents are aligned in their methodology", placed in "`.claude/skills/` plus AGENTS.md pointer":

- A roadmap skill is at `.claude/skills/hamilton-roadmap/SKILL.md`, a root `AGENTS.md` points to it, and an agent that reads only `AGENTS.md` opens the skill file. To show it, run a session that starts from `AGENTS.md` and record the files it opened.

The rest is the plan's working reading of that requirement, and may be revised on evidence as long as the result above holds:

- A fresh agent follows the shared method. Seed a scratch copy of the Ticket store with three Tickets: one ready Ticket whose work would remove a public name and add an optional backend, one Ticket whose dependency is not merged, and one Ticket for a 1.x fix. Give a fresh agent session only the repository on `2.0` and the request "work on the next Hamilton 2.0 item". The session must produce all of the following, judged from the files it opened and wrote and the branches it created, not from its summary:
  - It reads `tickets/hamilton-2.0/README.md` and the Tickets.
  - It claims the ready Ticket and not the blocked one.
  - Its branch for the ready Ticket is based on `2.0`. When sent to the 1.x fix, its branch is based on `upstream/main`.
  - Its change adds migration instructions for the removed name in the same branch.
  - Its backend lives outside the runtime core and attaches through a public contract.
  - Asked to add retry behavior, it writes a Ticket or a survey note instead of code.
  - It makes no call that writes to `apache/hamilton`.
- The skill is a sound prompt. It serves the purpose of the trial above and gives sufficient, consistent direction to a contributor's agent that has the repository but was not there when the plan was made. It states its goal, says what it does with no arguments, repeats no rule another file states, and holds no line an agent would derive from the Tickets or the code. This is judged by reading the skill file and `AGENTS.md` as prompts, line by line, and by checking that the change does what this Ticket states.
