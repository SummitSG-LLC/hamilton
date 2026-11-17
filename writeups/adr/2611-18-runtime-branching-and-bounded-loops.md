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

# 2611-18. Runtime branching and bounded loops in Hamilton 2.0

**Status:** Proposed (2026-11, awaiting the owner's decision; the evidence is the survey [`writeups/surveys/runtime-branching-and-bounded-loops.md`](../surveys/runtime-branching-and-bounded-loops.md); the outline is apache/hamilton discussion #1645, "Hamilton 2.0: Architecture and Roadmap Reassessment")

This record holds the decisions the survey asks of the owner. Until the owner states a decision on each question below, every "Decision" entry is the survey's recommendation, not a decision. When the owner decides, the record is rewritten from the owner's statement, and its status becomes Accepted.

## Context

A Hamilton graph is a static directed acyclic graph, and execution is driven by demand: only the nodes the requested outputs need run.

The existing ways to choose do not decide at run time:

- `@config.when`, `step(...).when(...)` and `@resolve` choose when the graph is built.
- `final_vars` chooses when the Driver is called.
- `Parallelizable` and `Collect` map a block over items; they do not choose a path.

The README sends users who need "loops or conditional logic to create an LLM agent or a simulation" to the sister library Apache Burr. A maintainer asked on the outline whether conditional path execution and a loop syntax are possible. The outline answered that "Neither feature is an automatic 2.0 commitment" and placed runtime branching, bounded loops and nested mapping among its "Separate proofs". This effort's plan builds neither feature.

The survey compared Burr 0.43.0, LangGraph 1.2.22, Airflow 3.4.0, Dagster 1.13.30, Flyte (flytekit 1.16.32) and TensorFlow 2.21.0. It found five things that bear on the decision:

- **Branching needs no cycles.** Every acyclic system compared supports it.
- **Joins carry documented traps where a skip flows downstream** and each join states a rule (Airflow, Dagster, LangGraph). Where the branch is one structured operation that is itself the join (Flyte, TensorFlow), they do not.
- **A structured bounded loop now exists in an acyclic system.** Airflow 3.4.0 added a loop over a subgraph that keeps the graph acyclic, requires `max_iterations` and carries one value.
- **Burr allows cycles but has no built-in bound and no step caching.**
- **Burr's `Hamilton` action breaks on Hamilton 2.0 as now planned.** It calls `Driver.raw_execute`, which Hamilton schedules to fail at 2.0.0.

There is one user request for runtime branching (apache/hamilton issue #1290) and none for loops.

The outcome vocabulary comes from Ticket 06's survey and its record 2611-15 (Proposed; decision 11 is the agreement on skipped). The wording was agreed for this record:

- **skipped:** not executed because a runtime branch decision did not select the task's path. It is not failure.
- **blocked:** not executed because a prerequisite failed or was blocked.
- **cancelled:** stopped by the run before it finished.

## Decision

These are the survey's recommendations, pending the owner's decision on each.

1. **Runtime branching is deferred.** It is not in the first 2.0 release, and it is reopened as a separate proof after the plan, mapping and cache work of Tickets 10, 11 and 14.
2. **If branching is built,** a branch is a set of alternative implementations of one node, chosen at run time from a value computed in the run. That node is the join. Skips that flow downstream with per-join rules are not adopted.
3. **A branch controls nodes by demand.** A node is skipped when nothing selected or requested needs it, so a requested output always runs.
4. **The semantics of a branch, if built:**
   - A skipped node is not a failure and does not flow downstream.
   - All alternatives declare the same output type, checked at build time.
   - Optional parameters do not absorb a skip.
   - A missing value is never returned as `None`.
   - Nodes that depend on a decision do not start before it resolves.
   - Required inputs are validated before the run.
   - The skip records the decision and its value as its cause.
   - The cache key of the node follows the alternative that ran.
5. **Ticket 07's contracts reserve two things now:** the `skipped` outcome with a cause, and a way to settle a task without running it. Nothing in the contracts is named for branches or loops.
6. **Bounded loops are deferred** to the outline's separate proof. If built: one outer node with a body subgraph, typed carried names, a stop condition, a required `max_iterations`, and cancellation at iteration boundaries.
7. **Arbitrary cycles are declined.** They stay with Apache Burr.
8. **Task identity in Ticket 07 is a typed instance path** whose elements name their kind. A map item is the only kind for now.
9. **Burr's `Hamilton` action keeps working on Hamilton 2.0.** Either Hamilton keeps a supported entry point for it, or a replacement call is agreed with the Burr project before 2.0 is released. The migration entry for `Driver.raw_execute` names Burr. The README's Burr note stays as written for 2.0.

## Consequences

- No branching or loop code is written in this plan. Users keep today's workarounds: a two-phase run, or a Python loop inside one function.
- Ticket 07 carries a little more than it otherwise would: a cause on `skipped`, settling a task without running it, and a typed instance path. Nested mapping needs the instance path anyway.
- A later branching proof starts from agreed semantics instead of inventing them.
- Contacting the Burr project is an outward act that waits for the owner's go.

## Alternatives considered

- **Adopt runtime branching in the first 2.0 release.** It fits Hamilton well. It was not recommended because demand is thin and the plan, mapping and cache contracts it depends on are not built yet.
- **Decline runtime branching and send users to Burr.** Not recommended. Data-pipeline branching is outside the README's scope for Burr ("an LLM agent or a simulation"), and Burr's model is a state machine.
- **Airflow-style skip propagation with join rules.** Not recommended, because of the join traps that Airflow, LangGraph and Dagster document.
- **Branch membership by declaration**, with an error for a request on an unselected path. It is the alternative to item 3. It guards nodes that must not run on the wrong path, at the cost of a declaration on each member node.
- **Decline bounded loops for 2.0.** Not recommended over deferral. It rests only on missing demand, while the outline already assigns loops to a separate proof and deferral reserves only the typed instance path.
- **Allow cycles.** Declined. It would change what a parameter name means, every renderer and the cache.
