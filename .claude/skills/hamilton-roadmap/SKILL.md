---
name: hamilton-roadmap
description: The shared method for Hamilton 2.0 work - find, claim, do and hand over one Ticket of the 2.0 roadmap on the fork SummitSG-LLC/hamilton. Use when asked to work on Hamilton 2.0, on the roadmap, on "the next 2.0 item", or on a numbered 2.0 Ticket, and before any change meant for the branch `2.0`.
argument-hint: "[Ticket number]"
---
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Working on a Hamilton 2.0 Ticket

Goal: every contributor's agent takes a Hamilton 2.0 Ticket from the store to a pull request the owner can land, by the same steps, and leaves enough state behind that another session can take over at any point. The owner is Dev-iL.

The Ticket you take is your contract. Its "Rules that must hold", "Watch out for" and "Definition of done" bind your work; this skill does not repeat them and only adds the steps around them. Where the Ticket and this skill disagree, follow the Ticket and say so when you hand over.

## What you were asked

- No arguments, or "the next item": resume your own unfinished work if there is any (step 1); otherwise pick the next ready Ticket (step 2), tell the person which one and why, and take it through steps 3 to 6.
- A Ticket number or file: take that Ticket. If it is not ready, or someone else holds it, say so and stop.
- A request that is no Ticket's work, or that the Ticket you hold does not cover: see the second item of step 5.

## Where things are

- Remotes: tell them apart by URL, because their names differ between clones (`git remote -v`). The fork, `github.com/SummitSG-LLC/hamilton`, holds `2.0` and the store. Upstream, `github.com/apache/hamilton`, holds `main`, the 1.x line. Below, `<fork>` and `<upstream>` stand for their names in your clone.
- The store, which holds the Tickets: `tickets/` on the branch `2.0-planning` of the fork, and nowhere else; a checkout of `2.0` has none. Read `tickets/store-config.md` there before anything else: it says how to read the store and how a claim is made. The effort's front file is `tickets/hamilton-2.0/README.md`, and finished Tickets sit in `tickets/hamilton-2.0/done/`. Keep a separate worktree of that branch for the store, and bring it up to date with the fork before each read and each edit. This item is the only place that says where the store is; if it moves, change this item.
- How fixes move between `main` and `2.0`, and what to do with your branch when `2.0` is rebased: `writeups/adr/2611-13-fix-flow-between-main-and-2-0.md`.

## 1. Resume

- Fetch both remotes first. A blank `Claimed by:` line or a missing `done/` entry in a stale checkout proves nothing.
- Look for work already under way for you or the person you work for: a Ticket whose `Claimed by:` line names one of you, its branch (step 4) on the fork or locally, an open pull request from that branch, and the Ticket's latest state note. If you find it, continue from the state note and the branch instead of starting again.

## 2. Pick

- Read the front file, then the open Tickets.
- A Ticket is ready only when the owner has merged every Ticket on its `Depends on:` line into `2.0`. A dependency counts as merged when its file sits in `done/`, or when its latest state note says its work is on `2.0` and you find that work on the fetched `<fork>/2.0`. Ticket numbers say nothing about readiness. When the store and `2.0` disagree, ask the owner instead of guessing.
- Skip a Ticket whose `Claimed by:` line is filled in, whose `Status:` is not `open`, or whose latest state note says it is done.
- Of the ready Tickets left, take the lowest number, unless the person named another.

## 3. Claim

- Claim before any other work, as the store's configuration (see "Where things are") says: one commit in the store that fills in the `Claimed by:` line with who you work for and the date, pushed to the fork. If the push is rejected, fetch and read the Ticket again; if someone else took it, go back to step 2. Never force-push the store's branch.
- If you cannot push to the fork, ask the owner to record the claim, and do not start until it is recorded.

## 4. Branch

- Name the branch `2.0-ticket-NN`, where NN is the Ticket's number, so that a later session finds it.
- Start it from the fetched `<fork>/2.0`. The repository's default branch is `main`, and tools start branches there unless told otherwise.
- The exception is work that a Ticket's scope sends to `main` of `apache/hamilton`, a 1.x fix: start it from the fetched `<upstream>/main` on a branch named `1.x-ticket-NN`. When the same Ticket also brings the change into `2.0`, that part gets its own `2.0-ticket-NN` branch from `<fork>/2.0`.
- Edit Tickets only in the store worktree. Before each push of a work branch, `git diff --stat <base>...HEAD -- tickets/` must print nothing.

## 5. Work

- Do the work the Ticket describes, under its rules.
- A request that falls outside the Ticket's scope, or that its rules rule out or leave out, does not become code, even when the person asks for it; only the owner can lift such a rule, and the ruling goes on the Ticket first. Write the request down instead and tell the person: as a note on the survey Ticket whose topic covers it, or as a new Ticket in the store, in the shape of the others, with the next free number, open and unclaimed, saying that the owner decides. Commit and push it in the store.
- Keep your state where the next session will look:
  - Commit to the work branch in small steps and push it to the fork. It is your branch: rewrite it only with `--force-with-lease`.
  - At each milestone (claimed and branched, blocked, pull request opened, waiting for the owner), add a state note to the Ticket in the store, written as the existing ones are: a bullet "State on YYYY-MM-DD: ..." under "Watch out for" that says what is done, what is left and where it is.

## 6. Hand over

- Go through the Ticket's rules and its definition of done one item at a time, and for each one show that it holds or say why it does not apply; an item you could not meet goes into the pull request's debt, not out of sight.
- Squash work-in-progress and fix-up commits into topic commits.
- Open the pull request into `2.0` on the fork: `gh pr create --repo SummitSG-LLC/hamilton --base 2.0 --head 2.0-ticket-NN`. With several remotes, `gh` prefers the one named `upstream`, which in many clones is `apache/hamilton`, so pass `--repo` to every `gh` command.
- Wait for CI on the pull request and fix what fails.
- Write the hand-over state note: the pull request, what is left, and what waits for the owner.
- Work that waits, for the owner's go on `apache/hamilton` or because you could not open a pull request, must still be resumable: push its branch to the fork (never to `<upstream>`), draft the pull request description, and put both in the state note.
- The owner merges. Once the pull request is merged, move the Ticket to `done/` in one commit in the store.
