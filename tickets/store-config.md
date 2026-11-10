# Ticket store configuration

- **Venue:** files. Each effort is a folder under `tickets/`; each Ticket is one Markdown file in it; a finished Ticket moves to the effort's `done/` folder.
- **Location:** `tickets/` on the side branch `2.0-planning` of the fork `SummitSG-LLC/hamilton`, and nowhere else. That branch is `2.0` plus one planning commit that adds `tickets/` (and excludes it from the Markdown license hook), followed by bookkeeping commits. It is rebased onto `2.0` whenever `2.0` moves, and it is never merged into `2.0`, so `tickets/` never reaches `2.0` or `main`. It holds the Hamilton 2.0 effort (`tickets/hamilton-2.0/`). Read it with a worktree of `2.0-planning`, or with `git show origin/2.0-planning:tickets/...`.
- **Types:** the default set — bug, feature, refactor, docs, chore.
- **Claims:** a claim is a commit on `2.0-planning` that sets the Ticket's `Claimed by:` line, pushed to the fork before work starts; a push that is rejected because the branch moved means someone else changed the store, so fetch and look again. Status changes, state notes and amendments are commits on `2.0-planning` too. A pull request into `2.0` never changes a Ticket.
- **Automation:** none configured. No Ticket carries an `Auto:` grant, so no Ticket is eligible for unattended execution.
