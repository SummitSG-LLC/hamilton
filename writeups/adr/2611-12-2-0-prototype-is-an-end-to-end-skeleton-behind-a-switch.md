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

# 2611-12. The 2.0 prototype is an end-to-end skeleton behind an opt-in switch; the 1.x paths stay as the reference

**Status:** Accepted (2026-11, a starting decision of the Hamilton 2.0 effort; the outline is apache/hamilton discussion #1645, "Hamilton 2.0: Architecture and Roadmap Reassessment")

## Context

The outline describes a new compiler and runtime for Hamilton 2.0, and withdraws the earlier effort estimates "until a combined runtime proof exists". A plan of that size can be argued about for a long time without anyone running it. The owner of the prototype effort wants a branch that people can install, run and give feedback on.

Hamilton 1.x has four paths that the new work would replace or sit beside: graph building, the default execution path, the task-based execution path and `AsyncDriver`.

## Decision

The first 2.0 plan builds a thin skeleton that works end to end on the branch `2.0`: the ordinary `Builder`/`Driver` API can build a graph through the new compiler and run it on the new runtime.

- One switch selects the new compiler and the new runtime together: a `Builder` option for one Driver, and an environment variable for a whole test run.
- With the switch off, `Driver` and `Builder` build and execute exactly as on 1.x. The only allowed differences are changes that have migration instructions and fixes that are also proposed for `main`.
- With the switch on, a Driver either builds through the compiler and runs on the new runtime, or fails with an error that names what is unsupported. It never falls back to a 1.x path.
- `AsyncDriver` is a 1.x path and ignores the switch.
- The 1.x paths stay in the branch as the reference against which the new path's behavior and speed are compared.

## Consequences

- The branch carries two implementations for the length of the prototype, and a change to shared code has to keep both working.
- Behavior and speed can be compared on the same graph, through the same API, in the same process, by turning the switch on and off.
- Because nothing falls back, a feature the new runtime lacks shows up as an error that names it, and the list of those errors is the list of work that remains.
- A user who does not turn the switch on sees only the breaking changes that the migration document lists.
- Making the new path the default is a later decision with its own migration instructions; the migration document keeps a section for that day.

## Alternatives considered

- **Foundations only**: land the groundwork (typing, one annotation boundary, the dependency split, contracts on paper) and start the runtime afterwards. Rejected: nothing would run end to end, so the contracts would be accepted without a proof, and feedback would again be on a plan.
- **A standalone runtime proof**: build the new runtime beside Hamilton, driven by its own entry point. Rejected: it would show that the scheduling design works, but not that ordinary `Builder`/`Driver` code, decorators and adapters work on it, and it would give no old-against-new comparison through one API.
