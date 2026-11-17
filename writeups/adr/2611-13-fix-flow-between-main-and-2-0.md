<!--
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
-->

# 2611-13. How fixes flow between `main` and `2.0`

**Status:** Accepted (2026-11, a starting decision of the Hamilton 2.0 effort; the outline is apache/hamilton discussion #1645, "Hamilton 2.0: Architecture and Roadmap Reassessment"). Amended 2026-11-17 by the owner's ruling: while `2.0` lives on the fork, it is rebased onto `main`; once it moves to `apache/hamilton`, it takes `main` by merge.

## Context

While 2.0 is developed, two lines receive changes: `main`, from which 1.x releases are cut, and the long-lived branch `2.0`. Some defects exist on both, and work on `2.0` finds defects in 1.x code. With the switch off, `2.0` must behave as `main` does, apart from changes that have migration instructions, so a fix cannot live on `2.0` alone. Pull requests are opened against `2.0`, so other people's branches are based on its commits.

## Decision

- A fix that is valid on 1.x goes to `main` as its own pull request, and is cherry-picked into `2.0` when work on `2.0` needs it before it lands on `main`.
- While `2.0` lives on the fork `SummitSG-LLC/hamilton`, it takes `main` by rebase: its own commits are replayed on top of the current `main`. The first rebase, on 2026-11-17, put the planning commit on top of `main` at `e6bebcd1`.
- Rebasing `2.0` rewrites it and needs a force-push of `2.0`, which is the owner's act or waits for the owner's go. The push uses `--force-with-lease` against the commit the rebase started from.
- After each rebase of `2.0` on the fork, each open work branch is rebased onto the new `2.0` with `git rebase --onto <new 2.0> <old 2.0>` and force-pushed with a lease, by whoever holds that branch.
- Once `2.0` moves to `apache/hamilton`, it takes `main` by merge, never by rebase: force-pushes to a shared upstream branch are not an option. The merge is done on a work branch off `2.0` and reaches `2.0` through a pull request.
- A back-port from `2.0` to `main` is a cherry-pick, or a re-implementation, on a branch off `main`. `2.0` is not merged into `main` until 2.0 itself lands.

## Consequences

- 1.x users get a fix in the next 1.x release, without waiting for 2.0.
- A cherry-picked fix is on `2.0` at once, without the unrelated changes of `main`. On the fork, once its upstream twin is on `main`, the next rebase drops the cherry-pick when the change is identical; when it was adapted, the person rebasing drops it by hand. Each fix then appears once, under its upstream commit.
- While on the fork, the history of `2.0` is linear: `main`, then the 2.0-only commits, with no merge commits.
- Every rebase changes the commit ids of `2.0`. Open work branches and pull requests into `2.0` must be rebased after it, and a commit id of `2.0` quoted in a Ticket, a document or a pull request goes stale. Quote upstream commits, pull request numbers or tags instead.
- Each rebase replays every 2.0-only commit over the new `main`, so a conflict with a 2.0-only change, the version number among them, is resolved commit by commit, and the full checks run on the result.
- After the move upstream, the history of `2.0` gains merge commits, and a cherry-picked fix whose upstream twin later lands on `main` appears twice; the merge meets the same change a second time and merges cleanly unless `2.0` has changed those lines since. Commits on `2.0` are then never rewritten, so branches based on them stay valid.
- The move upstream is the point where the rule changes. The last rebase onto `main` before the move leaves `2.0` linear at that point.
- A fix is written against 1.x code first. Where the code has diverged on `2.0`, the cherry-pick needs adapting, or the fix is written twice.

## Alternatives considered

- **Merge `main` into `2.0` from the start.** This record's first version. Replaced for the fork period by the owner's ruling of 2026-11-17: on the fork, a force-push is possible, and a rebase keeps the history linear and each fix once. It remains the rule after the move upstream.
- **Rebase throughout, upstream included.** Rejected: force-pushes to a shared branch on `apache/hamilton` are not an option.
- **Fix on `2.0` first and back-port later.** Rejected as the default: 1.x users would wait for the back-port, and a forgotten back-port leaves `2.0` with the switch off differing from `main` in a way that no migration instruction covers.
- **Fix on `main` and wait for `2.0` to take `main` next.** Rejected: work on `2.0` that needs the fix would have to wait for, or force, a rebase or merge that also brings every other change on `main`.
