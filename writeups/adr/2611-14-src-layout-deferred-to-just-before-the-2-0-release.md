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

# 2611-14. The move to a `src/` layout waits until just before the 2.0 release

**Status:** Accepted (2026-11, a starting decision of the Hamilton 2.0 effort; the outline is apache/hamilton discussion #1645, "Hamilton 2.0: Architecture and Roadmap Reassessment")

## Context

The outline sketches a possible layout with the core under `src/hamilton` and provider packages that have their own `pyproject.toml` and `src` trees, and asks that installed wheels be tested outside the source checkout. Today the package is the top-level directory `hamilton/`, so Python run from the repository root imports the checkout and not an installed distribution.

Moving the package changes the path of every core file. While 2.0 is developed, `main` and `2.0` both receive changes, `2.0` takes `main` by merge, and fixes are cherry-picked between them (ADR 2611-13).

## Decision

The core stays at `hamilton/` for the whole of 2.0's development. The move to a `src/` layout is made just before the 2.0 release, as one change of its own, when `2.0` no longer takes changes from a line that has the old layout.

## Consequences

- Merges of `main` into `2.0` and cherry-picks in both directions keep working on the same paths.
- Until the move, the protection a `src/` layout gives against importing the checkout by accident comes from CI: a job builds the core wheel, installs it in a fresh environment in a directory outside the repository, and builds and executes a graph there.
- The move, when made, touches packaging, CI, the documentation build and the release scripts in one change, and pull requests open at that moment have to be rebased across it.
- New packages added during 2.0's development go under `hamilton/` and move with the rest.

## Alternatives considered

- **Move to `src/` at the branch point of `2.0`.** Rejected: every later merge of `main` and every cherry-pick would cross the rename, for as long as both lines receive changes.
- **Move both lines now**, `main` included. Rejected: it puts a change to every path into the 1.x line, where every open pull request would have to be rebased across it, for a benefit that only 2.0's packaging work needs.
