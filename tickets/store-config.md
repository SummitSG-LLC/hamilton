# Ticket store configuration

- **Venue:** files. Each effort is a folder under `tickets/`; each Ticket is one Markdown file in it; a finished Ticket moves to the effort's `done/` folder.
- **Location:** `tickets/` in this repository, on the `2.0` branch line only. It holds the Hamilton 2.0 effort (`tickets/hamilton-2.0/`). This folder is planning material: it is removed before `2.0` merges into `main` upstream.
- **Types:** the default set — bug, feature, refactor, docs, chore.
- **Claims:** a `Claimed by:` line in a Ticket is visible only in the working copy and branch that holds it. Contributors who work in parallel agree on claims through the pull request that changes the line, or work from one shared checkout.
- **Automation:** none configured. No Ticket carries an `Auto:` grant, so no Ticket is eligible for unattended execution.
