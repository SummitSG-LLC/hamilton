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

# Survey: task outcomes, best-effort execution, retry and fallback for Hamilton 2.0

**Status:** proposal, awaiting the owner's decisions. The decisions will be recorded in [ADR 2611-15](../adr/2611-15-task-outcome-states-and-failure-policy.md). This survey builds nothing. Where it says a policy "belongs in the first 2.0 release", it means the release in which the new runtime becomes Hamilton's default. It does not mean that the policy is built on the `2.0` branch now. The prototype on that branch implements no best-effort mode, no retry policy and no fallback policy, whatever is decided here. That is the owner's ruling for the prototype, recorded in the effort's Tickets: "best-effort, retry and fallback stay on the old path until feedback settles their semantics". The prototype itself is described in [ADR 2611-12](../adr/2611-12-2-0-prototype-is-an-end-to-end-skeleton-behind-a-switch.md).

## Summary

The question: which outcome states can a task end in on Hamilton's new runtime, how does one state lead to another, and which of best-effort execution, retry and fallback belong in the first 2.0 release? The answer feeds the runtime contracts of the effort's next step, which define the outcome data that execution backends, observers and the coordinator exchange.

The survey compared Dask (`distributed` and `dask` 2026.8.0), Prefect 3.9.3, Dagster 1.13.30, Apache Airflow 3.4.0, and the structured-concurrency libraries: CPython `asyncio` and `concurrent.futures` at 3.11.0 and 3.14.10, Trio 0.35.0 and AnyIO 4.16.0. It also read Hamilton's own 1.x code and ran three probes against it. The findings that drive the proposal:

- **No two systems handle "not run because something upstream failed" the same way.**
  - Airflow stores a terminal `upstream_failed` state.
  - Prefect stores a non-terminal `Pending` state named `NotReady`, which, by a reading of its source, never ends.
  - Dask marks the dependent with the same `erred` state as the root failure, plus a pointer to that root.
  - Dagster records nothing: an "abandoned" step gets only a log line.
- **None of the systems compared substitutes a value for a failed task's result.** Hamilton 1.x does: `GracefulErrorAdapter` puts a sentinel in place of the result. The probe below shows the hazard. With its default sentinel `None`, a node whose input is legitimately `None` is silently not run.
- **The orchestrators and Dask disagree with the concurrency libraries on siblings.** When one task fails, Dask, Prefect, Dagster and Airflow let independent work continue by default; Airflow offers fail-fast only as an option. `asyncio.TaskGroup`, Trio nurseries and AnyIO task groups cancel the siblings. Hamilton's coordinator runs one call in one process and keeps no state after it, which places it with the concurrency libraries.
- **No system can interrupt a running synchronous function in a thread.** In each, either the work runs to completion and its result is discarded, or a signal or process kill ends it.
- **Dask and the three orchestrators retry; none of the concurrency libraries does.**
  - They identify attempts as follows: Dask by a hidden `run_id`, Prefect by `run_count`, Dagster by `retry_number`, Airflow by `try_number` with one stored row per try.
  - On side effects: Dask assumes pure functions, Airflow asks for idempotent tasks, Prefect offers transactions with rollback hooks, and Dagster says nothing.

The proposal, in one paragraph. A task ends in exactly one of these outcomes: `succeeded`, `failed` or `cancelled`. Two more are defined now and produced only by later policies: `blocked`, for best-effort execution, and `skipped`, for runtime branching (Ticket 26). An outcome records what happened to the task, not what the run asked for. Under the default fail-fast policy, the first failure stops the run. Every task that has not finished then ends `cancelled`, with a cause that names the failure, and the caller receives the failing node's own exception. Best-effort execution, together with a typed way for a node to accept a prerequisite's failure, belongs in the first 2.0 release if that release leaves users no 1.x execution path to select, because `GracefulErrorAdapter` cannot run on the new runtime. While a 1.x path can still be selected, it can wait. A first-party retry policy and value fallback do not; the contracts keep room for both. Eleven decisions for the owner are listed in [Decisions for the owner](#decisions-for-the-owner), each with a recommendation and its effect on the runtime contracts.

## Scope, versions and method

**Systems and versions.** Each claim about another system cites that system's own repository at a release tag, with a line range. The tags are:

- `dask/distributed` and `dask/dask` at 2026.8.0;
- `PrefectHQ/prefect` at 3.9.3, with 2.20.27 for Prefect 2 comparisons;
- `dagster-io/dagster` at 1.13.30;
- `apache/airflow` at 3.4.0, with 2.10.5 for Airflow 2 comparisons;
- `python/cpython` at v3.11.0 (Hamilton's floor) and v3.14.10;
- `python-trio/trio` at v0.35.0;
- `agronholm/anyio` at 4.16.0.

These were the newest releases on PyPI or the newest tags on 2026-11-17. Prefect, Dagster and Airflow keep their documentation in their repositories, so documentation is cited at the same tag as the code. No live documentation page is used as a source. Hamilton is cited at commit `ef88b1e9` of `apache/hamilton`, the effort's branch point. The `2.0` branch at `31b3a832` carries every cited Hamilton file unchanged; `git diff --stat ef88b1e9 31b3a832` over them is empty.

**How the sources were checked.**

- The evidence for each system was gathered from its source tree at the tag. Each facet was searched with at least two query formulations; the query logs are kept with the working notes, not in this report.
- A script then fetched every cited raw file at its tag and checked each quoted phrase in this report against its stated line range. The section [How the citations were verified](#how-the-citations-were-verified) gives the count and result.
- Where a claim rests on reading source with no documentation behind it, the text says so.

**Frames.** The question is looked at from three sides:

- the pipeline author, who writes nodes and calls `execute`;
- the maintainer, who owns the runtime contracts and every backend and observer built on them;
- the operator, who reads run outcomes in logs, the Hamilton UI or a tracker.

[Three frames](#three-frames) collects what each one needs.

**What is not covered.**

- Crash recovery and durable execution: the outline separates them from this question ("Best-effort execution and in-process retries do not require durable execution-state persistence. Crash recovery does.").
- The semantics of runtime branches, which are Ticket 26's.
- Timeouts, except to say how they map to outcomes.
- Systems not named by the owner, such as Ray, Luigi or Kedro.

## Terms

These terms are defined once and used the same way for every system. Each system's own words are mapped onto them in the comparison table.

- **Orchestrator:** Airflow, Prefect or Dagster: a system with a scheduler that keeps each task's state and result in a store. Dask is a task scheduler whose results live in worker memory behind the client's `Future` handles; `asyncio`, Trio and AnyIO are concurrency libraries.
- **Task:** one unit the coordinator schedules. That is a node of the compiled graph, or one mapped instance of a node inside a `Parallelizable`/`Collect` block.
- **Attempt:** one execution of a task's function. Without retry, a task has at most one attempt.
- **Run:** one call to `execute` (or the proposed `aexecute`).
- **Outcome:** the terminal state a task ends in, within one run.
- **Prerequisite:** a task whose value another task consumes.
- **Dependent:** a task that consumes another task's value. The dependents of a task include indirect ones.
- **Sibling:** a task that is neither a prerequisite nor a dependent of a given task.
- **Fail-fast:** the policy under which the first failure ends the run.
- **Best-effort:** the policy under which a run continues with every task that does not depend on a failure, and reports partial results.
- **Retry:** running a further attempt of a failed task within the same run.
- **Fallback:** an explicit rule that substitutes a value for a failed task's result, so that its dependents run.
- **Blocked:** not executed because a prerequisite did not succeed. This report uses "blocked" only for that meaning.
- **Skipped:** not executed because a runtime branch decision did not select the task's path. This report uses "skipped" only for that meaning and leaves its semantics to Ticket 26. Where a system uses "skipped" for something else, the comparison says so.
- **Cancelled:** the run stopped the task before it finished, whether the task had started or not.
- **Partial result:** the values of the tasks that succeeded in a run in which some task did not succeed.

## Hamilton 1.x today

**Outcome states.** No 1.x component has a cancelled, blocked or skipped state.

- The task-based executor's `TaskState` has six members, and `is_terminal` accepts only `SUCCESSFUL` and `FAILED` ([h-taskstate]).
- Observers learn one bit. `post_node_execute` and `post_graph_execute` receive `success: bool` and `error: Exception | None` ([h-post-node], [h-post-graph]).
- The Hamilton UI's tracking SDK records `SUCCESS`, `FAILURE`, `RUNNING` and `UNINITIALIZED` ([h-sdk-status]). The UI server's first database migration fixes those four choices ([h-ui-migration]).

**Dependents and siblings of a failure.** The three execution paths behave differently, and none of the differences is documented as a promise.

- **Default path:** nodes are called one at a time, depth first, through one recursive function. The first exception ends the run, and no further node runs.
- **Task-based path:** the coordinator raises the first error it collects. Its `finally` block then calls `finalize()` on the executors ([h-raise]), and `PoolExecutor.finalize()`, which `MultiThreadingExecutor` and `MultiProcessingExecutor` inherit, calls `self.pool.shutdown()` with default arguments ([h-finalize]). In `concurrent.futures`, those defaults wait for running work and do not cancel queued work ([cf-shutdown]). Probe 1 below measures the effect.
- **`AsyncDriver`:** awaits nodes with `asyncio.gather` without `return_exceptions` ([h-gather]). `gather` does not cancel other awaitables when one raises ([aio-gather]). The outline measured that "an independent sibling finished after the graph reported failure" in ten runs out of ten per build.

**Partial results.** No 1.x path returns values after a failure. The caller receives the node's exception.

**Retry.** There is no retry mechanism anywhere in `hamilton/`; a search for `retr(y|ies)`, `backoff` and `max_attempts` finds none. Users retry inside node functions. For example, the contrib dataflow `zilto/webscraper` decorates the node `html_page` with tenacity's `@retry(... stop=stop_after_attempt(3))` ([h-tenacity]). Observers, the tracker and the cache see one execution, whatever happened inside.

**Best-effort and fallback: `GracefulErrorAdapter`.** This is the only 1.x mechanism, and it combines both.

- It is a `NodeExecutionMethod`. It catches one chosen exception type and returns a sentinel value in place of the failed node's result ([h-graceful]).
- When a node's input equals the sentinel, compared by type and `==`, it returns the sentinel without calling the node ([h-graceful-sentinel]). That is how dependents of a failure become no-ops.
- `@accept_error_sentinels` lets a node opt in to receive the sentinel and run anyway ([h-accept]).
- It takes over node execution: it is a `NodeExecutionMethod`, which implements the single-implementer `do_node_execute` method. The effort's plan refuses such adapters with a clear error when the new runtime is switched on (Ticket 07), because the new runtime's node-call wrapper contract takes that role. For `Parallelizable` nodes it also reaches into the callable that the task-based executor wrapped during the run ([h-graceful-callable], [h-rewrite]), a rewrite the new runtime will not do. The adapter therefore cannot run on the new runtime as written. It works on the 1.x default path, as Probe 2 shows.
- Its docstring says it is "only compatible with the dict-based result builder".
- An example in the repository, `examples/parallelism/graceful_running`, uses it to gather the results of the mapped items that succeeded.

**Probe 1: siblings on the 1.x task-based path with threads.**

- **Setup:** one mapped item raises after 50 ms; three siblings sleep 500 ms. The build was `enable_dynamic_execution(allow_experimental_mode=True)` with `MultiThreadingExecutor(max_tasks=4)`, run ten times with CPython 3.15.0 on the effort's development machine.
- **Result:** in every run the error reached the caller after all three siblings had finished. That was 0.501 s to 0.507 s after the start, though the failure happened at 0.05 s.

Excerpt of the output:

```text
run 0: siblings finished before caller saw error: 3, after: 0; error reached caller at 0.501s
...
run 9: siblings finished before caller saw error: 3, after: 0; error reached caller at 0.504s
```

On that path a failure therefore does not cancel running siblings. With four items and four workers nothing was queued, so the probe did not measure queued work. From the `shutdown()` defaults ([cf-shutdown]), work already submitted to the pool would also run; this part is inferred, not measured. A third probe, on the default path, confirmed that a failing node ends the run and no further node runs.

**Probe 2: `GracefulErrorAdapter` with its default sentinel.** A node returns `None` legitimately, with no error, and a dependent consumes it:

```text
no adapter -> {'uses_it': 'ran with None'}
GracefulErrorAdapter(sentinel None) -> {'uses_it': None}
```

With the adapter attached, the dependent silently did not run, and its result was reported as `None`. Nothing failed. This is the outline's warning made concrete: an in-band value cannot tell "the input is `None`" from "the prerequisite failed". The probe scripts are short and are reproduced in [Appendix: probes](#appendix-probes).

## The systems

Each system is described against the same six questions:

1. outcome states;
2. dependents of a failed task;
3. partial results;
4. retries and side effects;
5. fallback;
6. cancellation.

Each section ends with the system's notion of "skipped" and the change at its last major version.

### Dask (distributed and dask 2026.8.0)

Dask has four separate state vocabularies: scheduler task states, worker task states, `Future.status`, and the local schedulers' bookkeeping. They must not be mixed up.

1. **Outcome states.**
   - The scheduler's states are `released`, `waiting`, `no-worker`, `queued`, `processing`, `memory`, `erred` and `forgotten` ([dask-states]). Success is `memory` and failure is `erred`.
   - Neither is final: `erred -> released` exists for retries, and every task is eventually released or forgotten.
   - `Future.status` is one of `pending`, `finished`, `error`, `cancelled` or `lost` ([dask-future-status]).
   - The docs call the scheduler states "an internal detail" that "may change between versions" ([dask-internal]).
   - No run object carries a status.
2. **Dependents.**
   - A failure spreads to dependents as the same state. `_propagate_erred` marks each waiter `erred` and sets its `exception_blame` to the root failure ([dask-propagate]). The docs: "All futures that depend on an erred future also err with the same exception" ([dask-futures-err]).
   - "Upstream failed" is therefore stored as `erred` and told apart only by the blame pointer ([dask-blame]). The client receives the root's exception for the dependent too.
   - Nothing lets a dependent run anyway: there is no trigger rule, no `allow_failure` and no optional input.
   - In the local schedulers (`dask.local`), the first failure re-raises and ends the computation ([dask-local-raise]).
3. **Partial results.**
   - Each `Future` holds its own outcome.
   - `Client.gather(errors="skip")` drops failed results from the returned collection ([dask-gather-skip]).
   - `wait()` returns done and not-done sets without raising for erred futures.
   - The local schedulers return only the first exception, with no values.
4. **Retries.**
   - `retries=` is a countdown with no delay, backoff, jitter or exception filter ([dask-retries]). Retry is not a state: the task returns to `waiting`.
   - Each dispatch gets a fresh `run_id`, and late reports from an older dispatch are rejected ([dask-run-id]). No attempt number is visible to users.
   - Dask "assumes that all functions are pure" ([dask-pure]) and offers no idempotency or cleanup mechanism.
   - Worker deaths are counted separately (`allowed-failures`).
5. **Fallback.** None. The only nearby feature is `gather(errors="skip")`, which shapes the returned collection and does not feed dependents.
6. **Cancellation.**
   - The scheduler has no cancelled state. A cancel releases or forgets the task, along with dependents that nobody else wants.
   - A task that is already executing on a worker cannot be stopped: the task moves to a `cancelled` state, "which means that the asyncio task will proceed to completion (outcome is irrelevant)", and only then is the Dask task released ([dask-cancel-running]).
   - The cancel reason is recorded on the client as `FutureCancelledError(reason, msg)` ([dask-cancel-reason]).
   - The distributed scheduler has no fail-fast: independent siblings keep running.
- **"Skipped":** none in any sense. **Recent changes:** `queued` became the default scheduling mode in 2022.11.0, attempts were signed with `run_id` in 2023.7.0, and forwarding of the cancellation reason was fixed in 2025.3.0.

### Prefect 3.9.3

Prefect separates a state's *type*, of which there are nine and which drive orchestration, from its *name*, which is a free string for display.

1. **Outcome states.**
   - The types are `SCHEDULED`, `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`, `CRASHED`, `PAUSED` and `CANCELLING` ([prefect-statetype]). The terminal ones are `COMPLETED`, `CANCELLED`, `FAILED` and `CRASHED` ([prefect-terminal]).
   - Named variants include `Cached` and `RolledBack` (type COMPLETED), `TimedOut` (type FAILED), and `AwaitingRetry` and `Retrying` ([prefect-states-doc]).
   - `Crashed` means "an infrastructure issue" as against `Failed`'s "code issue". It is not retried ([prefect-crash]).
2. **Dependents.**
   - A dependent of a failed future is created, and it raises `UpstreamTaskError`. The engine then stores `Pending(name="NotReady")` ([prefect-notready]). A test asserts exactly that ([prefect-notready-test]).
   - `NotReady` is of type PENDING, which is not terminal, and no code path moves it on. The dependent never reaches a terminal state. This is a reading of the source; the narrative docs do not mention `NotReady`.
   - A task called directly, not submitted, raises in the flow function, so its dependents are never created.
   - The opt-in is `allow_failure`: "This annotation allows you to opt into receiving a failed input downstream. … the attached exception will be passed to your function" ([prefect-allow-failure]). It admits FAILED and NotReady upstreams, but not CRASHED or CANCELLED ones ([prefect-allow-failure-scope]).
3. **Partial results.**
   - In Prefect 3, a flow's final state comes only from its return value or a raised exception: "task failures within a flow do not automatically cause the flow run to fail unless they affect the flow's return value or raise an uncaught exception" ([prefect-v3-final]). In Prefect 2, failed tasks failed the flow ([prefect-v2-final]).
   - `return_state=True` hands the caller a `State` instead of raising.
   - The documented pattern for "run to completion even if some tasks fail" is `wait()` plus `.state` on each future ([prefect-wait]).
4. **Retries.**
   - Tasks take `retries`, `retry_delay_seconds` (a number, a list or a callable), `retry_jitter_factor` and `retry_condition_fn` ([prefect-retry-params]).
   - Attempts reuse the same task-run ID, and `run_count` counts them ([prefect-run-count]).
   - Retry is a pair of names over non-terminal types, `AwaitingRetry` and `Retrying`.
   - Side effects: caching is presented as the way to make retries idempotent ([prefect-caching]). Transactions run rollback hooks, and "Prefect does not automatically undo those operations" ([prefect-no-undo]).
5. **Fallback.** None built in. The docs point to `return_state=True` with branching, `.result(raise_on_failure=False)`, or `allow_failure`, where the dependent receives the exception object and decides what to do.
6. **Cancellation.**
   - A flow run is cancelled by state (`Cancelling`), then a signal, then a kill after a grace period ([prefect-cancel-flow]).
   - Task runs cannot be cancelled on their own.
   - In process, the thread-pool task runner checks a cancel event once, before the user function starts. Running sync work is not interrupted: "timeouts **cannot interrupt blocking operations**" ([prefect-sync-timeout]).
   - Siblings are not cancelled when one task fails. When the flow function exits on an exception, the task runner drops queued work and waits for running work ([prefect-runner-exit]).
   - The reason is free text in `State.message`.
- **"Skipped":** no built-in state; the docs show `Completed(name="Skipped")` as a custom name ([prefect-skipped]). **Prefect 2 to 3:** the flow's final state stopped deriving from task states. Client-side task orchestration, transactions and default caching arrived.

### Dagster 1.13.30

Dagster records a step's outcome as events in an event log. A run has its own status.

1. **Outcome states.**
   - Step events include `STEP_SUCCESS`, `STEP_FAILURE`, `STEP_SKIPPED` and `STEP_UP_FOR_RETRY`, the last commented `"failed" but want to retry` ([dagster-events]).
   - The status shown to users is derived from these events: `SKIPPED`, `SUCCESS`, `FAILURE` and `IN_PROGRESS` ([dagster-step-status]).
   - The in-memory plan state machine has the terminal sets success, failed, skipped and abandoned ([dagster-active-sets]).
   - Run statuses include `SUCCESS`, `FAILURE`, `CANCELING` and `CANCELED` ([dagster-run-status]).
2. **Dependents.**
   - A dependent of a failed step is *abandoned*. It gets an error log line ("Dependencies for step … Not executing.") and no step event ([dagster-abandon]).
   - "Not run because upstream failed" is thus not stored; the result API reports such a step as "untouched", meaning it has no events ([dagster-untouched]).
   - Since 1.5.11, a skip takes precedence over an abandon. The changelog says this was done for "the 'retry from failure' workflow when conditional branching is in use" ([dagster-skip-precedence]).
   - There are no trigger rules and no `allow_failure`.
3. **Partial results.**
   - Independent steps keep running after a failure; the plan loop runs until the plan is complete ([dagster-loop]).
   - The run fails if any step failed. A run whose only non-successes are skips succeeds ([dagster-run-fail]).
   - `execute_in_process` raises on the first error by default (`raise_on_error=True`). `execute_job` returns a result object with per-node predicates and output values.
4. **Retries.**
   - `RetryPolicy` takes `max_retries`, `delay`, `backoff` and `jitter` ([dagster-retry-policy]). Every exception retries unless it is raised as `Failure(allow_retries=False)`. A custom condition is expressed by raising `RetryRequested` by hand.
   - An attempt keeps its step key, and `context.retry_number` counts from 0 ([dagster-retry-number]).
   - The docs say nothing about side effects or idempotency on retry.
   - From the source only: under a retry policy, an interrupt is also turned into a retry request ([dagster-interrupt-retry]).
5. **Fallback.** None. `In(default_value=...)` applies only to inputs with no upstream connection ([dagster-default-value]).
6. **Cancellation.**
   - Run termination marks the run `CANCELING`, then sends SIGINT into the run worker. Inside op code the signal is raised as an exception ([dagster-interrupt]).
   - An interrupted step ends as `STEP_FAILURE` with `ErrorSource.INTERRUPT`. There is no step-level cancelled state ([dagster-interrupt-failure]).
   - Siblings are not cancelled when one step fails.
- **"Skipped":** `STEP_SKIPPED` means that an optional output the step consumes was not produced. Branching is modelled the same way ([dagster-branching]). It never means "upstream failed". **Recent changes:** run retries (1.2.0), skip precedence (1.5.11), and `require_upstream_step_success` (1.11.10 and 1.12.0).

### Apache Airflow 3.4.0

Airflow stores one `TaskInstance` row per task, map index and try. A `DagRun` has its own state.

1. **Outcome states.**
   - The TaskInstance states are `none`, `scheduled`, `queued`, `running`, `success`, `restarting`, `failed`, `skipped`, `upstream_failed`, `up_for_retry`, `up_for_reschedule`, `deferred`, `awaiting_input` and `removed` ([airflow-ti-states]).
   - The terminal ones are `success`, `failed`, `skipped`, `upstream_failed` and `removed` ([airflow-terminal]).
   - For the run's outcome, `skipped` counts with success and `upstream_failed` with failure ([airflow-state-groups]).
2. **Dependents.**
   - The scheduler's trigger-rule check writes `upstream_failed` as a stored terminal state. Under the default `all_success`, it does so when any direct upstream is `failed` or `upstream_failed`, so the state propagates ([airflow-upstream-failed]).
   - The flag that creates the state is described in its own docstring as "a hack to generate the upstream_failed state creation while checking to see whether the task instance is runnable" ([airflow-hack]).
   - Thirteen trigger rules let a dependent opt in to running after failures, for example `all_done`, `one_failed` and `none_failed` ([airflow-trigger-rules]).
   - A dependent that runs and consumes a failed upstream's return value receives `None` ([airflow-xcom-none]). That `None` cannot be told apart from a legitimate one.
3. **Partial results.**
   - The DagRun's state is computed from its leaf tasks ([airflow-leaves]). The docs warn that an `all_done` leaf can make a run succeed "even if something failed in the middle".
   - Values of the tasks that succeeded remain as XComs.
4. **Retries.**
   - Tasks take `retries`, `retry_delay`, `retry_exponential_backoff` and `max_retry_delay` ([airflow-retry-params]). Since 3.3, pluggable retry policies can retry, fail, reschedule or defer to the default.
   - In 3.4.0 every try is its own row, with a UUID and a `try_number`. The failed try is marked `failed`, and a new try is created in `up_for_retry` ([airflow-try-rows]).
   - On side effects: "You should treat tasks in Airflow equivalent to transactions in a database … the tasks should produce the same outcome on every re-run" ([airflow-idempotent]). XComs are cleared between tries.
5. **Fallback.** None built in. The documented patterns are trigger rules (a "watcher" task), setup and teardown tasks, and callbacks that observe without changing the value.
6. **Cancellation.**
   - There is no `cancelled` TaskInstance state. A running task is stopped by marking it `failed` or `success` from outside. The worker's heartbeat then gets a 409, and the supervisor sends SIGTERM, which calls `on_kill()`, then SIGKILL ([airflow-heartbeat-kill]).
   - An opt-in `fail_fast` makes the running siblings of a failed task `failed` and the other unfinished tasks `skipped` ([airflow-fail-fast]).
   - A `dagrun_timeout` marks every unfinished task, including running ones, `skipped` ([airflow-dagrun-timeout]).
   - No structured cancellation cause exists.
- **"Skipped":** many meanings. The documented list starts with branching, `LatestOnly` and manual skips ([airflow-skip-meanings]); the cancellation side effects are in [airflow-fail-fast] and [airflow-dagrun-timeout]. The meanings found include:
  - a branch not selected;
  - `LatestOnly` and short-circuit;
  - a task that raised `AirflowSkipException`;
  - a skip cascaded from an upstream skip;
  - a trigger rule that can no longer be met;
  - a zero-length mapping;
  - a task skipped by hand;
  - unfinished work when a run is cancelled or timed out, or under `fail_fast`.

  "Upstream failed" is the separate state `upstream_failed`. **Airflow 2 to 3:** the Task Execution API was introduced, with a UUID per attempt; the trigger rules `none_failed_or_skipped` and `dummy` were removed; `fail_stop` was renamed `fail_fast`. In 3.4.0, try numbers are allocated before the next try starts.

### Structured-concurrency libraries: asyncio (3.11.0 and 3.14.10), Trio 0.35.0, AnyIO 4.16.0

These are concurrency libraries, not orchestrators. They have no data dependencies, so "dependents" maps to the siblings in a task group and to the awaiting parent.

1. **Outcome states.**
   - An `asyncio` Task is done when it "either returned a value, raised an exception, or the Task was cancelled" ([aio-done]). The internal states are `PENDING`, `CANCELLED` and `FINISHED`, and a failure is `FINISHED` with an exception set.
   - `Task.cancelled()` is true only if the coroutine let the `CancelledError` propagate. A request alone does not make a task cancelled ([aio-cancelled-def]).
   - `concurrent.futures` adds `RUNNING` ([cf-states]).
   - AnyIO 4.14 added `TaskHandle.Status` with `PENDING`, `FINISHED`, `CANCELLING`, `CANCELLED` and `FAILED` ([anyio-status]).
   - A Trio child task has no handle at all.
2. **Siblings on failure.**
   - `asyncio.TaskGroup`: "The first time any of the tasks belonging to the group fails with an exception other than `asyncio.CancelledError`, the remaining tasks in the group are cancelled" ([aio-taskgroup]). The same text is in 3.11.0.
   - Trio nurseries do the same ([trio-nursery]), and so do AnyIO task groups ([anyio-taskgroup]).
   - `asyncio.gather` does not: "Other awaitables in the *aws* sequence **won't be cancelled** and will continue to run" ([aio-gather]).
   - No library lets a single task opt out.
3. **Partial results.**
   - Task groups raise an `ExceptionGroup` of the failures, without the cancelled siblings ([aio-group-raise]).
   - Values are reachable only through the handles the caller kept. Trio offers none.
   - `gather(return_exceptions=True)` returns exceptions in place of values ([aio-return-exceptions]).
   - Trio changed its default to always raise groups in 0.25.0. Its explanation: callers "would work well in testing, and then crash under heavier load" when a function could sometimes raise a group ([trio-strict-why]).
4. **Retries.** None in any of the three. Two query formulations over every documentation file of each project found only an entry for `tenacity` in Trio's list of third-party libraries. On side effects, Trio documents that raising `Cancelled` "means that the operation *did not happen*" for its own primitives ([trio-did-not-happen]).
5. **Fallback.** None. The nearest pattern is the `asyncio.shield` example that catches `CancelledError` and sets `res = None`, which the docs call "not recommended".
6. **Cancellation.**
   - `asyncio` throws `CancelledError` into the coroutine "at the next opportunity" ([aio-cancel-inject]), and the coroutine may suppress it. Trio and AnyIO cancel scopes are level-triggered.
   - A running thread cannot be interrupted:
     - `concurrent.futures.Future.cancel` fails once the call is running ([cf-cancel]);
     - `shutdown(cancel_futures=True)` cancels only work that has not started ([cf-shutdown]);
     - Trio: "neither Python nor the operating systems it runs on provide any general mechanism for cancelling an arbitrary synchronous function running in a thread" ([trio-thread]).
   - Recording why:
     - Trio's `Cancelled` carries `source`, which is one of `KeyboardInterrupt`, `deadline`, `explicit`, `nursery`, `shutdown` or `unknown`. Siblings of a failing child get `source="nursery"` and a reason naming the child's exception ([trio-cancel-source]).
     - `asyncio.Task.cancel(msg)` takes a message, but `TaskGroup` cancels siblings with no message ([aio-taskgroup-abort]).
   - Timeouts turn cancellation into `TimeoutError`, which the outer code sees as a failure ([aio-timeout]).
- **"Skipped":** none. Work not run because a sibling failed is either never created (`TaskGroup.create_task` raises during shutdown) or ends cancelled before it starts. **Changes:**
  - Python 3.11 added `TaskGroup`, `uncancel` and the cancel count.
  - Python 3.13 made `create_task` on an inactive group close the coroutine.
  - Trio 0.25.0 made strict exception groups the default.
  - AnyIO 4.0.0 moved to PEP 654 groups.
  - Trio 0.31.0 and AnyIO 4.11.0 added cancellation reasons.

### Comparison

The table maps each system's words onto this report's terms. "Not stored" means that no state or event records the case.

| | Dask 2026.8.0 | Prefect 3.9.3 | Dagster 1.13.30 | Airflow 3.4.0 | asyncio / Trio / AnyIO |
|---|---|---|---|---|---|
| Succeeded | `memory` / `finished` | `Completed` | `STEP_SUCCESS` | `success` | returned (`FINISHED`) |
| Failed | `erred` / `error` | `Failed`, `Crashed` | `STEP_FAILURE` | `failed` | raised (`FINISHED` + exception) |
| Blocked | `erred` + `exception_blame` | `Pending`/`NotReady` (never terminal) | abandoned, not stored | `upstream_failed` (terminal) | not applicable |
| Skipped (branch not selected) | none | no run, no state | `STEP_SKIPPED` (optional output not produced) | `skipped` (one of many meanings) | none |
| Cancelled | `Future` `cancelled` with reason; no scheduler state | `Cancelled` (flow runs; tasks via cleanup) | run `CANCELED`; step ends `STEP_FAILURE` (interrupt) | none (`failed`, `skipped` or `restarting`) | `CANCELLED`; Trio `source` |
| Default on a failure | dependents err, siblings run | dependents NotReady, siblings run | dependents abandoned, siblings run | dependents `upstream_failed`, siblings run; `fail_fast` opt-in | task group cancels siblings; `gather` does not |
| Opt in to consume a failure | none | `allow_failure` (receives exception) | none | 13 trigger rules (receives `None`) | catch in the task |
| Partial results | per `Future`; `gather(errors="skip")` | return value or `State`; `wait()` + `.state` | result object per node; raises by default in process | XComs of succeeded tasks | exception group; handles if kept |
| Retry identity | hidden `run_id` per dispatch | `run_count` on the same run | `retry_number` on the same step key | `try_number`, one row (UUID) per try | none |
| Retry limits | count only | count, delays, jitter, condition | count, delay, backoff, jitter; `Failure(allow_retries=False)` | count, delay, backoff, cap; policies | none |
| Side-effect assumption | functions are pure | caching and transactions; no automatic undo | not stated | tasks must be idempotent | Trio: `Cancelled` means "did not happen" |
| Fallback value | none | none | none | none (implicit `None`) | none |
| Running sync work on cancel | runs on, result discarded | not interrupted (thread pool) | SIGINT raised in the main thread | SIGTERM, `on_kill`, SIGKILL | cannot be interrupted |

### Where the systems disagree

These disagreements are real, and this report keeps them open rather than forcing a consensus. The proposal picks a side for Hamilton and says why; the evidence does not settle them in general.

- **Blocked: stored, folded, or derived?** Airflow stores it as terminal; Prefect stores it as non-terminal; Dask folds it into failure with a cause pointer; Dagster derives it from missing events.
  - Each choice has a documented cost:
    - Airflow's creation of the state is self-described as a hack.
    - Prefect's `NotReady` never ends, and `allow_failure` depends on matching its name.
    - Dask's client cannot tell a dependent's error from the root's without reading `exception_blame`.
    - Dagster's result API needs a separate "untouched" predicate.
  - Dagster also keeps an `UPSTREAM_FAILED_TO_MATERIALIZE` reason at the asset level.
- **Siblings: continue or cancel?** Dask and the three orchestrators continue by default. All three concurrency libraries cancel inside a task group. Airflow offers fail-fast as an option, and then marks unfinished work `skipped`.
- **Cancelled: a state or not?** Prefect and the concurrency libraries have it. Airflow has none, and Dagster has it only at run level, recording an interrupted step as a failure. Dask has it only on the client's `Future`.
- **"Skipped": one meaning or many?** Dagster limits it to "optional output not produced". Airflow uses it for many causes, including cancellation side effects. Dagster's own changelog shows the cost of such overloading: "dbt Fusion reports both a genuine no-op and an upstream-failure skip as `skipped`", so dagster-dbt must treat `skipped` as a failure ([dagster-dbt-skip]).

## Proposal for Hamilton

The proposal is for the 2.0 release. The prototype on the `2.0` branch implements only what its Tickets already require: fail-fast, cancellation of unfinished work, and cleanup (Tickets 11, 12 and 16). It also keeps task identity that tells attempts apart (Ticket 07).

### Principles

1. **An outcome records what happened to the task, not what the run asked for.** This is how `asyncio` and `concurrent.futures` behave: a cancel request does not make a running task cancelled ([aio-cancelled-def], [cf-cancel]). The principle matters because Hamilton nodes write through materializers. An operator who reads `cancelled` must be able to rely on the node's work not having finished.
2. **One terminal outcome per task, reported exactly once.** Every task the run creates ends in exactly one outcome, and observers are told exactly once. A mapped instance that was never created, because its expander failed or the run stopped first, has no outcome. The expander's and the collector's outcomes cover it.
3. **No in-band sentinels.** A failure is never represented by a value that a node could also return. Probe 2 shows why.
4. **Nothing needs stored state.** Every outcome is decided within the run, by the coordinator, from the run's own state. Nothing survives the process.

### Outcome states

| Outcome | Meaning | Produced by | Carries |
|---|---|---|---|
| `succeeded` | The task's last attempt returned a value. The value may be `None`. | every policy | the value, which goes to dependents and the result builder |
| `failed` | The task's last attempt raised an exception, and no policy recovered it. | every policy | the exception |
| `cancelled` | The run stopped the task before it finished, whether it had started or not. | every policy | a cause: the task whose failure stopped the run, or the caller (for example `KeyboardInterrupt`, or cancellation of the awaiting task under `aexecute`) |
| `blocked` | The task did not start because a prerequisite ended `failed` or `blocked`. | best-effort only | the root failed task or tasks |
| `skipped` | A runtime branch decision did not select the task's path. | runtime branching only (Ticket 26) | the branch decision, as Ticket 26 defines it |

The non-terminal phases are `pending` (waiting for prerequisites) and `running` (an attempt is executing). They are events that observers may see, not outcomes. When retry exists, a third phase, "awaiting retry", sits between a failed attempt and the next one.

### Transitions

Under the default policy, fail-fast:

- `pending` → `running` → `succeeded` or `failed`.
- `pending` → `cancelled` when the run stops before the task starts. The cause is the first failure, or the caller.
- `running` → `cancelled` only when the work actually stopped: a coroutine that let its `CancelledError` propagate, or a future backend task that honours a cancel.
- A synchronous task that is running when the run decides to stop cannot be interrupted. The run waits for it, as Ticket 12 already requires, and records what it did: `succeeded` or `failed`. Its value is discarded, because the run is failing.
- A coroutine that catches its cancellation and returns a value ends `succeeded` (principle 1).
- A timeout, if one is added later, ends the task `failed` with `TimeoutError`, as in `asyncio.timeout` ([aio-timeout]), Prefect's `TimedOut` (type FAILED) and Airflow.

Under best-effort, which is opt-in, a task's failure does not stop the run, and the transitions change as follows:

- `pending` → `blocked` when a prerequisite ends `failed` or `blocked`, unless the task opted in to consume that failure (decision 8).
- Independent tasks continue as normal.
- If the caller stops the run, every unfinished task ends `cancelled` with the caller as cause.

When runtime branching exists, a further transition is added: `pending` → `skipped`. Ticket 26 defines when it applies. This report fixes only that `skipped` is not a failure, so a skipped prerequisite never makes a dependent `blocked`.

When retry exists, a failed attempt is followed by "awaiting retry" and then a new attempt, until the limit is reached. Each attempt is reported with its own number. The task's outcome is the outcome of its last attempt.

### What the caller sees

- **Fail-fast.** The caller receives the failing node's own exception, unchanged: not a group, and not a wrapper (Ticket 12 requires this). If two tasks fail concurrently, the first failure the coordinator observed is raised. The other failure still ends as `failed` and reaches observers. No values are returned. The values of the tasks that succeeded reach observers through the post-node events, as on 1.x. This matches `execute_in_process` in Dagster, the Dask local schedulers, and `asyncio.TaskGroup` without kept handles.
- **Best-effort.** The run never reports success when a requested output did not succeed. The recommended surface is a Hamilton exception raised at the end of the run, carrying the run's outcomes and the values of the requested outputs that succeeded. Nothing is put in place of the missing ones. A caller that opted in to partial results catches one documented exception type. The decision record leaves the exact type to the Ticket that builds best-effort.

### Which policies belong in the first 2.0 release

| Policy | In the first 2.0 release? | Why |
|---|---|---|
| Fail-fast with cancellation and cleanup | Yes, as the default | The owner chose it for the prototype. It is what an in-process call does in `asyncio.TaskGroup`, Trio and AnyIO. With no store to keep independent results, work after a failure is wasted unless a policy returns it. |
| Best-effort, opt-in per run | Yes, if that release leaves no 1.x execution path to select; otherwise later (decision 7) | `GracefulErrorAdapter` is 1.x's only graceful mechanism, and it cannot run on the new runtime: it takes over node execution, which the plan refuses with the switch on, and its `Parallelizable` branch depends on the callable rewrite ([h-graceful-callable], [h-rewrite]). Once no 1.x path can be selected, its users have no path without best-effort. While one can, they can stay on it, as the owner's ruling for the prototype already has it. |
| Typed opt-in for a node to consume a prerequisite's failure | Together with best-effort | It replaces `@accept_error_sentinels` and the "gather what succeeded" use in `examples/parallelism/graceful_running`. The prior art is Prefect's `allow_failure`, which passes the exception, and Airflow's trigger rules, which pass `None` with no way to tell. The node receives an outcome object (failed or blocked, with the exception), never a sentinel. |
| Retry, as a first-party policy | No; the contracts keep attempt identity | In-function retry already works on every path, as in [h-tenacity]. Ticket 07's node-call wrapper contract lets third-party code retry around a node call. Hamilton cannot yet tell an idempotent node from a materializer that writes. |
| Fallback, meaning value substitution | No | None of the systems compared has it. The one 1.x implementation shows the hazard (Probe 2). The consumer opt-in above covers the documented use cases without hiding a failure. |

These conclusions apply to the 2.0 release only. The prototype implements none of the last four rows, whatever the owner decides.

### What a retry policy would have to settle later

If a retry policy is proposed later, the evidence says it must settle the following:

- **Attempt identity.** The attempt number belongs to the task identity, as in Ticket 07. The precedents are Dagster's `retry_number`, Prefect's `run_count` and Airflow's `try_number`.
- **Limits and conditions.** A limit and an exception condition are needed. Dagster's `Failure(allow_retries=False)` and Prefect's `retry_condition_fn` are the two precedents.
- **Side-effect policy.**
  - Retry is opt-in per node, and is not offered for materializer and data-saver nodes unless they declare themselves idempotent.
  - Airflow's rule ("tasks should produce the same outcome on every re-run") states the obligation.
  - Prefect's "does not automatically undo" warns against promising more.
  - The outline: reusing node outputs "does not by itself make external writes safe to resume".
- **Cache interplay.** A failed attempt writes nothing to the cache.
- **Cleanup.** Context managers and `finally` blocks of a failed attempt complete before the next attempt starts.
- **Delays.** Within one run, a delay holds the run's resources, unlike in an orchestrator, which can free a worker while a retry waits.

## Alternatives ranked

Four designs for the outcome states were compared against six criteria. The criteria, and the frame each serves:

1. **Observer clarity (operator).** Can an observer tell, from one outcome, why a task produced no value, without walking the graph?
2. **Contract stability (maintainer).** Will third-party observers and backends written against 2.0 keep working when later policies arrive?
3. **Consistency with the backends' own semantics (maintainer).** Do the outcomes match what `asyncio` and `concurrent.futures` actually report?
4. **Fit with the effort's Tickets 11, 12 and 16.** Each of them expects failed and cancelled outcomes.
5. **Concepts for the pipeline author.** How many states must a node author learn?
6. **No stored state.**

| Design | 1 Clarity | 2 Stability | 3 Consistency | 4 Fit | 5 Concepts | 6 Stateless | Rank |
|---|---|---|---|---|---|---|---|
| **A. Proposed:** `succeeded`, `failed`, `cancelled` with cause; `blocked` and `skipped` defined, each produced only by its policy | good: each outcome has one cause class | good, if the 2.0 type carries every state the 2.x line will produce (decision 2) | good | good | five states, two of them only for opt-in policies | yes | 1 |
| **B. Minimal forever:** `succeeded`, `failed`, `cancelled`; best-effort dependents are `cancelled` with cause "prerequisite failed" (Trio's reason-field approach) | weaker: `cancelled` gains a meaning in which nothing was stopped, so every consumer must read the cause to count failures | best: the type never grows | good | good | three | yes | 2 |
| **D. Derived:** no `blocked`; observers infer it from `failed` plus the graph (Dagster's "abandoned"). This is the counter-hypothesis the Ticket names. | weak: an observer needs the plan, and mapped instances of a failed expander cannot be inferred | good | good | equal to A under fail-fast | three | yes | 3 |
| **C. Orchestrator-sized:** Airflow-like states, such as `upstream_failed`, `up_for_retry`, `removed` and a crashed state | good for each case | poor: needs states with no meaning in one process (`removed`, crashed) and stored scheduling | poor | adds states no Ticket uses | many | partly | 4 |

B is the strongest alternative, and A beats it on criterion 1 only. The evidence for that criterion is what happens when one label covers several causes: Airflow's many meanings of `skipped`, the dbt conflation recorded in Dagster's changelog, and Dask's need for `exception_blame`. Against that stands Trio's design, which puts the cause in a field and keeps one cancelled state. If the owner weighs contract stability above observer clarity, B is a sound choice; decision 2 is where that weighing happens. Under the default policy, A, B and D produce the same outcomes. They differ only once best-effort exists.

## Counter-arguments engaged

- **"Hamilton needs no `blocked` state, because failed dependents can be derived."** This holds under fail-fast, where `blocked` never occurs. Under best-effort the derivation needs the plan and the run's mapped instances, which observers do not have. Dagster's own result API had to add an "untouched" predicate ([dagster-untouched]), and its asset level keeps an explicit upstream-failed reason. This is design D, ranked third.
- **"Best-effort should stay out of 2.0, as the owner ruled for the prototype; users can catch exceptions inside nodes."** This is the strongest argument against the proposal. The ruling covers the prototype "until feedback settles their semantics", and this report is part of that feedback. The case for best-effort in the release rests on `GracefulErrorAdapter` having users. The repository has an example and docs for it, but **there is no usage data**: no download or telemetry figure separates the adapter's users. If the release that makes the new runtime the default still lets users select a 1.x execution path, `GracefulErrorAdapter` users can stay on it, and best-effort can wait for a later 2.x release. Decision 7 states both answers.
- **"Fail-fast is the wrong default; Dask and every orchestrator continue independent work."** In those systems continued work is not lost. The orchestrators persist each task's result in a store: an XCom table, an event log or a result record. Dask keeps each result reachable through the `Future` handle the client holds, as AnyIO's `TaskHandle` does within a task group. Hamilton's `execute` returns one result to one caller and offers neither a store nor per-task handles. Work continued after a failure is lost under fail-fast, and is recoverable only through a best-effort policy that returns it. That is why best-effort is opt-in rather than absent.
- **"Users expect retries; Dask and every orchestrator have them."** True, and the proposal keeps attempt identity so that retry can be added without changing the contracts. Against first-party retry in the first release: Hamilton cannot yet tell idempotent nodes from writers, and in-function retry plus the wrapper contract covers the transient-I/O case. The cost of deferring is real: a generated node, such as a loader from `@load_from`, cannot carry a tenacity decorator, and in-function retries are invisible to observers and to the cache.
- **"`cancelled` for a never-started task is not a cancellation."** Ticket 26 initially read cancelled as "started or queued, then stopped". This report's definition, which Ticket 26 adopted, covers never-started tasks too. Under fail-fast the only alternatives for such a task are `blocked`, which wrongly suggests a policy kept running, or no outcome, which breaks principle 2. Python's own `concurrent.futures` uses `CANCELLED` for work that never started ([cf-shutdown]).

## Three frames

- **Pipeline author.**
  - On a failure, the author gets the node's own exception, as on 1.x.
  - Partial results require an explicit opt-in, and the author never receives a sentinel.
  - A node that wants a prerequisite's failure declares it and receives a typed outcome.
  - Retry stays inside the node function, or in a wrapper.
- **Maintainer.**
  - One outcome type, with a cause on `cancelled` and `blocked`.
  - One invariant: one outcome per created task, reported once.
  - The conformance kit (Ticket 15) can check that invariant against any backend.
  - Adding a state after 2.0.0 would break third-party observers that match outcomes exhaustively, which is the reason for decision 2.
- **Operator.**
  - Each outcome has one meaning, so counts in a tracker add up.
  - The Hamilton UI and its tracking SDK know only four states ([h-sdk-status], [h-ui-migration]). Showing `cancelled`, `blocked` or `skipped` there needs a schema migration in the UI server. That is outside this effort, and it is debt for whoever connects the tracker to the new runtime.

## What this report and Ticket 26 agree on

Ticket 26's agent and this report's author exchanged definitions while both surveys were open. Both reports use them:

- `skipped` means only "not executed because a runtime branch decision did not select its path".
- `blocked` means "not executed because a prerequisite failed or was blocked", and arises only under best-effort.
- `cancelled` means "the run stopped the task before it finished, whether it had started or not".
- A skipped prerequisite is not a failure and never produces `blocked`.

Ticket 26 decides whether `skipped` propagates to dependents, how a join treats a skipped input, and what happens to a requested output on an unselected path.

## Decisions for the owner

Each decision lists the options, the recommendation, and what changes in Ticket 07's contracts with each answer.

1. **Outcome vocabulary and the recording rule.**
   - Options:
     - (a) `succeeded`, `failed`, `cancelled`, where an outcome records what happened (a running synchronous task finishes as `succeeded` or `failed`; a timeout is `failed`);
     - (b) the same states, but a task running when the run stops is recorded as `cancelled`.
   - **Recommendation: (a).**
   - Ticket 07: with (a), the coordinator reports a running synchronous task's real outcome after waiting for it. With (b), it reports `cancelled` and discards a value that may come with side effects already done.
2. **Which states the 2.0 outcome type carries.**
   - Options:
     - (a) exactly the states that the 2.0 policies produce, adding others in later releases;
     - (b) every state the 2.x line is expected to produce: `blocked` if decision 7 adopts best-effort for 2.x, and `skipped` if Ticket 26's decision adopts runtime branching. A state that no policy yet produces is documented as such.
   - **Recommendation: (b).** Adding a member after 2.0.0 is a breaking change for observers that match outcomes exhaustively.
   - Ticket 07: (b) adds one or two documented members that the slice never produces. That is in tension with Ticket 07's instruction to make illegal states unrepresentable: a member no policy produces is representable but unreachable, so the contract author must document it as reserved and the conformance kit must not expect it. (a) keeps the type at three members, and later Tickets add members with migration notes.
3. **Unfinished tasks under fail-fast.**
   - Options:
     - (a) every task that has not finished ends `cancelled`: independent siblings and never-started dependents alike;
     - (b) dependents of the failure end `blocked` and siblings `cancelled`;
     - (c) only started tasks get an outcome.
   - **Recommendation: (a), together with the invariant "one outcome per created task, reported once".**
   - Ticket 07: (a) needs one terminal transition, from pending or running to cancelled. (b) makes the coordinator classify each unfinished task against the failure. (c) leaves observers unable to tell a never-started task from a lost one.
4. **A cause on `cancelled`.**
   - Options:
     - (a) a structured cause: the failed task's identity, or "caller";
     - (b) free text;
     - (c) none, as `asyncio.TaskGroup` does.
   - **Recommendation: (a).** Trio's `Cancelled.source` and Dask's `FutureCancelledError(reason)` are the precedents.
   - Ticket 07: (a) adds a small cause type to the outcome data, which must stay serializable for an out-of-process backend. (b) and (c) add nothing.
5. **What the caller receives under fail-fast.**
   - Options:
     - (a) the failing node's own exception unchanged, the first one observed, with other failures visible only to observers;
     - (b) an exception group of all failures;
     - (c) a Hamilton exception wrapping the node's exception and carrying the outcomes.
   - **Recommendation: (a).** Ticket 12 already requires that the caller sees the node's own error.
   - Ticket 07: (a) adds no type. (b) and (c) add a public exception type and change what callers catch, which is a migration item.
6. **How `cancelled` reaches 1.x hooks through the bridge (Tickets 10 and 12).**
   - Options:
     - (a) `post_node_execute` is called only for tasks that had `pre_node_execute`; a started-then-cancelled task gets `success=False` and its cancellation exception as `error`; never-started tasks reach no 1.x hook; `post_graph_execute` gets `success=False` and the raised error;
     - (b) also call `post_node_execute` for never-started cancelled tasks.
   - **Recommendation: (a).** It keeps the 1.x pairing of pre and post calls.
   - Ticket 07: the hook-mapping table in its decision record states (a) or (b).
7. **Best-effort in the first 2.0 release.**
   - Options:
     - (a) yes: an opt-in run policy that produces `blocked`, never reports success when a requested output did not succeed, and raises one documented exception carrying outcomes and the succeeded values;
     - (b) not in the first release: `GracefulErrorAdapter` stays on the 1.x execution paths for as long as 2.x lets users select one;
     - (c) never: authors catch exceptions in nodes.
   - **Recommendation: (a) if the release that makes the new runtime the default leaves users no 1.x execution path to select; otherwise (b).** The condition is about every 1.x path, not only the task-based one: the adapter works on the default path (Probe 2), and it fails on the new runtime because it takes over node execution. Confidence is limited, because there is no usage data for the adapter.
   - Ticket 07: none for the slice. With (a) or (b), the contracts reserve `blocked` (see decision 2) and the run outcome "failed with partial results"; with (c) they do not.
8. **A typed opt-in for a node to consume a prerequisite's failure.**
   - Options:
     - (a) in the same release as best-effort: a per-parameter declaration through which the node receives an outcome object (failed or blocked, with the exception) and runs;
     - (b) later;
     - (c) never.
   - **Recommendation: (a)**, tied to decision 7. It replaces `@accept_error_sentinels` and covers gathering the items that succeeded in a `Collect`.
   - Ticket 07: none for the slice. The outcome object must be a public type if (a) is chosen.
9. **First-party retry in the first 2.0 release.**
   - Options:
     - (a) no: attempt identity stays in the contracts, the wrapper contract allows third-party retry, and the docs point to in-function retry with its side-effect caveat;
     - (b) yes: per-node, opt-in, count and condition, refused on materializers unless they are declared idempotent.
   - **Recommendation: (a).**
   - Ticket 07: (a) keeps the attempt field that Ticket 07 already scopes, and nothing else. (b) adds an "awaiting retry" phase and per-attempt events to the observer contract.
10. **Fallback (value substitution) in the first 2.0 release, and the fate of `GracefulErrorAdapter`.**
    - Options:
      - (a) no fallback: `GracefulErrorAdapter` and `@accept_error_sentinels` get migration instructions pointing to decisions 7 and 8 for the day the new runtime becomes the default;
      - (b) a fallback rule per node that substitutes a typed value, while the task's outcome stays `failed`.
    - **Recommendation: (a).**
    - Ticket 07: (a) adds nothing. (b) adds a "substituted" mark to the failed outcome and a substitution step to the coordinator.
11. **Agreement with Ticket 26 on `skipped`.**
    - Options:
      - (a) `skipped` means only "branch not selected", is not a failure, and never produces `blocked`;
      - (b) `skipped` also covers "not run because upstream failed", as in Airflow's cascades.
    - **Recommendation: (a).** Both surveys use it.
    - Ticket 07: none until Ticket 26's decisions. With (b), `blocked` and `skipped` would merge.

## Confidence, gaps and assumptions

- **Strong evidence**, from source and docs at the tag, consistent across files:
  - the state sets of every system;
  - how each treats dependents;
  - that no system has a value fallback;
  - that running threads cannot be interrupted;
  - the retry parameters and attempt identities.
- **Limited evidence:**
  - That Prefect's thread-pool runner leaves a task cancelled before its function starts as `Crashed` locally. This is a source trace, and no test asserts it.
  - That Dagster has no emitter of the asset-level `UPSTREAM_FAILED_TO_MATERIALIZE` reason in core. It may be in another package.
  - That Airflow's `/wait` endpoint returns results for failed runs. This is a source reading; the docs show only a success example.
  - That the Dask multiprocessing scheduler lets in-flight tasks finish. This is inferred from the standard library's `shutdown()` defaults.
  - These points are noted for completeness. None of them is a claim the proposal turns on.
- **Documentation and code disagree in four places:**
  - Airflow's docs list a `canceled` DagRun state that the code does not have.
  - Airflow's docs say clearing sets `max_tries` to 0, which the code does not do.
  - AnyIO's `TaskHandle.status` docstring disagrees with its code.
  - Prefect's states page lists three terminal categories but omits `CANCELLED`, which the code treats as terminal.
  - In each case this report follows the code.
- **Gaps.**
  - There is no usage data for `GracefulErrorAdapter` (decision 7).
  - The Hamilton UI was not examined beyond its status enum and first migration.
  - Systems not named by the owner (Ray, Luigi, Kedro) were not surveyed.
  - Timeouts and crash recovery are out of scope.
- **Assumptions.**
  - The first 2.0 release is the one that makes the new runtime the default; that release's plan is not decided.
  - The probes ran on one machine with CPython 3.15.0. They establish 1.x behavior, not timing claims.

## How the citations were verified

On 2026-11-17 a script fetched each of the 97 cited files in raw form at its tag or commit. For each reference it checked one to five phrases that the claim depends on, including every phrase this report quotes from that reference. Each phrase had to occur within the cited line range, after whitespace and comment markers were normalized. Three quotations from the outline were checked against the discussion text. All 159 checks passed. The first run found four failures, and each was corrected before the final run:

- two line ranges were too narrow;
- one quotation included emphasis markup that the source does not have;
- the checker did not strip the source's `#:` comment markers.

A phrase check confirms that the quoted words are where the citation says. It does not confirm that the claim built on them is a fair reading. For the claims the proposal turns on, the working notes record the surrounding source as well as the quoted lines. Those claims are the treatment of dependents in each system, the absence of fallback, and that running threads cannot be interrupted.

## Appendix: probes

Each probe ran from a scratch directory outside the repository with `uv run python <script>`, against the `2.0` branch at `31b3a832`. Each was run once; Probe 1 loops ten times within its run.

Probe 1, siblings on the task-based path (module `probe_map_mod.py`):

```python
import time
from hamilton.htypes import Collect, Parallelizable

EVENTS = []


def item() -> Parallelizable[int]:
    yield from range(4)


def work(item: int) -> int:
    if item == 0:
        time.sleep(0.05)
        EVENTS.append((f"item {item} raises", time.monotonic()))
        raise ValueError("boom")
    EVENTS.append((f"item {item} starts", time.monotonic()))
    time.sleep(0.5)
    EVENTS.append((f"item {item} finishes", time.monotonic()))
    return item


def gathered(work: Collect[int]) -> list[int]:
    return list(work)
```

It was driven ten times by `driver.Builder().with_modules(probe_map_mod).enable_dynamic_execution(allow_experimental_mode=True).with_remote_executor(executors.MultiThreadingExecutor(max_tasks=4)).build().execute(["gathered"])`. Each run recorded when the `ValueError` reached the caller.

Probe 2, `GracefulErrorAdapter` with the default sentinel:

```python
from typing import Optional


def maybe_value() -> Optional[int]:
    return None  # a legitimate result, no error


def uses_it(maybe_value: Optional[int]) -> str:
    return "ran with " + repr(maybe_value)
```

It was executed with no adapter, then with `GracefulErrorAdapter(error_to_catch=ValueError)`, requesting `["uses_it"]`.

## References

Each bracketed label in the text, such as [h-taskstate], is a link to the cited lines at the stated tag or commit. The link definitions are below, grouped by system; they are visible in the Markdown source.

<!-- Hamilton, commit ef88b1e9 of apache/hamilton -->

[h-taskstate]: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/execution/state.py#L29-L39
[h-post-node]: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/lifecycle/base.py#L646-L657
[h-post-graph]: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/lifecycle/base.py#L793-L800
[h-sdk-status]: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/ui/sdk/src/hamilton_sdk/tracking/trackingtypes.py#L23-L27
[h-ui-migration]: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/ui/backend/server/trackingserver_run_tracking/migrations_sqlite/0001_initial.py#L51-L54
[h-raise]: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/execution/executors.py#L470-L502
[h-finalize]: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/execution/executors.py#L307-L313
[h-gather]: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/async_driver.py#L33-L38
[h-tenacity]: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/contrib/hamilton/contrib/user/zilto/webscraper/__init__.py#L58-L60
[h-graceful]: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/lifecycle/default.py#L592-L612
[h-graceful-sentinel]: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/lifecycle/default.py#L739-L753
[h-graceful-callable]: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/lifecycle/default.py#L755-L759
[h-accept]: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/lifecycle/default.py#L545-L556
[h-rewrite]: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/execution/executors.py#L128-L131

<!-- Dask, dask/distributed and dask/dask at 2026.8.0 -->

[dask-states]: https://github.com/dask/distributed/blob/2026.8.0/distributed/scheduler.py#L158-L167
[dask-future-status]: https://github.com/dask/distributed/blob/2026.8.0/distributed/client.py#L377-L392
[dask-internal]: https://github.com/dask/distributed/blob/2026.8.0/docs/source/scheduling-state.rst#L43-L46
[dask-propagate]: https://github.com/dask/distributed/blob/2026.8.0/distributed/scheduler.py#L2844-L2846
[dask-futures-err]: https://github.com/dask/dask/blob/2026.8.0/docs/source/futures.rst#L223
[dask-blame]: https://github.com/dask/distributed/blob/2026.8.0/distributed/scheduler.py#L1326-L1328
[dask-local-raise]: https://github.com/dask/dask/blob/2026.8.0/dask/local.py#L536-L547
[dask-gather-skip]: https://github.com/dask/distributed/blob/2026.8.0/distributed/client.py#L2495-L2496
[dask-retries]: https://github.com/dask/distributed/blob/2026.8.0/distributed/scheduler.py#L1298-L1302
[dask-run-id]: https://github.com/dask/distributed/blob/2026.8.0/distributed/scheduler.py#L1385-L1390
[dask-pure]: https://github.com/dask/distributed/blob/2026.8.0/docs/source/client.rst#L118-L123
[dask-cancel-running]: https://github.com/dask/distributed/blob/2026.8.0/docs/source/worker-state.rst#L215-L222
[dask-cancel-reason]: https://github.com/dask/distributed/blob/2026.8.0/distributed/client.py#L693-L694

<!-- Prefect, PrefectHQ/prefect at 3.9.3 (and 2.20.27 where stated) -->

[prefect-statetype]: https://github.com/PrefectHQ/prefect/blob/3.9.3/src/prefect/client/schemas/objects.py#L89-L100
[prefect-terminal]: https://github.com/PrefectHQ/prefect/blob/3.9.3/src/prefect/client/schemas/objects.py#L103-L108
[prefect-states-doc]: https://github.com/PrefectHQ/prefect/blob/3.9.3/docs/v3/concepts/states.mdx#L38-L59
[prefect-crash]: https://github.com/PrefectHQ/prefect/blob/3.9.3/src/prefect/task_engine.py#L923-L941
[prefect-notready]: https://github.com/PrefectHQ/prefect/blob/3.9.3/src/prefect/task_engine.py#L984-L998
[prefect-notready-test]: https://github.com/PrefectHQ/prefect/blob/3.9.3/tests/test_tasks.py#L876-L894
[prefect-allow-failure]: https://github.com/PrefectHQ/prefect/blob/3.9.3/src/prefect/utilities/annotations.py#L55-L67
[prefect-allow-failure-scope]: https://github.com/PrefectHQ/prefect/blob/3.9.3/src/prefect/utilities/engine/__init__.py#L1013-L1021
[prefect-v3-final]: https://github.com/PrefectHQ/prefect/blob/3.9.3/docs/v3/how-to-guides/migrate/upgrade-to-prefect-3.mdx#L66-L88
[prefect-v2-final]: https://github.com/PrefectHQ/prefect/blob/2.20.27/docs/concepts/states.md#L170-L178
[prefect-wait]: https://github.com/PrefectHQ/prefect/blob/3.9.3/docs/v3/how-to-guides/workflows/run-work-concurrently.mdx#L361-L408
[prefect-retry-params]: https://github.com/PrefectHQ/prefect/blob/3.9.3/src/prefect/tasks.py#L346-L357
[prefect-run-count]: https://github.com/PrefectHQ/prefect/blob/3.9.3/src/prefect/task_engine.py#L598-L599
[prefect-caching]: https://github.com/PrefectHQ/prefect/blob/3.9.3/docs/v3/concepts/caching.mdx#L7-L19
[prefect-no-undo]: https://github.com/PrefectHQ/prefect/blob/3.9.3/docs/v3/advanced/transactions.mdx#L194-L206
[prefect-cancel-flow]: https://github.com/PrefectHQ/prefect/blob/3.9.3/docs/v3/advanced/cancel-workflows.mdx#L14-L18
[prefect-sync-timeout]: https://github.com/PrefectHQ/prefect/blob/3.9.3/docs/v3/how-to-guides/workflows/write-and-run.mdx#L124-L128
[prefect-runner-exit]: https://github.com/PrefectHQ/prefect/blob/3.9.3/src/prefect/task_runners.py#L541-L546
[prefect-skipped]: https://github.com/PrefectHQ/prefect/blob/3.9.3/docs/v3/concepts/flows.mdx#L443-L458

<!-- Dagster, dagster-io/dagster at 1.13.30 -->

[dagster-events]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/events/__init__.py#L124-L125
[dagster-step-status]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/execution/stats.py#L114-L118
[dagster-active-sets]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/execution/plan/active.py#L106-L124
[dagster-run-status]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/storage/dagster_run.py#L55-L89
[dagster-abandon]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/execution/plan/active.py#L499-L524
[dagster-untouched]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/execution/execution_result.py#L133-L134
[dagster-skip-precedence]: https://github.com/dagster-io/dagster/blob/1.13.30/CHANGES.md#L4674
[dagster-loop]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/execution/plan/execute_plan.py#L59
[dagster-run-fail]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/execution/api.py#L815-L833
[dagster-retry-policy]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/definitions/policy.py#L35-L60
[dagster-retry-number]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/execution/context/op_execution_context.py#L569-L573
[dagster-interrupt-retry]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/execution/plan/utils.py#L94-L104
[dagster-default-value]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/definitions/input.py#L412
[dagster-interrupt]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/execution/plan/utils.py#L52
[dagster-interrupt-failure]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/execution/plan/execute_plan.py#L318-L326
[dagster-branching]: https://github.com/dagster-io/dagster/blob/1.13.30/docs/docs/guides/build/ops/graphs.md#L74-L76
[dagster-dbt-skip]: https://github.com/dagster-io/dagster/blob/1.13.30/CHANGES.md#L127

<!-- Airflow, apache/airflow at 3.4.0 -->

[airflow-ti-states]: https://github.com/apache/airflow/blob/3.4.0/airflow-core/docs/core-concepts/tasks.rst#L72-L87
[airflow-terminal]: https://github.com/apache/airflow/blob/3.4.0/airflow-core/src/airflow/utils/state.py#L37-L44
[airflow-state-groups]: https://github.com/apache/airflow/blob/3.4.0/airflow-core/src/airflow/utils/state.py#L226-L238
[airflow-upstream-failed]: https://github.com/apache/airflow/blob/3.4.0/airflow-core/src/airflow/ti_deps/deps/trigger_rule_dep.py#L478-L486
[airflow-hack]: https://github.com/apache/airflow/blob/3.4.0/airflow-core/src/airflow/ti_deps/dep_context.py#L57-L60
[airflow-trigger-rules]: https://github.com/apache/airflow/blob/3.4.0/airflow-core/docs/core-concepts/dags.rst#L435-L447
[airflow-xcom-none]: https://github.com/apache/airflow/blob/3.4.0/task-sdk/src/airflow/sdk/definitions/xcom_arg.py#L364-L381
[airflow-leaves]: https://github.com/apache/airflow/blob/3.4.0/airflow-core/docs/core-concepts/dag-run.rst#L29-L41
[airflow-retry-params]: https://github.com/apache/airflow/blob/3.4.0/task-sdk/src/airflow/sdk/bases/operator.py#L702-L712
[airflow-try-rows]: https://github.com/apache/airflow/blob/3.4.0/RELEASE_NOTES.rst#L340-L363
[airflow-idempotent]: https://github.com/apache/airflow/blob/3.4.0/airflow-core/docs/best-practices.rst#L47-L57
[airflow-heartbeat-kill]: https://github.com/apache/airflow/blob/3.4.0/task-sdk/src/airflow/sdk/execution_time/supervisor.py#L2054-L2070
[airflow-fail-fast]: https://github.com/apache/airflow/blob/3.4.0/airflow-core/src/airflow/models/taskinstance.py#L236-L246
[airflow-dagrun-timeout]: https://github.com/apache/airflow/blob/3.4.0/airflow-core/src/airflow/jobs/scheduler_job_runner.py#L3308-L3328
[airflow-skip-meanings]: https://github.com/apache/airflow/blob/3.4.0/airflow-core/docs/core-concepts/tasks.rst#L81

<!-- CPython, Trio and AnyIO -->

[aio-done]: https://github.com/python/cpython/blob/v3.14.10/Doc/library/asyncio-task.rst#L1292-L1293
[aio-cancelled-def]: https://github.com/python/cpython/blob/v3.14.10/Doc/library/asyncio-task.rst#L1485-L1489
[cf-states]: https://github.com/python/cpython/blob/v3.14.10/Lib/concurrent/futures/_base.py#L18-L33
[anyio-status]: https://github.com/agronholm/anyio/blob/4.16.0/src/anyio/_core/_tasks.py#L261-L285
[aio-taskgroup]: https://github.com/python/cpython/blob/v3.11.0/Doc/library/asyncio-task.rst#L340-L347
[trio-nursery]: https://github.com/python-trio/trio/blob/v0.35.0/docs/source/reference-core.rst#L658-L660
[anyio-taskgroup]: https://github.com/agronholm/anyio/blob/4.16.0/docs/tasks.rst#L17-L19
[aio-gather]: https://github.com/python/cpython/blob/v3.14.10/Doc/library/asyncio-task.rst#L548-L551
[aio-group-raise]: https://github.com/python/cpython/blob/v3.14.10/Doc/library/asyncio-task.rst#L394-L399
[aio-return-exceptions]: https://github.com/python/cpython/blob/v3.14.10/Doc/library/asyncio-task.rst#L553-L554
[trio-strict-why]: https://github.com/python-trio/trio/blob/v0.35.0/docs/source/reference-core.rst#L884-L893
[trio-did-not-happen]: https://github.com/python-trio/trio/blob/v0.35.0/docs/source/reference-core.rst#L487-L489
[aio-cancel-inject]: https://github.com/python/cpython/blob/v3.14.10/Doc/library/asyncio-task.rst#L318-L319
[cf-cancel]: https://github.com/python/cpython/blob/v3.14.10/Doc/library/concurrent.futures.rst#L527-L530
[cf-shutdown]: https://github.com/python/cpython/blob/v3.14.10/Doc/library/concurrent.futures.rst#L96-L107
[trio-thread]: https://github.com/python-trio/trio/blob/v0.35.0/src/trio/_threads.py#L303-L316
[trio-cancel-source]: https://github.com/python-trio/trio/blob/v0.35.0/src/trio/_core/_run.py#L1262-L1269
[aio-taskgroup-abort]: https://github.com/python/cpython/blob/v3.14.10/Lib/asyncio/taskgroups.py#L221-L226
[aio-timeout]: https://github.com/python/cpython/blob/v3.14.10/Doc/library/asyncio-task.rst#L754-L757
