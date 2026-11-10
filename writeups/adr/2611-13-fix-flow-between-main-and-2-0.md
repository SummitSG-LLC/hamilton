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

**Status:** Accepted (2026-11, a starting decision of the Hamilton 2.0 effort; the outline is apache/hamilton discussion #1645, "Hamilton 2.0: Architecture and Roadmap Reassessment")

## Context

While 2.0 is developed, two lines receive changes: `main`, from which 1.x releases are cut, and the long-lived branch `2.0`. Some defects exist on both, and work on `2.0` finds defects in 1.x code. With the switch off, `2.0` must behave as `main` does, apart from changes that have migration instructions, so a fix cannot live on `2.0` alone. Pull requests are opened against `2.0`, so other people's branches are based on its commits.

## Decision

- A fix that is valid on 1.x goes to `main` as its own pull request, and is cherry-picked into `2.0`.
- `2.0` takes `main` by merge, never by rebase.
- A back-port from `2.0` to `main` is a cherry-pick, or a re-implementation, on a branch off `main`. `2.0` is not merged into `main` until 2.0 itself lands.

## Consequences

- 1.x users get a fix in the next 1.x release, without waiting for 2.0.
- A cherry-picked fix is on `2.0` at once, without the unrelated changes a merge of `main` would bring. The later merge of `main` meets the same change a second time; it merges cleanly unless `2.0` has changed those lines since.
- The history of `2.0` holds merge commits and some changes twice, and commits on `2.0` are never rewritten, so branches and pull requests based on it stay valid.
- Each merge of `main` can conflict with 2.0-only changes, the version number among them, and has to be followed by the full checks.
- A fix is written against 1.x code first. Where the code has diverged on `2.0`, the cherry-pick needs adapting, or the fix is written twice.

## Alternatives considered

- **Rebase `2.0` onto `main`.** Rejected: it rewrites the commits that open pull requests and other contributors' branches are based on, and it replays every 2.0 commit over each `main` change.
- **Fix on `2.0` first and back-port later.** Rejected as the default: 1.x users would wait for the back-port, and a forgotten back-port leaves `2.0` with the switch off differing from `main` in a way that no migration instruction covers.
- **Fix on `main` and wait for the next merge of `main` into `2.0`.** Rejected: work on `2.0` that needs the fix would have to wait for, or force, a merge that also brings every other change on `main`.
