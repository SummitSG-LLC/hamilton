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

# 2611-15. Task outcome states and failure policy of the new runtime

**Status:** Proposed (awaiting the owner's decision). The survey behind this record is [`writeups/surveys/failure-policy.md`](../surveys/failure-policy.md). When the owner decides, each "Recommended" below is replaced by the owner's decision and the status becomes Accepted.

## Context

The new runtime of Hamilton 2.0 exchanges outcome data between its coordinator, execution backends and observers. The runtime contracts (Ticket 07 of the 2.0 effort) take their outcome states from this record, and every later backend, observer and conformance check builds on them.

The 2.0 outline names the contracts the failure policies need:

- best-effort: "Successful, failed, blocked, skipped, and cancelled outcomes; partial-result reporting";
- retry: "Attempt identity, limits, cleanup, and side-effect policy";
- fallback: "Explicit substitution rules".

The outline also says to design them together with cancellation and mapping.

Hamilton 1.x has two terminal task states, successful and failed. Its lifecycle hooks report a `success` flag and an error. Its one graceful mechanism, `GracefulErrorAdapter`, substitutes an in-band sentinel for a failed result. It takes over node execution, which the plan refuses when the new runtime is switched on. Its `Parallelizable` branch also depends on a callable rewrite that the new runtime will not do.

The survey compared Dask 2026.8.0, Prefect 3.9.3, Dagster 1.13.30, Airflow 3.4.0, and `asyncio` (3.11.0 and 3.14.10), Trio 0.35.0 and AnyIO 4.16.0. It found:

- **Dependents of a failure.** The systems disagree on how to record a dependent that was not run because its prerequisite failed. Airflow stores a terminal state, Prefect a non-terminal one, Dask folds it into failure with a cause pointer, and Dagster records nothing.
- **Fallback.** None of the systems substitutes a value for a failed result.
- **Siblings.** Dask and the orchestrators (Airflow, Prefect, Dagster) continue independent work after a failure; the structured-concurrency libraries cancel it.
- **Threads.** No system can interrupt a running thread.

The prototype on the `2.0` branch implements no best-effort mode, retry policy or fallback policy, whatever this record decides (owner's ruling). This record decides what the 2.0 release's contracts must hold, and which policies belong in the first 2.0 release, meaning the release in which the new runtime becomes the default.

## Decision

Proposed; each item awaits the owner.

1. **Outcome vocabulary and the recording rule.** Recommended: a task ends in `succeeded`, `failed` or `cancelled`, and an outcome records what happened to the task, not what the run asked for. A synchronous task that is running when the run stops is waited for and recorded as `succeeded` or `failed`. A timeout, if one is added later, is `failed`.
2. **States the 2.0 outcome type carries.** Recommended: every state the 2.x line is expected to produce. That means `blocked` (a prerequisite failed or was blocked) if decision 7 adopts best-effort for 2.x, and `skipped` (a runtime branch was not selected) if Ticket 26's decision adopts runtime branching. A state that no policy yet produces is documented as such.
3. **Unfinished tasks under fail-fast, the default policy.** Recommended: every task that has not finished ends `cancelled`, siblings and never-started dependents alike. Every task the run creates ends with exactly one outcome, reported to observers exactly once.
4. **Cause on `cancelled`.** Recommended: a structured cause. It is either the identity of the task whose failure stopped the run, or "caller" (for example `KeyboardInterrupt`, or cancellation of the awaiting task).
5. **What the caller receives under fail-fast.** Recommended: the failing node's own exception, unchanged; the first failure the coordinator observed. Other failures reach observers only.
6. **`cancelled` through the 1.x hook bridge.** Recommended:
   - `post_node_execute` is called only for tasks that had `pre_node_execute`.
   - A started-then-cancelled task gets `success=False` and its cancellation exception.
   - Never-started tasks reach no 1.x hook.
   - `post_graph_execute` gets `success=False` and the raised error.
7. **Best-effort in the first 2.0 release.** Recommended: yes, as an opt-in run policy that produces `blocked`, if that release leaves users no 1.x execution path to select. Otherwise, not in the first release, and `GracefulErrorAdapter` stays on the 1.x paths. A best-effort run never reports success when a requested output did not succeed. It raises one documented exception that carries the outcomes and the values that succeeded.
8. **Typed opt-in to consume a prerequisite's failure.** Recommended: in the same release as best-effort. It is a per-parameter declaration through which the node receives an outcome object, never a sentinel.
9. **First-party retry in the first 2.0 release.** Recommended: no.
   - Attempt identity stays in the contracts.
   - Third-party code may retry through the node-call wrapper contract.
   - The docs point to in-function retry and its side-effect caveat.
10. **Fallback (value substitution) in the first 2.0 release.** Recommended: no. `GracefulErrorAdapter` and `@accept_error_sentinels` get migration instructions that point to decisions 7 and 8, for the day the new runtime becomes the default.
11. **`skipped`, agreed with Ticket 26.** Recommended: `skipped` means only "not executed because a runtime branch decision did not select its path". It is not a failure, and it never produces `blocked`. Ticket 26 decides how it propagates and how joins treat it.

## Consequences

- **The contracts (Ticket 07) carry:**
  - an outcome type with `succeeded`, `failed` and `cancelled`, plus whatever decision 2 reserves;
  - a cause on `cancelled`, which must stay serializable for an out-of-process backend;
  - the invariant of one outcome per created task;
  - task identity that tells attempts apart.
- **The slice and Tickets 11, 12 and 16** produce only `succeeded`, `failed` and `cancelled`, and the conformance kit (Ticket 15) can check the invariant against any backend.
- **Observers and the Hamilton UI.** Observers can tell a stopped task from a failed one without walking the graph. The Hamilton UI's tracking schema knows only `SUCCESS`, `FAILURE`, `RUNNING` and `UNINITIALIZED`, so showing the new outcomes needs a UI migration. That is outside this effort.
- **Migration.** `GracefulErrorAdapter`, `@accept_error_sentinels` and the sentinel-based "gather what succeeded" pattern have no equivalent on the new runtime until decisions 7 and 8 are built. The migration document's section for the day the new runtime becomes the default must say so.
- **Retry users.** Users who retry inside node functions see no change. Their attempts stay invisible to observers and to the cache.

## Alternatives considered

- **Minimal forever.** Three states only, with best-effort dependents reported as `cancelled` and the cause "prerequisite failed"; this is Trio's approach of a reason field instead of more states. It is the strongest alternative, and its contract never grows. It was ranked second, because `cancelled` would gain a meaning in which nothing was stopped, and every observer would have to read the cause to count failures. Airflow's overloaded `skipped` and the dbt conflation recorded in Dagster's changelog show the cost of one label for several causes.
- **Derived blocked.** No `blocked` state; observers infer it from `failed` and the graph, as Dagster does with "abandoned". This was the Ticket's counter-hypothesis. It was rejected because observers do not hold the plan, and mapped instances of a failed expander cannot be inferred.
- **Orchestrator-sized.** Airflow-like states such as `upstream_failed`, `up_for_retry`, `removed` and a crashed state. Rejected: several have no meaning for a runtime that runs in one process and keeps no state after the run.
- **Continue-by-default**, as Dask and every orchestrator do. Rejected for the default policy. Those systems keep continued work reachable, through a store or through per-task handles. A Hamilton run returns one result to one caller and offers neither, so work continued after a failure is lost unless a best-effort policy returns it.
