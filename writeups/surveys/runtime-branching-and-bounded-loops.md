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

# Survey: runtime branching and bounded loops — do they fit Hamilton, or stay with Apache Burr?

A survey of the Hamilton 2.0 effort, written 2026-11-17. It builds nothing. The owner's decisions go in decision record [2611-18](../adr/2611-18-runtime-branching-and-bounded-loops.md), which stays Proposed until the owner decides.

## Summary

**Runtime branching fits Hamilton.** It needs no cycles. Four of the six systems compared (Airflow, Dagster, Flyte, TensorFlow) branch inside an acyclic graph. Hamilton computes only what the requested outputs need, so a branch fits it as "alternative implementations of one node, chosen by a value computed in the run". The node with the alternatives is then the join, and it always has exactly one value.

The systems that instead let a skip flow downstream and then ask every join to state a rule all document traps at the join:

- In Airflow, the default rule skips a join that follows a branch, and its own docs say "You almost never want to use all_success or all_failed downstream of a branching operation".
- In LangGraph, a join whose predecessor was not selected "never runs and no error is raised".
- In Dagster, unexpected skips recur in its changelog.

**Recommendation for branching: agree the semantics now, defer the feature.** Agree on the semantics in this report now (section 6), but do not add the feature to the first 2.0 release. Keep the `skipped` outcome that Ticket 06 reserves, and let the coordinator of Ticket 07 settle a task without running it. Demand is thin: one user question in the issue tracker (#1290). The plan for this effort also leaves runtime branching out.

**Bounded loops are a closer call than the README suggests.** Airflow 3.4.0, released 2026-11-06, added the exact shape the outline describes: a loop over a subgraph whose outer graph stays acyclic. It has a required `max_iterations`, one carried value, and a gate that fails when the bound is reached without the stop condition. Burr, where the README sends users for loops, has cycles but no built-in bound: it only warns "this has the possibility of running forever!". It also has no step caching.

**Verdict on loops: the structured bounded form fits Hamilton in principle, and arbitrary cycles stay with Burr.** Airflow 3.4.0 shows the structured shape working inside an acyclic graph. It is unproven against Hamilton's way of writing functions, because a value carried from one iteration to the next has no parameter name that can stand for it (section 7).

**Recommendation for loops: defer, decline arbitrary cycles.** Defer bounded loops to the separate proof the outline already assigns them to, and do not add them to the first 2.0 release. Decline arbitrary cycles outright, and leave them with Burr. I found no Hamilton user asking for loops. An iterative algorithm in a Hamilton node is a Python loop inside one function today.

**Ticket 07 should reserve one thing for loops.** Task identity should be a typed instance path, a sequence of elements that each name their kind. A loop iteration or a nested map item can then be added later without changing what an index means. Airflow's own code warns that its shared column "cannot tell an iteration from a map index".

**The composition path the README points to breaks at 2.0.** Burr's `Hamilton` action calls `Driver.raw_execute`, which Hamilton schedules to fail at 2.0.0. Section 12 lists nine decisions for the owner, each with a recommendation.

## 1. The question

For runtime branching and for bounded loops, the question is whether Hamilton should adopt the feature, defer it or decline it, and under which semantics if it is adopted.

Runtime branching means that a value computed during a run decides which part of the graph executes. A bounded loop means that a subgraph repeats a limited number of times.

The counter-hypothesis to adopting either feature is the position in Hamilton's README [H1]: "Apache Hamilton is great for DAGs, but if you need loops or conditional logic to create an LLM agent or a simulation, take a look at our sister library Burr". On that view the two libraries are split on purpose. A second way to branch or loop inside Hamilton would blur that split and give every user a harder model. Section 8 weighs that position as grounds both for and against.

The question came from a maintainer on the outline [H11]: "Could we have conditional path execution? hard to do with DFS, but could be done with BFS" and "could we define a loop path syntax with the function signature?", with the caveat "These would both require some API UX iteration and thinking before deciding they're worthwhile." The outline answers that "Traversal order alone neither creates nor prevents conditional execution", and that "Branch and loop syntax should follow concrete examples and agreed semantics. Neither feature is an automatic 2.0 commitment". Its stage table puts "runtime branching, bounded loops, nested mapping" under "Separate proofs".

## 2. Terms

These terms are used with one meaning for every system. Where a system uses the same word for something else, the comparison says so.

- **Build-time selection.** Choosing which functions become nodes before a run starts, from configuration. Hamilton's `@config.when`, `step(...).when(...)` and `@resolve` do this.
- **Request-time selection.** Choosing which outputs to compute when calling the Driver. Hamilton's `final_vars` does this; only nodes upstream of the requested outputs run.
- **Mapping.** Running a block of nodes once per item of a collection produced in the run, then collecting the results. Hamilton's `Parallelizable` and `Collect` do this.
- **Runtime branch decision.** A choice among paths of the graph made from a value computed during the run.
- **Decision input.** The value the decision is made from.
- **Alternative.** One of the paths a decision chooses among.
- **Selected or unselected.** An alternative is selected when the decision chose it, and unselected otherwise.
- **Unselected branch.** The nodes that a run does not execute because they lie only on unselected alternatives. Section 6 defines "only on" for Hamilton.
- **Skipped.** The outcome of a task the run deliberately did not execute because a runtime branch decision did not select its path. This is the meaning agreed with Ticket 06's survey, which owns the outcome vocabulary: [`writeups/surveys/failure-policy.md`](failure-policy.md) and its proposed record 2611-15, decision 11, both in review in SummitSG-LLC/hamilton pull request #9.
  - Skipped is not a failure, so it never produces blocked.
  - In Ticket 06's vocabulary, **blocked** is a task not executed because a prerequisite ended failed or blocked; it arises only in a best-effort mode.
  - **Cancelled** is a task the run stopped before it finished, whether it had started or not.
- **Join.** A node that receives values from more than one alternative of a decision, or from an alternative and from outside the branch.
- **Requested output on an unselected path.** An output the caller asked for that lies on an unselected alternative.
- **Bounded loop.** A body, which is a subgraph, executed repeatedly inside one run, with a hard maximum number of iterations.
- **Carried state.** The values one iteration passes to the next.
- **Termination.** The rule that ends a loop: a stop condition, the bound, or both.
- **Iteration identity.** What distinguishes two executions of the same body node in different iterations, in run state, events, caches and persistence.
- **Cycle.** An edge path from a node back to itself in the graph as declared. A bounded loop as defined here does not need one; Airflow and TensorFlow keep the declared graph acyclic.

## 3. Method and sources

### Systems compared, and why each is comparable

Each system received the same eleven questions:

1. the model;
2. the branching mechanism;
3. the unselected branch;
4. the skipped state;
5. the join;
6. a requested output on an unselected path;
7. loops;
8. iteration identity;
9. cancellation;
10. caching and tracking;
11. the limits the project itself documents.

The six systems fall into three groups by what they share with Hamilton.

| System | Version | Why it is comparable | What is not comparable |
| --- | --- | --- | --- |
| Apache Burr | 0.43.0, tag `v0.43.0-incubating` | The sister library the README sends users to. Python functions run in one process. | A state machine with explicit state. Runs one action per step. Requests actions, not values. |
| LangGraph | 1.2.22, tag `1.2.22` | The most widely used in-process graph of Python functions with routing and cycles. | Bulk-synchronous steps over state channels. Returns state keys, not node outputs. |
| Apache Airflow | 3.4.0, tag `3.4.0` | A static DAG declared in Python. Its TaskFlow API wires values by function argument. It has the most worked-out skip and join rules, and a new structured loop. | Its nodes are separately scheduled tasks, usually processes or pods. Values cross process boundaries. Skip is a persisted scheduler state. |
| Dagster | 1.13.30, tag `1.13.30` | Functions whose inputs are wired by name. Assets wire by parameter name, as Hamilton does. It has an in-process executor. Skip follows from which values exist. | Steps run in their own process by default. Values pass through I/O managers. Every step is recorded in an event log. |
| Flyte | flytekit 1.16.32 and backend 1.16.9 | A typed DAG built by running Python once, then compiled. The branch is a node in that DAG. | Wiring by promise, not by parameter name. Nodes are containers or pods. A Kubernetes controller runs the graph. |
| TensorFlow | 2.21.0, tag `v2.21.0` | A typed dataflow graph traced from Python and run in one process. It has structured branch and loop operations, and a documented older design built on dead-value propagation. | Nodes are tensor kernels, not user functions. Gradients consume intermediates. |

JAX 0.12.0.1 appears only as a short note that corroborates TensorFlow's structured operations. It is not a compared system and did not receive the eleven questions.

**Why these systems.** I wanted at least two systems close to Hamilton on each axis that matters:

- **Node granularity** (a function call in one process): Burr, LangGraph and TensorFlow.
- **Graph model** (a static DAG of named, typed values): Dagster, Flyte and Airflow's TaskFlow API.
- **Home of the feature**: Burr, because the question is whether the features stay there.

**Systems not surveyed:**

- Prefect, Metaflow, Kedro and Temporal.
- Flyte 2, whose backend is a separate tree from the 1.x backend that runs flytekit 1.16 branch nodes.

Kedro has no runtime branching to my knowledge. Prefect relies on plain Python control flow outside a static graph; that model is represented here by Flyte's eager workflows and LangGraph's functional API.

### How the sources were checked

The sources are each project's code and in-repository docs at the release tag above. I cloned each repository shallowly and read and grepped it without running it. Appendix A lists the references; the text cites them by key. Each key claim carries a permalink to a tag with line numbers, and a short quotation.

The report rests on these claims, and I opened and read each against the tagged source myself:

- **Airflow:**
  - the Task Loops release note, `loop()` signature, acyclic statement, gate semantics and limits [A7];
  - the join pitfall and the fix rule [A5];
  - skipped counted as success [A4];
  - mark-failed setting pending tasks to skipped [A9];
  - the `region_index` comment [A8];
  - the XCom `None` for a skipped upstream [A6].
- **Dagster:** the conditional-execution docs [G1] and the skip rule with the fan-in exception [G2].
- **Flyte:** `else` is mandatory [F3]; void output [F6]; the output intersection [F6]; skipped phase [F4]; skip propagation that includes failure [F5]; one node per branch [F7]; eager workflows' stated cost [F9]; primitive predicates [F10]; the documented recursion limit [F8].
- **TensorFlow:** the `cond` output rules and the "executed regardless" warning [T1]; the illegal-use note [T3]; `maximum_iterations` [T6]; the carried-structure rule [T6]; lowering [T9]; the Merge rule [T5]; the AutoGraph one-branch rule [T11].
- **JAX:** `cond`'s `vmap` note [J1] and `while_loop` [J2].
- **Burr:** the origin sentence [B10]; the run-forever warning [B5]; transition selection [B2]; the UI status type [B6]; the ecosystem entry [B12]; the `raw_execute` call [B11]; halting caveats [B4]; parallelism caveats [B9].
- **LangGraph:** the default recursion limit and its docs [L8]; the list-join docs [L6]; reads of unwritten keys [L7].
- **Hamilton:** issues #1290 and #1016.

Three research helpers gathered the evidence, one per pair of systems. Each recorded at least two search formulations per question; Appendix B summarizes them. Each helper's report was read in full by me, the single author of the comparison and proposal.

These sources are weaker, and the claims that rest on them are marked where used:

- LangGraph's conceptual docs live outside the code repository, in `langchain-ai/docs`. That site is unversioned. I cite them pinned to docs commit `3def9fa8` of 2026-11-17, which is not a release snapshot of 1.2.22.
- Two Dagster claims are inferred from code, and no test asserts either:
  - a `Nothing` input from a skipped upstream also skips;
  - an `In(default_value=...)` does not rescue a connected skipped input.
- Flyte documents a recursion-depth limit for dynamic workflows. The helper found no code that enforces it.
- Dagster+ is closed source, so where it emits `AssetMaterializationFailureType.SKIPPED` was not checked.
- TensorFlow's dead-tensor semantics come from code comments and from the authors' EuroSys 2018 paper [T12]. The paper describes the v1 design. Nothing was executed.
- Burr's README comparison table is the project's own assessment of itself and of LangGraph. I do not use it as neutral evidence.

## 4. Hamilton today (1.90.0)

### How execution chooses work

The Driver first selects the nodes upstream of the requested outputs (`get_upstream_nodes`, [H3]). All three 1.x execution paths then call nodes through one recursive depth-first function, `execute_subdag` [H2]. Execution is therefore demand-driven: a node runs only because a requested output needs it.

No node chooses at run time which of its dependencies to need. Every dependency named by a parameter is computed before the node is called. The one exception is an external input that has a default value (`DependencyType.OPTIONAL`, [H4]): if the caller does not pass it, the parameter keeps its default. A node that some function produces is always computed if anything requested needs it, even when the consuming parameter has a default.

### What the existing features cover

| Feature | When it chooses | What it can and cannot do for a value computed in the run |
| --- | --- | --- |
| `@config.when` [H5] | Graph build, from config | Picks one implementation of a node. The choice must be known before the run. A run-time choice is possible only in two phases: compute the decision input, then build a second Driver with it in config. |
| `step(...).when(...)` in `@pipe_input` and `@pipe_output` [H6] | Graph build, from config | Same as `@config.when`, for one step of a pipe. |
| `@resolve` [H7] | Graph build, from config, in power-user mode | Shapes decorators from config. It cannot use a value computed in the run. |
| `final_vars` | Call time | Picks which outputs to compute. The caller must already know which path is wanted. |
| Optional parameter with a default [H4] | Call time, external inputs only | Absorbs a missing external input. It does not skip a node another function produces. |
| `Parallelizable` and `Collect` [H8] | Run time | Maps a block over items produced in the run. Yielding zero or one item emulates "run this path or not" (measured below). The docs limit it to one level of mapping, one `Collect` input per function, and one collect downstream of a mapping. |

### Measured: emulating a branch with today's mapping

I ran the module in Appendix C on Hamilton 1.90.0, at commit `31b3a832` of `2.0`, on CPython 3.15.0, with dynamic execution and the synchronous local task executor. `needs_conversion` yields the currency only when it is not USD, so the block `fx_rate` → `converted` runs once or not at all, and `rate_or_nothing` collects 0 or 1 values:

```text
hamilton (1, 90, 0) python 3.15.0
USD request amounts_usd -> [10.0, 5.0] calls: ['transactions', 'currency', 'needs_conversion', 'rate_or_nothing', 'amounts_usd']
EUR request amounts_usd -> [11.0, 5.5] calls: ['transactions', 'currency', 'needs_conversion', "fx_rate('EUR')", 'converted', 'rate_or_nothing', 'amounts_usd']
EUR request fx_rate -> raised TypeError cannot use 'list' as a dict key (unhashable type: 'list') calls: ['transactions', 'currency', 'needs_conversion', "fx_rate(['EUR'])"]
USD request fx_rate -> raised TypeError cannot use 'list' as a dict key (unhashable type: 'list') calls: ['transactions', 'currency', 'needs_conversion', 'fx_rate([])']
```

**When the request is downstream of the collect, the emulation works.** For USD, `fx_rate` is never called.

**When `fx_rate` itself is requested, it gets the wrong input.** The node declared `needs_conversion: str` and is called once with the whole yielded list: `['EUR']`, or `[]` for USD. So today's closest approximation to "a requested output on an unselected path" gives neither a skip nor a clear error. It gives a call with the wrong type. This is recorded as debt for a 1.x fix and is not pursued here.

The emulation also costs a mapping concept, the dynamic-execution builder flag, and a collect node with an `if` in user code.

### Measured: a loop unrolled into a chain

A bounded loop with a known count can be unrolled into a chain of nodes today, with `@parameterize` or `@subdag`. On the 1.x default path a chain of generated `x_i = x_{i-1} + 1` nodes (Appendix C) gave these results with the default recursion limit of 1000:

| Python | Ran | Raised `RecursionError` |
| --- | --- | --- |
| 3.11.15 | 950 nodes | 990 nodes |
| 3.15.0 | 990 nodes | 1,000 nodes |

The effort's notes record a failure at 1,500 nodes; my threshold is lower on both builds. This is a limit of the recursive `execute_subdag`, not of unrolling. The new runtime's coordinator, which releases work when its prerequisites are done, has no such recursion.

Hamilton also lets a graph contain a cycle. Issue #1016 asked to detect cycles at build time and was closed as "intended behavior": "There are. afew people that will use a DG (no A :) ) with cycles and override intermediate nodes" [H10]. This is not a loop feature; nothing repeats.

### Demand

A read-only search of apache/hamilton issues and discussions found one direct request for runtime branching. Issue #1290, "Question about Dynamic Task Branching in Hamilton" (2025-03), asked to choose `func1` or `func2` from a function's return value. The maintainer answered [H9]: "Hamilton does not currently support dynamic branching based on the output value of a function in the DAG. *Why?* No one has strongly asked for this (and we'd need to figure out an API that fits with hamilton)." The suggested workarounds were to run all paths with `GracefulErrorAdapter`, or to run Hamilton within Hamilton with config.

I found no request for loops. The outline's own questions come from a maintainer, not from users.

## 5. How the systems compare

### Each system in brief

**Apache Burr 0.43.0.**

- *Model.* Applications are "actions (functions that write to/read from state), and transitions (functions that determine the next action to execute based on state)" [B1]. One action runs per step, and state is explicit and immutable.
- *Branching.*
  - Transitions carry conditions (`when`, `expr`, `default`). "the first one that evaluates to True will be the transition that is selected … If no condition evaluates to `True`, the application execution will stop early" [B2].
  - Unselected actions are simply never visited. There is no skipped status: the UI's status type is `'success' | 'failure' | 'running'` [B6]. The UI shows the unselected path by absence, highlighting executed nodes on the static graph.
  - There is no join construct. A field that another path never wrote is absent from state, and reading it raises `KeyError` [B8]. A value written by an earlier path or iteration stays visible; that is an inference from the merge rule.
  - The caller requests actions to halt at, not values. If the graph dead-ends before a requested halt, Burr returns the last action run and logs that "this is considered undefined behavior -- if you get here, you should fix!" [B14]. The docs call halting without reaching a halt condition "not a supported feature" [B4].
- *Loops.*
  - Cycles are the canonical example [B4], and the carried state is the whole application state.
  - There is no iteration bound. The only guard is a warning: "No halt termination specified -- this has the possibility of running forever!" [B5]. A bounded retry edge (`error(..., max=3)`) appears only as a planned idea [B13].
  - Iteration identity is `sequence_id`, a per-application step counter incremented before every step. With `partition_key` and `app_id` it keys persistence [B7]. There is no per-action iteration counter.
  - There is no cancellation API, and no step-result caching. The parallelism module notes its child key "will not handle caching" [B9].
  - Parallel fan-out and fan-in run sub-applications inside one action, a feature "in an experimental release phase" [B9].
- *Relation to Hamilton.*
  - Burr's README says it "was built as a _harness_ to handle state between executions of Apache Hamilton DAGs (because DAGs don't have cycles)" [B10].
  - Burr ships a `Hamilton` action that runs a Hamilton graph as one Burr action [B11, B12]. It calls `Driver.raw_execute`, `list_available_variables`, `is_external_input` and `visualize_execution`, and installs Hamilton through the `sf-hamilton` extra [B11].
  - The outline's June statements about Burr hold at 0.43.0:
    - cycles with unknown termination: confirmed;
    - conditional execution: confirmed;
    - "represents parallel subdags internally": partly, since they are sub-applications under one parallel action;
    - "no caching but has result persistence": partly, since the persister stores per-step state and the tracker records action results.

**LangGraph 1.2.22.**

- *Model.* Execution follows the "Pregel Algorithm/Bulk Synchronous Parallel model" over state channels [L1].
- *Branching.*
  - `add_conditional_edges`, `Command(goto=...)` and `Send` route at run time [L2, L3].
  - Unselected nodes get no task and leave no record [L4]. There is no skipped status; run status values include `"out_of_steps"` but nothing per node [L5].
  - A join written as `add_edge([a, b], c)` waits for all sources. The docs warn: "If one of them never runs (for example, a conditional edge does not select its branch), `d` never runs and no error is raised" [L6].
  - Separate edges run the join once per step in which any source finishes. `defer=True` waits until "no tasks are pending anywhere in the graph" [L6].
  - Callers request state keys, not node outputs. A key never written is omitted from a list request and returned as `None` for a single-key request [L7].
- *Loops.*
  - Cycles are allowed. "A loop needs a way to stop. The usual pattern is a conditional edge that routes to END" [L12].
  - A step limit is always on, and its default is 10,007 supersteps ("Starting in version 1.1.4, the default is 10,007 super-steps", [L8]). Exceeding it raises `GraphRecursionError`. The limit counts supersteps, not visits to a node.
  - Identity is the superstep number plus a task id hashed from checkpoint id, namespace, step, node and triggers [L9].
  - Cancellation is a cooperative drain at a superstep boundary [L10]. Node results can be cached by input when the user opts in [L11].

**Apache Airflow 3.4.0.**

- *Model.* "A workflow is represented as a Dag (a Directed Acyclic Graph)" [A1]. Cycles raise `AirflowDagCycleException` [A10].
- *Branching.*
  - `@task.branch` returns the task ids to follow; "all other paths are skipped" [A2]. The branch writes `skipped` only on its direct children, and the default trigger rule `all_success` then cascades the skip [A3].
  - `skipped` is "The task was skipped due to branching, LatestOnly, or similar, or was marked as skipped manually" [A4]. It is counted with success in `success_states`, so a run whose leaves are skipped succeeds [A4, A6].
  - The word is overloaded: marking a run failed sets "non-finished ones to SKIPPED", and so does a run timeout [A9]. In Airflow, skipped therefore also covers what this report calls cancelled.
  - Joins are governed by thirteen trigger rules [A5]. The docs warn "*You almost never want to use all_success or all_failed downstream of a branching operation*" and fix the documented example with `none_failed_min_one_success` [A5].
  - A docs-against-code disagreement stays open: `all_done_min_one_success` is documented as "All non-skipped upstream tasks are done…", yet the code skips the task if any upstream skipped [A11].
  - A consumer whose upstream was skipped, if its trigger rule lets it run, receives `None` for the upstream's return value. It cannot tell this from a real `None` [A6].
- *Loops.*
  - Task Loops (AIP-111) are new in 3.4.0. "a decorated task group can be repeated a number of times decided at runtime using `.loop()`. A conditional loop works like a `do ... while` loop … bounded by `max_iterations`" [A7].
  - The declared graph stays acyclic: "there is no dependency loop introduced, the tasks in the Dag still do form a cycle-free graph. The looping nature is handled at runtime only" [A7].
  - `max_iterations` is a required, positive argument. A gate task evaluates `until`. "Reaching `max_iterations` while the condition remains `False` means the loop did not converge: the gate task in the final iteration is marked as failed" [A7].
  - The carried state is one value: the body's single terminal task's return value becomes `loop.previous` for the next iteration [A7].
  - Identity: iterations are `loop.index` from 1, mapped instances `map_index` from 0, retries `try_number`; "A retry stays in the same iteration and does not consume another iteration" [A7].
  - In the database both iteration and map slot share one column, `region_index`. Its code comment says "Code that reads the column without knowing which node the region executes cannot tell an iteration from a map index" [A8].
  - "Mapping a whole loop, nesting loops, and placing a loop inside a mapped task group are not supported" [A7].
  - Two weaknesses stay open. The feature is eleven days old and its release notes already list loop fixes. The loops page also says the last iteration is `loop.index == loop.max_iterations - 1`, which disagrees with its own 1-based numbering [A7].

**Dagster 1.13.30.**

- *Model.* Ops and assets form a static graph, with an execution plan of steps. The default executor runs each step in its own process and can run them in one [G10].
- *Branching.*
  - Conditional execution uses optional outputs. "As an op only starts to execute once all its inputs have been resolved, you can use this behavior to model conditional execution … Since op execution is skipped for ops that have unresolved inputs, only one of the downstream ops will execute" [G1].
  - A step is skipped if any input's source is missing. For a fan-in input it is skipped only if all sources are missing [G2]. There is no trigger-rule equivalent; the shape of the input decides.
  - Skipped is a step event, `STEP_SKIPPED`. A run has no skipped status, and a run whose requested asset was skipped is `SUCCESS` with no error [G3, G4].
  - Returning `None` instead of not yielding does not skip. It passes `None` downstream with a warning: "For conditional execution, results must be yielded" [G8].
  - The changelog shows unexpected skips as a recurring bug class, including blocking checks that "could silently cause downstream assets to be skipped". Since 1.5.11, a skip takes precedence over abandoning a step after an upstream failure [G9].
- *Loops.* Cycles are rejected at definition time [G5]. There is no loop construct; `DynamicOut` with `.map` and `.collect` is fan-out, not repetition [G6]. Identity is the step key with a mapping key, plus `retry_number` and `run_id` [G7].

**Flyte (flytekit 1.16.32, backend 1.16.9).**

- *Model.* "the function body of a workflow is evaluated at serialization-time (aka compile-time)" [F1]. The compiler rejects cycles [F11].
- *Branching.*
  - `conditional(...).if_(...).then(...).else_()` compiles to one branch node, and an `else` is mandatory ("Dangling If is not allowed", [F3]). Each case is exactly one node, so a multi-step case must be a subworkflow [F7].
  - Predicates are comparisons "applicable only to primitive values" [F10].
  - The unselected case is not executed and is marked `Skipped` ("Branch evaluated to false", [F4]).
  - `SKIPPED` is a node phase that counts as success, and it propagates to dependents. The same rule also marks a node `Skipped` when an upstream node `Failed` or `TimedOut` [F5]. In Flyte, skipped therefore also covers what this report calls blocked.
  - The join is the branch node itself. Its outputs are the intersection of the names all cases produce, type-checked on shared names [F6]. A name produced by only one case does not exist downstream.
  - The IDL comment says branches "need to conform to the same interface", and the compiler instead takes the intersection; this disagreement stays open.
  - "One node returns a void output and no error, we will default to None return": one case with no output voids the whole conditional [F6].
- *Loops.*
  - There is no loop node. Repetition uses `@dynamic` workflows, compiled and run at run time; the docs show recursion this way and say "Flyte imposes limitations on the depth of recursion" [F8]. No enforcing code was found, so that claim is weak.
  - Eager workflows give Python control flow at the cost of "compile-time analysis and first-class data lineage tracking" [F9].
  - Cache keys hold no position in the graph [F12].

**TensorFlow 2.21.0.**

- *Model.* A dataflow graph traced from Python once and run in one process.
- *Branching.*
  - `tf.cond` emits one `If` operation whose branches are functions [T4]. Only one branch's operations run [T2].
  - "Any Tensors or Operations created outside of `true_fn` and `false_fn` will be executed regardless of which branch is selected at runtime … it has frequently surprised users who expected a lazier semantics" [T1].
  - Both branches "must have the same non-zero number and type of outputs" [T1], and a branch returning `None` is an error [T11].
  - "It is illegal to "directly" use tensors created inside a cond branch outside it … return it as an output of the branch function" [T3]. AutoGraph "forbids variables to be defined in only one branch of a TensorFlow conditional, if the variable is used afterwards" [T11].
  - Fetching a dead value in a v1 session is an error, not `None` [T13].
  - In the v1 design, an untaken branch receives a dead tensor; dead inputs skip the kernel; and a merge "is ready if all control inputs have arrived and either a) a live data input becomes available or b) all data inputs are dead" [T5, T12]. Deadness is a per-value bit, not a recorded skipped state.
- *Loops.*
  - `tf.while_loop` carries `loop_vars`. The body returns values "of the same arity (length and structure) and types as `loop_vars`" [T6].
  - `maximum_iterations` is "Optional" and AND-ed with the condition [T6], and the functional `While` operation has no bound attribute [T7]. The bound becomes required only when gradients meet XLA [T10].
  - v1 identity is a frame per loop and an iteration number per frame [T8].
- *Counter-evidence for "one operation stays simple".* The default runtime lowers `If` and `While` back into "Switch, Merge, Enter, Exit, NextIteration" to keep non-strict evaluation [T9]. The single operation exists at the API and graph level, while the main executor still carries frames, iterations and dead values.

**JAX 0.12.0.1 (corroboration only).** `lax.cond` runs one branch, "However, when transformed with `vmap` … `cond` is converted to `jax.lax.select`. Both branches will be traced in all cases" [J1]. `while_loop` is "lowered to a single WhileOp", its carry "must hold a fixed shape and dtype across all iterations", and it "is not reverse-mode differentiable" [J2].

### Side by side

The cells use this report's terms.

| Question | Burr | LangGraph | Airflow | Dagster | Flyte | TensorFlow |
| --- | --- | --- | --- | --- | --- | --- |
| Graph known before the run | Yes (actions and transitions) | Node set yes; routing no | Yes (loop iterations and map slots created at run time) | Yes (dynamic outputs cloned at run time) | Yes (compiled) | Yes (traced) |
| Cycles in the declared graph | Allowed | Allowed | Rejected | Rejected | Rejected | v1 yes; v2 no (lowered back to cycles at run time) |
| Branch mechanism | Conditional transition | Conditional edge, `Command`, `Send` | Branch task names children | Optional output not yielded | Branch node with cases | `If` operation with branch functions |
| Unselected branch | Never visited | Never visited | Direct children marked skipped; cascade by trigger rule | Steps with a missing input skipped | Cases not taken marked skipped | Not run (dead values in v1) |
| Skipped recorded | No status | No status | `skipped`, a success state; also used for cancelled | `STEP_SKIPPED` event; no run status | `SKIPPED` phase, a success; also used for blocked | Per-value bit, not recorded |
| Join | None; shared state | Barrier (never runs if a source is unselected), or per-step, or `defer` | Thirteen trigger rules, chosen per node | Any input missing skips; fan-in needs all missing | The branch node; output intersection | The `If` operation; same structure and types required |
| Requested output on an unselected path | Halt not reached: last action returned, warning | Key omitted, or `None` | `None` via XCom, or skipped consumer | Run succeeds, nothing materialized | Name not in interface, so not requestable | Illegal to use; dead fetch is an error |
| Loop construct | Cycle | Cycle | `.loop()` over a task group (3.4.0) | None | None (`@dynamic`, `@eager`) | `while_loop`, `While` |
| Bound | None (warning) | Always on; 10,007 supersteps by default | `max_iterations` required | — | Documented, not found in code | Optional |
| At the bound | Runs on | `GraphRecursionError` | Gate fails | — | — | Loop stops |
| Carried state | Whole application state | State channels | One value (`loop.previous`) | — | — | `loop_vars`, fixed structure |
| Iteration identity | `sequence_id` per step | Superstep and task-id hash | `loop.index`; `region_index` shared with map index | — | — | Frame and iteration number |
| Cancellation | No API | Cooperative drain at a step boundary | Mark failed sets pending tasks to skipped | `CANCELING`, `CANCELED` run status | Abort recurses into the taken case | Not surveyed |
| Step caching | None | Opt-in, by input | None | Data versions per asset | By task signature and inputs | Per traced function |

### What the comparison shows

1. **Branching does not need cycles.** Every acyclic system here branches. Cycles appear only where loops are expressed as edges (Burr, LangGraph) or in TensorFlow's lowered executor form.
2. **Joins are where branching costs users, and the costs follow the design.** There are two designs:
   - *Skips flow downstream and each join states a rule.* This is Airflow, Dagster, LangGraph, Flyte's propagation, and TensorFlow v1 `Merge`. Each of these systems documents a trap: Airflow's default rule skips the join [A5]; LangGraph's barrier silently never runs [L6]; Dagster ships recurring skip bugs [G9]; Airflow and LangGraph hand `None` to a consumer that cannot tell it from a value [A6, L7].
   - *The branch is one structured operation that is itself the join.* This is Flyte's branch node and TensorFlow's `If`. The join always has a value and the types are checked at build time. The price is a rule about values made inside a branch: Flyte drops them from the interface [F6], and TensorFlow makes using them illegal [T3, T11].
3. **Systems that record "skipped" overload the word, and those that do not leave the operator to infer it.**
   - Airflow's `skipped` covers cancellation [A9], and Flyte's covers upstream failure [F5]. Both count it as success.
   - Burr and LangGraph record nothing, and the operator infers the unselected path from absence.
   - Ticket 06's vocabulary keeps skipped, blocked and cancelled apart, which neither group does.
4. **Loops come in three shapes, which differ in bound and in identity:**
   - *Cycles with a step budget* (Burr: no bound; LangGraph: 10,007 supersteps). Termination is the user's routing.
   - *A structured loop in an acyclic graph* (Airflow 3.4.0, TensorFlow and JAX `while_loop`). One declared operation, a body, explicit carried state. The bound is required in Airflow and optional in TensorFlow; reaching it fails in Airflow and stops quietly in TensorFlow.
   - *No loop, with repetition built from a graph compiled at run time or by leaving the graph* (Flyte's `@dynamic` and `@eager`, Dagster).
5. **Iteration identity is retrofitted, and the retrofit leaks.** Airflow shares one column between iteration number and map index, and warns against it in its own code [A8]. TensorFlow v1 needs frames and iteration tags inside its executor [T8]. A runtime that names each part of an instance's identity from the start avoids both.

## 6. Branching, worked through a Hamilton example

### Two rules for "on the unselected path"

Hamilton runs what the requested outputs need. That gives two possible rules for which nodes a branch controls, and the rule decides whether a requested output can lie on an unselected path at all.

- **By demand (proposed).** A node in the plan is skipped when every consumer that would need it is skipped or has been resolved to an alternative that does not use it. Requested outputs count as consumers that always need their node.
  - Under this rule a requested output is never on an unselected path. Requesting a node makes it needed, so it runs.
  - The plan knows before the run which nodes depend on which decision for this request, so renderers and the catalog can show it.
- **By declaration (alternative).** Each alternative declares the nodes that belong to it, as TensorFlow's branch functions and Flyte's single-node cases do.
  - A declared node runs only when its alternative is selected, even if a request names it. A request for a declared node on an unselected alternative then ends with an error that names the decision and its value.
  - This rule can guard a node that must not run on the wrong path. It costs a second declaration for every member node.

### The example

The example is a batch of transactions. Converting it to USD needs a network call for the exchange rate, which is pointless when the batch is already in USD. The decorator name `select_on` is illustrative only, not a proposed API. Syntax is later work, and it must not reuse `@config.when`, so that build-time and run-time selection stay distinct.

```python
def transactions(raw: list[dict]) -> list[dict]:
    return [t for t in raw if t["amount"] != 0]


def currency(transactions: list[dict]) -> str:
    return transactions[0]["currency"]


def fx_rate(currency: str, fx_client: FxClient) -> float:
    return fx_client.rate(currency, "USD")  # network call; meaningless for USD


@select_on("currency", equals="USD")  # illustrative: chosen when currency == "USD"
def amounts_usd__as_is(transactions: list[dict]) -> list[float]:
    return [t["amount"] for t in transactions]


@select_on("currency", not_equals="USD")  # illustrative: chosen otherwise
def amounts_usd__converted(transactions: list[dict], fx_rate: float) -> list[float]:
    return [t["amount"] * fx_rate for t in transactions]


def daily_report(amounts_usd: list[float]) -> dict:
    return {"total": sum(amounts_usd), "count": len(amounts_usd)}


def fx_audit(currency: str, fx_rate: float) -> dict:
    return {"currency": currency, "rate": fx_rate}
```

The decision input is `currency`. `amounts_usd` has two alternatives and is the join. `fx_rate` is needed only through `amounts_usd__converted`, unless a request needs it directly.

**Request `daily_report`, batch in USD:**

| Node | Outcome |
| --- | --- |
| `transactions` | Runs |
| `currency` | Runs; returns `"USD"` |
| `amounts_usd` | Runs `as_is` |
| `daily_report` | Runs |
| `fx_rate` | Skipped, with the decision `amounts_usd` on `currency == "USD"` as its cause |

`fx_client` is not used. The result is `{"daily_report": ...}`.

**Request `daily_report`, batch in EUR:** `fx_rate` runs after `currency` is known, then `amounts_usd` runs `converted`. Nothing is skipped.

**Request `daily_report` and `fx_audit`, batch in USD:**

- *Under the demand rule,* `fx_audit` needs `fx_rate`, so `fx_rate("USD")` runs. Whatever the function does with USD decides the outcome: a real client returns 1.0 and the run succeeds, while a lookup table without USD raises in user code. No branch rule is involved, because the request selected the node.
- *Under the declaration rule,* if `fx_rate` were declared a member of `converted`, the run would end with an error that names `amounts_usd`, `currency == "USD"` and the requested output `fx_audit`.

### Each semantic, under the proposed rule

- **Unselected branch.** The unselected alternatives of a decision, and the nodes needed only through them in this plan. In the USD run: `amounts_usd__converted` and `fx_rate`.
- **Skipped.** Each node of the unselected branch ends skipped.
  - Skipped is not failure and produces no blocked. It never flows downstream, because by construction nothing selected depends on a skipped node.
  - This is the main difference from Airflow, Dagster, Flyte and LangGraph, where a skip reaches consumers and each consumer needs a rule.
- **Join.** The node with alternatives is the join, and it always has exactly one value.
  - All alternatives must declare the same output type, checked at build time, as Flyte and TensorFlow do.
  - Downstream nodes never see a skipped input, so there are no trigger rules. Optional parameters do not absorb skips.
  - Because of that, a parameter with a default never silently means "maybe skipped". This mirrors the outline's warning that an optional argument "should not silently mean that an upstream failure is acceptable".
- **Requested output on an unselected path.** It cannot occur under the demand rule. Under the declaration rule it is an error that names the decision. It is never `None` and never an omitted key, because Airflow and LangGraph show that a missing value given as `None` cannot be told from a real `None` [A6, L7].
- **Order.** Nodes that depend on a decision are not started before it resolves. Nothing is computed speculatively.
  - TensorFlow's opposite choice runs everything outside the branch functions and "has frequently surprised users" [T1].
  - The cost is less parallelism: `fx_rate` waits for `currency`.
- **Inputs.** Required external inputs are validated before the run for every node the plan might run. So `fx_client` is required even for a USD batch. The alternative, validating when an alternative is selected, would turn a missing input into a failure in the middle of a run.
- **Failure of the decision input.** If `currency` fails, the decision never resolves. Under fail-fast, the default, remaining tasks are cancelled. In a future best-effort mode the alternatives and their exclusive upstream would be blocked, not skipped, because no decision was made.
- **Cache.** A node with alternatives takes its code version from the alternative that ran, so its cache key changes with the decision. A skipped node writes no cache entry and no data version. Unchanged upstream nodes, such as `transactions`, are reused across a USD run and a EUR run.
- **Tracking.** Observers receive a skipped outcome for each skipped node, with the decision node and the decision input's value as its cause. Renderers show the decision and its alternatives from the compiled graph without input values. Burr and LangGraph record nothing for unselected work, which leaves the operator to infer it.

### Why the existing features do not cover the example

- *`@config.when`* needs `currency` before the graph is built. That forces two Driver builds per batch, and `transactions` is computed twice unless passed as an override.
- *`final_vars`* needs the caller to know the currency first; the same two-phase pattern applies.
- *An optional parameter* `fx_rate: float | None = None` does not skip `fx_rate`, because a function produces it [H4].
- *`step(...).when(...)` and `@resolve`* choose from config at build time [H6, H7].
- *The `Parallelizable` emulation* works for `daily_report`, at the cost of a mapping concept, an experimental builder flag and a collect node. It hands a requested `fx_rate` a list instead of a string (section 4).

## 7. A bounded loop, worked through a Hamilton example

The example is k-means clustering, which repeats an assignment step and a centroid update until the centroids stop moving. The body has several nodes, and per-iteration visibility is the reason to make it a loop of nodes rather than one function. The decorator `loop` and its arguments are illustrative only.

```python
def points(path: str) -> list[Point]: ...


def initial_centroids(points: list[Point], k: int) -> list[Point]: ...


# The body: runs once per iteration.
def assignments(points: list[Point], centroids: list[Point]) -> list[int]: ...


def new_centroids(points: list[Point], assignments: list[int], k: int) -> list[Point]: ...


def shift(centroids: list[Point], new_centroids: list[Point]) -> float: ...


@loop(  # illustrative only
    body=[assignments, new_centroids, shift],
    init={"centroids": "initial_centroids"},  # iteration 1 reads initial_centroids
    carry={"centroids": "new_centroids"},  # iteration n+1 reads iteration n's new_centroids
    until=lambda shift, tol: shift < tol,
    max_iterations=100,
)
def fitted_centroids(new_centroids: list[Point]) -> list[Point]:
    return new_centroids
```

### What each loop semantic would be

- **Carried state.**
  - `centroids` is the one carried value. It needs a name the body can read that is neither an outer node nor a body node. That is a new authoring concept, because in Hamilton a parameter name is a dependency and `centroids` would otherwise have to be a node.
  - Airflow solves this with a context object (`loop.previous`, one value [A7]), and TensorFlow with positional `loop_vars` of fixed structure [T6]. A Hamilton design would need typed carried names, checked at build time to have the same type in `init` and `carry`.
  - `points`, `k` and `tol` come from the outer graph and are the same in every iteration.
- **Termination.**
  - `until` is evaluated after each iteration. `max_iterations` is required: Airflow requires it [A7], Burr's lack of one is its only termination problem [B5], and the outline asks for a "bounded loop".
  - Whether hitting the bound fails the run (Airflow) or returns the last state (TensorFlow) is a decision for a later proof.
- **Iteration identity.** `fitted_centroids`, iteration 7, `assignments`. The identity is a typed instance path whose elements name their kind (a loop iteration here, a map item elsewhere), so iteration 7 is never confused with map item 7 [A8].
- **The outer graph.** It sees one node, `fitted_centroids`, and stays acyclic. This is the outline's "An acyclic outer graph can retain a structured loop as one operation."
  - Inside, there are two designs. One coordinator task can run an inner sub-run per iteration, like Burr's parallel sub-applications [B9]. Or the coordinator can release body tasks per iteration into the outer run, like Airflow's regions [A8].
  - TensorFlow shows that a single operation at the API level can still mean frames and iterations in the executor [T9]. The choice decides how identity, events and caching look.
- **Cancellation.** A cancel request stops at the next iteration boundary, and tasks of the current iteration end cancelled in Ticket 06's sense. LangGraph's cooperative drain at a step boundary is the closest precedent [L10].
- **Cache.** Per-iteration caching keys each body task by its inputs. Because iteration n+1's input is iteration n's output, a rerun reuses the prefix of iterations whose inputs are unchanged.

### Why the existing features do or do not cover the example

- **A Python loop inside one function** covers it today with the same result: `def fitted_centroids(points, k, tol, max_iterations)` with a `while` loop.
  - It loses per-iteration nodes, events and caching.
  - In Airflow, per-iteration scheduling, retry and clear are the point of a loop, because each iteration is a separately scheduled job. In Hamilton, a function call in one process, the in-function loop gives up only observability and per-iteration caching.
- **Unrolling with `@parameterize` or `@subdag`** covers a fixed count without early exit.
  - Ten iterations of a three-node body is thirty nodes, well inside the 1.x recursion limit measured in section 4. The new coordinator has no such limit.
  - It cannot stop when `shift < tol`. Later iterations can only be made no-ops by passing a converged flag.
- **Burr** covers it with actions for the body and a transition back while `shift >= tol`.
  - Burr has no bound, only a warning [B5], so the user writes the iteration count into state and into the transition. It has no step caching [B9].
  - Burr's `Hamilton` action can run a Hamilton graph as the body [B11], but that action calls `Driver.raw_execute`, which Hamilton schedules to fail at 2.0.0 (section 8).

## 8. The README's position, weighed both ways

**As grounds for leaving the features to Burr:**

- Burr exists for this. Its README says it "was built as a _harness_ to handle state between executions of Apache Hamilton DAGs (because DAGs don't have cycles)" [B10], and it ships a `Hamilton` action [B11, B12].
- A state machine with explicit state is the right model for agents and simulations, which is the README's own scope ("to create an LLM agent or a simulation"). Hamilton's implicit, per-node state has no place for "the state after step n".
- Adding cycles to Hamilton would change what a parameter name means, every renderer and the cache. The outline says so: "Arbitrary cycles would change substantially more of Hamilton's dataflow model."
- Every concept added to the graph is paid for by every user who reads a graph, including those who never write a branch.
- Demand is thin: one branching question (#1290), answered "No one has strongly asked for this", and no loop request.

**As grounds against:**

- The README scopes Burr to agents and simulations. Skipping a currency conversion, or iterating a clustering step, is neither. These are data-pipeline control flow inside Hamilton's own domain.
- The acyclic systems branch without a state machine: Airflow, Dagster, Flyte and TensorFlow. Airflow has just added a bounded loop over a subgraph without cycles [A7]. "A DAG library does not do this" no longer describes the field.
- Burr is not a complete answer for loops in Hamilton's domain. It has no built-in bound [B5], no step caching [B9], parallelism marked experimental [B9], and halting semantics it calls undefined [B4, B14].
- The composition path that the README points to breaks at 2.0 as now planned:
  - Burr's `Hamilton` action calls `self._driver.raw_execute(...)` [B11].
  - Hamilton marks `Driver.raw_execute` with `fail_starting=(2, 0, 0)` [H12].
  - Ticket 04 of this effort makes scheduled removals take effect, and it lists `Driver.raw_execute` among them.
  - Unless Hamilton keeps a supported entry point for Burr, or Burr changes its call, "stays with Burr" is a route that fails on Hamilton 2.0.
  - The integration also installs Hamilton through the old `sf-hamilton` package name [B11].

**Where it lands.** The README's position holds for arbitrary cycles and for agent-style control flow, and I recommend declining those for Hamilton. It is weaker for runtime branching, which needs no cycles and fits Hamilton's demand-driven model, and for bounded loops in data-pipeline work. It holds only as long as the Burr composition path keeps working.

## 9. Three frames

- **The pipeline author.**
  - *Branching:* the cost is one new concept, a node with alternatives chosen at run time. It stays close to `@config.when`, which the author already knows, but the decorator must be distinct so the author can tell when the choice happens. The author gives up nothing in the join, because the join has one value and one type.
  - *Loops:* the cost is a carried-name concept that breaks "a parameter name is a node". That is a larger change to how a Hamilton function reads.
  - *Today's workarounds:* a two-phase run for branching, and a Python loop in one function for loops. Both work, and the first costs an extra build and computation.
- **The maintainer.**
  - *Branching touches:* the compiler (alternatives kept and type-checked); the plan (which nodes depend on which decision); the coordinator (settle a task as skipped); outcomes (`skipped` with a cause); the cache (code version per alternative); renderers and the catalog.
  - The rest of the runtime can stay unaware of it, because skips do not flow downstream.
  - *Loops touch everything:* the compiler (body subgraph, carried names); the coordinator (instances per iteration, or a sub-run); identity; events; the cache; renderers; cancellation.
  - Airflow's region and identity retrofit [A8] and TensorFlow's lowering [T9] show how far a loop reaches into a runtime.
  - Both features add test surface to every backend in the conformance kit of Ticket 15.
- **The operator who runs and observes a graph.**
  - Branching needs the skipped outcome with its cause in events and the UI. Without it, the operator infers the unselected path from absence, as in Burr and LangGraph.
  - The outcome must not be overloaded, as Airflow's and Flyte's are. A skip must not count as a failure, and it must also not hide one. Airflow's `all_done` leaf masking a failure is the documented trap [A11].
  - Loops need per-iteration identity in logs and in the UI, a bound that ends a runaway run, and cancellation at an iteration boundary.

## 10. Options and ranking

The criteria are these. Each is judged against the evidence above.

- **Fit** with Hamilton's authoring model, where a parameter name is a dependency.
- **User cost**: concepts added for every user.
- **Contract cost**: work and risk in the contracts of Tickets 07, 11 and 14 now.
- **Demand evidence.**
- **Reversibility**: can the choice be undone or changed later without a breaking change?
- **Overlap** with Burr.

### Runtime branching

| Option | Fit | User cost | Contract cost now | Demand | Reversible | Overlap with Burr |
| --- | --- | --- | --- | --- | --- | --- |
| A. Adopt in the first 2.0 release, with section 6's semantics | Good | One concept | High: widens the skeleton the plan scoped, before Tickets 10, 11 and 14 settle the plan, mapping and cache | Low (one issue) | Hard once released | Low (data-pipeline branching) |
| **B. Defer: agree semantics now; reserve `skipped` and settling without running; separate proof later** | Good | None now | Low | Matches the low demand | Yes | Low |
| C. Decline; document the two-phase pattern and Burr | — | None | None | — | Yes | Pushes data-pipeline users to an agent library |
| D. Adopt Airflow-style skip propagation with join rules | Poor (rule per join) | Highest | High | Low | Hard | Low |

B ranks first. It costs nothing now, keeps the decision open, and fixes the semantics so the first prototype does not invent them. A would be first if demand were stronger; the gap between A and B is demand and timing, not fit. D ranks last on the documented join traps.

### Bounded loops

| Option | Fit | User cost | Contract cost now | Demand | Reversible | Overlap with Burr |
| --- | --- | --- | --- | --- | --- | --- |
| A. Adopt a structured bounded loop in the first 2.0 release | Fair (carried names are a new concept) | One larger concept | High | None found | Hard | Partial |
| **B. Defer to the outline's separate proof; reserve only a typed instance path; Burr stays the documented route meanwhile** | Fair | None now | Low (the path is needed for nested mapping anyway) | Matches none found | Yes | Partial |
| C. Decline for 2.0 and leave loops to Burr | — | None | None | — | Yes, but signals a closed door | Full, with Burr's missing bound and cache |
| D. Allow cycles | Poor | High | Very high | None | Hard | Full |

B ranks first over C. The outline already assigns bounded loops to a separate proof, and Airflow 3.4.0 shows the structured shape is workable in an acyclic system. Declining would rest only on missing demand, and B costs only a typed instance path that nested mapping needs anyway. C ranks second. D is declined.

## 11. Proposal

1. **Branching: defer, with semantics agreed now.** Use section 6's rules: alternatives of one node chosen at run time; the demand rule for which nodes are skipped; the node with alternatives as the join; no `None` for missing values; no speculation; inputs validated up front; `skipped` with a cause. Keep runtime branching out of the first 2.0 release, as the plan already does. Reopen it as a separate proof after Tickets 10, 11 and 14 when a user brings a concrete case, or when the owner wants it.
2. **Contracts now.**
   - Ticket 07's outcome data keeps Ticket 06's `skipped` and lets it carry a cause.
   - The coordinator contract lets a task be settled as skipped without running.
   - Task identity is a typed instance path whose elements name their kind. Today the only kind is a map item; a loop iteration or a nested map level is added later without changing what an index means. Nothing named "loop" or "branch" goes into the contracts.
3. **Bounded loops: defer** to the outline's separate proof, with the shape fixed if it is ever built: one outer node, a body subgraph, typed carried names, `until`, a required `max_iterations`, and cancellation at iteration boundaries. **Arbitrary cycles: decline**, and leave them with Burr.
4. **The Burr composition path.** Before 2.0 is released, keep Burr's `Hamilton` action working, or agree a replacement call with the Burr project. Name Burr in the migration entry for `Driver.raw_execute`. Contacting the Burr project is an outward act that waits for the owner's go.
5. **The README note** stays as written for 2.0. It is accurate while Hamilton has neither feature. Revisit it if branching lands.

### The strongest counter-arguments

**Against deferring branching.** Hamilton's demand-driven model makes branching cheap and natural. The one user who asked was sent to workarounds. The mapping emulation users would reach for is defective. Deferring leaves users with a two-phase run that computes shared nodes twice.

This argument is strong. The answer is about timing, not merit. The semantics depend on the plan, cache and mapping contracts that Tickets 10, 11 and 14 have not built, and the owner scoped the first plan as a skeleton without runtime branching. This report agrees the semantics now, so that deferral costs only time.

**Against deferring loops rather than declining them.** Deferral keeps an expensive feature alive with no demand, and every later contract review must keep room for it. Burr is the honest home.

The answer is that the only room reserved is a typed instance path, which nested mapping needs anyway. Airflow's retrofit [A8] shows the cost of not reserving it.

**Against the demand rule.** A user may want a guarded node that must never run on the wrong path. Under the demand rule, requesting `fx_audit` runs `fx_rate("USD")`.

The declaration rule handles that, at the cost of a second declaration on every member node. That is why the choice is listed as a decision rather than settled here.

## 12. Decisions for the owner

The record [2611-18](../adr/2611-18-runtime-branching-and-bounded-loops.md) holds these until the owner decides.

| # | Decision | Recommendation |
| --- | --- | --- |
| 1 | Runtime branching in the first 2.0 release: adopt, defer or decline? | **Defer.** Keep it out of the first release as the plan does. Reopen as a separate proof after Tickets 10, 11 and 14. |
| 2 | If branching is built, which shape? | **Alternatives of one node chosen at run time, with the node as the join.** Do not adopt skip propagation with join rules. |
| 3 | Which nodes does a branch control? | **By demand:** a node is skipped when nothing selected or requested needs it. The alternative is by declaration, with an error for a request on an unselected path. |
| 4 | Semantics of a branch if built | **Adopt section 6:** a skipped node is not a failure and does not flow downstream; requested outputs are never `None` for missing values; no speculative execution; required inputs validated before the run; the decision recorded as the skip's cause; the cache key follows the alternative that ran. |
| 5 | What Ticket 07 reserves now | **`skipped` (from Ticket 06) with a cause, and settling a task without running it.** Nothing named branch or loop. While no policy produces `skipped`, it is documented as not yet produced, as decision 2 of record 2611-15 proposes. |
| 6 | Bounded loops: adopt, defer or decline? | **Defer** to the outline's separate proof. If built: one outer node, typed carried names, `until`, required `max_iterations`, cancellation at iteration boundaries. |
| 7 | Arbitrary cycles | **Decline;** they stay with Burr. |
| 8 | Task identity in Ticket 07 | **A typed instance path whose elements name their kind,** map item only for now. No loop field. |
| 9 | The Burr composition path at 2.0 | **Keep Burr's `Hamilton` action working.** Either keep a supported entry point for it, or agree a replacement call with Burr before release, and name Burr in the migration entry for `Driver.raw_execute`. Contacting Burr waits for your go. The README note stays as written for 2.0. |

## 13. Confidence, gaps and assumptions

**Strong evidence.** What each system does, for each question, rests on its own code and in-repository docs at the stated tag. I re-read the claims the proposal turns on (section 3).

The demand-driven execution of Hamilton 1.x, the emulation's behavior and the recursion threshold were measured, with the commands and output in Appendix C. Confidence is high that:

- branching needs no cycles;
- the systems that let skips flow downstream document traps at the join;
- Burr has no built-in bound or step caching;
- Airflow 3.4.0 has a structured bounded loop;
- Burr's `Hamilton` action calls an API Hamilton schedules to fail at 2.0.0.

**Limited evidence:**

- **Demand.** One issue, and a search that may miss requests worded differently in the older stitchfix and DAGWorks history.
- **How Hamilton users would use either feature.** No prototype exists, and the outline calls for "API UX iteration".
- **Airflow's loop.** Eleven days old; its behavior may change.
- **The cost estimates for the runtime in sections 9 and 10.** These are judgement, not measurement.

**Gaps:**

- Prefect, Metaflow, Kedro, Temporal and Flyte 2 were not surveyed.
- Cancellation in TensorFlow was not surveyed.
- LangGraph's docs are not release-pinned.
- Flyte's recursion limit and Dagster's `Nothing` and default-input behavior are documented or inferred, not shown in code or tests.
- Nested mapping, which the outline groups with loops, is covered only through the typed instance path.

**Assumptions:**

- Ticket 06's outcome terms are the ones in its report and in decision 11 of its record 2611-15. Both were agreed with this survey on 2026-11-17, and both are still Proposed in SummitSG-LLC/hamilton pull request #9. If the owner decides them differently, sections 2 and 6 follow that decision.
- The new runtime's coordinator releases work when its prerequisites are done, as the effort describes; nothing of it existed when this was written.
- The illustrative decorators `select_on` and `loop` stand for any syntax with the same semantics.

**Not novel research.** The decision needs no work beyond comparing documented systems. One exception: the demand rule is this report's own reading of how a pull-based dataflow should scope a branch. The systems compared scope a branch by its position in the graph or by declaration, so the demand rule has no direct precedent among them, and a prototype should check it before it is relied on.

## Appendix A. References

Hamilton, apache/hamilton at `ef88b1e96140a01f3d72967316c2335f8b62a067` (the 2.0 branch point; these files are unchanged on `2.0`):

- [H1] README Burr note: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/README.md#L68
- [H2] `execute_subdag`, depth first: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/execution/graph_functions.py#L168-L270
- [H3] `get_upstream_nodes`: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/graph.py#L1022
- [H4] `DependencyType`: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/node.py#L52-L59
- [H5] `config.when`: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/function_modifiers/configuration.py#L211-L219
- [H6] `step(...).when`: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/function_modifiers/macros.py#L406-L413
- [H7] `resolve`: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/function_modifiers/delayed.py#L66-L67
- [H8] parallel-task caveats: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/docs/concepts/parallel-task.rst?plain=1#L114-L118 and #L145
- [H9] issue #1290: https://github.com/apache/hamilton/issues/1290
- [H10] issue #1016: https://github.com/apache/hamilton/issues/1016
- [H11] the outline, discussion #1645: https://github.com/apache/hamilton/discussions/1645 (comment on control flow: https://github.com/apache/hamilton/discussions/1645#discussioncomment-19484449)
- [H12] `Driver.raw_execute` with `fail_starting=(2, 0, 0)`: https://github.com/apache/hamilton/blob/ef88b1e96140a01f3d72967316c2335f8b62a067/hamilton/driver.py#L606-L613

Apache Burr 0.43.0, tag `v0.43.0-incubating` (commit `971a3530`), prefix https://github.com/apache/burr/blob/v0.43.0-incubating/:

- [B1] `docs/concepts/overview.rst?plain=1#L27`
- [B2] `docs/concepts/transitions.rst?plain=1#L91-L92`
- [B3] `burr/core/graph.py#L150-L160`
- [B4] `docs/concepts/state-machine.rst?plain=1#L40-L52`, `#L117`, `#L123-L126`
- [B5] `burr/core/application.py#L1176-L1179`
- [B6] `telemetry/ui/src/utils.tsx#L23`
- [B7] `burr/core/persistence.py#L136-L140`; `burr/core/application.py#L2091-L2098`
- [B8] `burr/core/state.py#L448-L463`
- [B9] `docs/concepts/parallelism.rst?plain=1#L55-L56`, `#L740-L743`; `burr/core/parallelism.py#L521`
- [B10] `README.md?plain=1#L163-L164`
- [B11] `burr/integrations/hamilton.py#L23-L30`, `#L106-L146`, `#L183-L195`
- [B12] `docs/ecosystem.rst?plain=1#L68-L69`
- [B13] `docs/concepts/planned-capabilities.rst?plain=1#L96-L106`
- [B14] `burr/core/application.py#L1249-L1256`

LangGraph 1.2.22, tag `1.2.22` (commit `08a20169`), prefix https://github.com/langchain-ai/langgraph/blob/1.2.22/libs/langgraph/langgraph/. Docs from https://github.com/langchain-ai/docs/blob/3def9fa8b6a4f5ac308dc37cb7f0c200de336dd7/src/oss/langgraph/ (unversioned; pinned to a docs commit):

- [L1] `pregel/main.py#L460-L483`
- [L2] `graph/state.py#L982-L1001`
- [L3] `types.py#L748-L760`, `#L843-L868`
- [L4] `pregel/_algo.py#L597-L613`
- [L5] `pregel/_loop.py#L297-L305`; `pregel/_task_status.py#L13-L36`
- [L6] `graph/state.py#L930-L933`; docs `graph-api-control-flow.mdx?plain=1#L376-L380`
- [L7] `pregel/_io.py#L23-L53`
- [L8] `_internal/_config.py#L42-L44`; `pregel/main.py#L3118-L3128`; docs `graph-api.mdx?plain=1#L649`
- [L9] `pregel/_algo.py#L614-L624`
- [L10] `runtime.py#L79-L104`; `errors.py#L56-L66`
- [L11] `graph/state.py#L1177-L1182`
- [L12] docs `graph-api-control-flow.mdx?plain=1#L473`

Apache Airflow 3.4.0, tag `3.4.0` (commit `619a787a`), prefix https://github.com/apache/airflow/blob/3.4.0/:

- [A1] `airflow-core/docs/core-concepts/overview.rst?plain=1#L21-L23`
- [A2] `airflow-core/docs/core-concepts/dags.rst?plain=1#L327-L329`
- [A3] `airflow-core/src/airflow/ti_deps/deps/trigger_rule_dep.py#L479-L483`
- [A4] `airflow-core/docs/core-concepts/tasks.rst?plain=1#L81`; `airflow-core/src/airflow/utils/state.py#L233-L236`
- [A5] `airflow-core/src/airflow/task/trigger_rule.py#L23-L38`; `airflow-core/docs/core-concepts/dags.rst?plain=1#L431-L447`, `#L464-L508`
- [A6] `task-sdk/src/airflow/sdk/definitions/xcom_arg.py#L364-L381`; `airflow-core/docs/core-concepts/dag-run.rst?plain=1#L36-L37`
- [A7] `RELEASE_NOTES.rst?plain=1#L33-L41`; `task-sdk/src/airflow/sdk/definitions/decorators/task_group.py#L136-L151`; `airflow-core/docs/authoring-and-scheduling/loops.rst?plain=1#L40-L44`, `#L48-L66`, `#L105-L110`, `#L230-L250`, `#L395-L401`, `#L447`
- [A8] `airflow-core/src/airflow/models/taskinstance.py#L1129-L1141`
- [A9] `airflow-core/src/airflow/api/common/mark_tasks.py#L227-L232`
- [A10] `task-sdk/src/airflow/sdk/definitions/dag.py#L1161-L1175`
- [A11] `airflow-core/src/airflow/ti_deps/deps/trigger_rule_dep.py#L519-L526`; `airflow-core/docs/core-concepts/dag-run.rst?plain=1#L39-L41`

Dagster 1.13.30, tag `1.13.30` (commit `528c6d6a`), prefix https://github.com/dagster-io/dagster/blob/1.13.30/:

- [G1] `docs/docs/guides/build/ops/graphs.md?plain=1#L74-L82`
- [G2] `python_modules/dagster/dagster/_core/execution/plan/active.py#L203-L252`
- [G3] `python_modules/dagster/dagster/_core/events/__init__.py#L111`; `python_modules/dagster/dagster/_core/storage/dagster_run.py#L55-L89`
- [G4] `python_modules/dagster/dagster/_core/execution/plan/compute.py#L216-L236`; `python_modules/dagster/dagster/_core/execution/api.py#L815-L833`
- [G5] `python_modules/dagster/dagster/_core/definitions/graph_definition.py#L288-L298`
- [G6] `docs/docs/guides/build/ops/dynamic-graphs.md?plain=1#L46-L50`
- [G7] `python_modules/dagster/dagster/_core/execution/plan/handle.py#L72-L78`
- [G8] `python_modules/dagster/dagster/_core/execution/plan/compute_generator.py#L367-L375`
- [G9] `CHANGES.md?plain=1#L462`, `#L480`, `#L1352`, `#L3435`, `#L4674`
- [G10] `docs/docs/guides/operate/run-executors.md?plain=1#L25`

Flyte, flytekit 1.16.32 (tag `v1.16.32`, commit `48d41584`), prefix https://github.com/flyteorg/flytekit/blob/v1.16.32/; backend 1.16.9 (tag `v1.16.9`, commit `b2be54c1`), prefix https://github.com/flyteorg/flyte/blob/v1.16.9/:

- [F1] flytekit `flytekit/core/workflow.py#L969-L973`; backend `docs/user_guide/concepts/main_concepts/workflows.rst?plain=1#L8`
- [F2] flytekit `flytekit/core/condition.py#L478-L508`; backend `flyteidl/protos/flyteidl/core/workflow.proto#L19-L47`
- [F3] flytekit `flytekit/core/condition.py#L449`
- [F4] backend `flytepropeller/pkg/controller/nodes/branch/evaluator.go#L91`, `#L134`
- [F5] backend `flyteidl/protos/flyteidl/core/execution.proto#L36`; `flytepropeller/pkg/controller/nodes/executor.go#L1064-L1065`; `flytepropeller/pkg/controller/nodes/predicate.go#L95-L106`
- [F6] backend `flytepropeller/pkg/compiler/validators/branch.go#L41-L42`, `#L102`; flytekit `flytekit/core/condition.py#L124-L127`; backend `flyteidl/protos/flyteidl/core/workflow.proto#L245`
- [F7] backend `flytepropeller/pkg/controller/nodes/branch/handler.go#L147-L148`
- [F8] flytekit `flytekit/core/dynamic_workflow_task.py#L27-L32`; backend `docs/user_guide/advanced_composition/dynamic_workflows.md?plain=1#L19`, `#L141-L142`
- [F9] backend `docs/user_guide/advanced_composition/eager_workflows.md?plain=1#L95-L97`
- [F10] backend `docs/user_guide/advanced_composition/conditionals.md?plain=1#L11-L13`
- [F11] backend `flytepropeller/pkg/compiler/workflow_compiler.go#L80-L82`
- [F12] backend `docs/user_guide/development_lifecycle/caching.md?plain=1#L118`

TensorFlow 2.21.0, tag `v2.21.0` (commit `a481b102`), prefix https://github.com/tensorflow/tensorflow/blob/v2.21.0/:

- [T1] `tensorflow/python/ops/cond.py#L275-L282`
- [T2] `tensorflow/python/ops/cond.py#L291-L300`
- [T3] `tensorflow/python/ops/cond.py#L308-L312`
- [T4] `tensorflow/python/ops/cond_v2.py#L73-L74`
- [T5] `tensorflow/core/common_runtime/propagator_state.cc#L509-L511`; `tensorflow/core/common_runtime/executor.cc#L887-L891`
- [T6] `tensorflow/python/ops/while_loop.py#L45-L53`, `#L83-L88`, `#L152-L155`
- [T7] `tensorflow/core/ops/functional_ops.cc#L235-L244`
- [T8] `tensorflow/core/common_runtime/propagator_state.h#L224-L226`
- [T9] `tensorflow/core/common_runtime/lower_functional_ops.h#L27`; `tensorflow/python/ops/control_flow_util_v2.py#L98-L111`
- [T10] `tensorflow/python/ops/control_flow_state.py#L68-L69`
- [T11] `tensorflow/python/autograph/g3doc/reference/limitations.md?plain=1#L21-L30`, `#L45-L46`
- [T12] Yu et al., "Dynamic Control Flow in Large-Scale Machine Learning", EuroSys 2018, https://doi.org/10.1145/3190508.3190551 (describes the v1 design)
- [T13] `tensorflow/core/common_runtime/direct_session.cc#L926-L930`; `tensorflow/core/framework/function.cc#L1195-L1206`

JAX 0.12.0.1, tag `jax-v0.12.0.1`, prefix https://github.com/jax-ml/jax/blob/jax-v0.12.0.1/:

- [J1] `jax/_src/lax/control_flow/conditionals.py#L213-L217`
- [J2] `jax/_src/lax/control_flow/loops.py#L1682-L1697`

## Appendix B. Search formulations

Each question was searched with at least two formulations per system: a grep of the tagged code and a search of the tagged docs, plus a third where the first two disagreed. These are representative examples.

- **Burr:**
  - `grep -n "get_next_node\|class Graph" burr/core/graph.py`
  - `grep -rn -i "skip" burr/core burr/tracking/common` (no status hits)
  - `grep -rn -i "max_steps\|max_iter\|recursion_limit\|infinite\|forever" burr/core` (only the warning)
  - `grep -rn -i "cancel\|interrupt" burr/core docs/concepts`
  - `grep -rn -i "cach\|memoiz" burr/core docs/concepts`
  - `grep -rn -i hamilton README.md docs`
  - reads of `docs/concepts/{transitions,state-machine,parallelism}.rst`
- **LangGraph:**
  - `grep -rn "recursion_limit\|GraphRecursionError\|DEFAULT_RECURSION_LIMIT"`
  - `grep -n "_triggers\|PULL" pregel/_algo.py`
  - `grep -rn -i skip pregel graph types.py`
  - `grep -n "never runs\|defer" graph-api-control-flow.mdx`
  - `grep -n "cache_policy\|CachePolicy"`
  - `grep -n "class RunControl\|GraphDrained"`
- **Airflow:**
  - `grep -n -i "branch|skip" dags.rst`
  - `grep -rn "class BaseBranchOperator|ignore_downstream_trigger_rules"`
  - `grep -n "SKIPPED|skipped" trigger_rule_dep.py`
  - `grep -n "class TriggerRule"`
  - `grep -rn -i "acyclic|AirflowDagCycleException"`
  - `grep -rln -i "\.loop("`
  - `grep -n -i "loop|branch|condition|skip" RELEASE_NOTES.rst`
  - `grep -n "region_id|region_index" taskinstance.py`
  - `grep -n "SKIPPED" mark_tasks.py`
- **Dagster:**
  - `grep -rln "is_required=False|skippable|selected_output_names" docs/docs`
  - `grep -n -i "skip" active.py`
  - `grep -rn "STEP_SKIPPED"`
  - `grep -n "FromMultipleSources" inputs.py plan.py`
  - `grep -rn -i "circular|cycle"` in `_core/definitions`
  - `grep -rn -i "loop|iterat" docs/docs/guides/build/ops`
  - `grep -n -i "skipped" CHANGES.md`
- **Flyte:**
  - `grep -n "class \|def \|raise" flytekit/core/condition.py`
  - `grep -n "IfBlock\|IfElseBlock\|BranchNode" workflow.proto`
  - `grep -rn "NodePhaseSkipped\|PredicatePhaseSkip"`
  - `grep -n "Intersect" validators/branch.go`
  - `grep -n "recurs\|loop\|depth\|limit" dynamic_workflows.md`
  - `grep -rn -i "recursion\|nesting\|max.*depth" --include=*.go`
  - `grep -n -i "cache key\|composed of" caching.md`
- **TensorFlow:**
  - `grep -n "executing_eagerly\|_eager_cond_implementation" cond.py`
  - `grep -n "is_dead\|get_is_dead" executor.cc`
  - `grep -n "dead\|is_merge" propagator_state.cc`
  - `grep -n maximum_iterations while_loop.py while_v2.py`
  - `grep -n "frame_name\|iteration" propagator_state.h`
  - `grep -rn "allow_dead_tensors\|does not have value"`
  - `grep -n "^#\|must be defined\|undefined" control_flow.md limitations.md`
- **Hamilton demand:**
  - `gh search issues --repo apache/hamilton` with "conditional", "branch", "loop", "cycle", "if else", "while", "skip", "switch", "recursion", "short circuit", "early stop", "control flow", "state machine" and "Burr"
  - a GraphQL search of discussions for "conditional", "branch", "loop", "cycle" and "Burr"

## Appendix C. Reproduction

The commands ran from a checkout of `2.0` at `31b3a832`, with the project's environment (`uv run`). The scripts live outside the repository, in `/tmp/t26demo/`.

`fx_branch.py`, the branch emulation:

```python
from hamilton.htypes import Collect, Parallelizable

CALLS: list[str] = []


def transactions(raw: list[dict]) -> list[dict]:
    CALLS.append("transactions")
    return raw


def currency(transactions: list[dict]) -> str:
    CALLS.append("currency")
    return transactions[0]["currency"]


def needs_conversion(currency: str) -> Parallelizable[str]:
    CALLS.append("needs_conversion")
    if currency != "USD":
        yield currency


def fx_rate(needs_conversion: str) -> float:
    CALLS.append(f"fx_rate({needs_conversion!r})")
    return {"EUR": 1.1, "GBP": 1.3}[needs_conversion]


def converted(fx_rate: float) -> float:
    CALLS.append("converted")
    return fx_rate


def rate_or_nothing(converted: Collect[float]) -> list[float]:
    CALLS.append("rate_or_nothing")
    return list(converted)


def amounts_usd(transactions: list[dict], rate_or_nothing: list[float]) -> list[float]:
    CALLS.append("amounts_usd")
    rate = rate_or_nothing[0] if rate_or_nothing else 1.0
    return [t["amount"] * rate for t in transactions]
```

`run_fx.py`, the runner. Run it with `uv run --python 3.15 python -I /tmp/t26demo/run_fx.py`; the output is in section 4. On CPython 3.11.15 the output is the same, except that the `TypeError` message reads `unhashable type: 'list'`.

```python
import sys

sys.path.insert(0, "/tmp/t26demo")
import fx_branch  # noqa: E402

import hamilton  # noqa: E402
from hamilton import driver  # noqa: E402
from hamilton.execution.executors import SynchronousLocalTaskExecutor  # noqa: E402

print("hamilton", hamilton.version.VERSION, "python", sys.version.split()[0])
dr = (
    driver.Builder()
    .with_modules(fx_branch)
    .enable_dynamic_execution(allow_experimental_mode=True)
    .with_local_executor(SynchronousLocalTaskExecutor())
    .build()
)
for cur in ["USD", "EUR"]:
    fx_branch.CALLS.clear()
    raw = [{"currency": cur, "amount": 10.0}, {"currency": cur, "amount": 5.0}]
    res = dr.execute(["amounts_usd"], inputs={"raw": raw})
    print(cur, "request amounts_usd ->", res["amounts_usd"], "calls:", fx_branch.CALLS)
for cur in ["EUR", "USD"]:
    fx_branch.CALLS.clear()
    raw = [{"currency": cur, "amount": 10.0}]
    try:
        res = dr.execute(["fx_rate"], inputs={"raw": raw})
        print(cur, "request fx_rate ->", res, "calls:", fx_branch.CALLS)
    except Exception as e:
        print(
            cur,
            "request fx_rate -> raised",
            type(e).__name__,
            str(e)[:300],
            "calls:",
            fx_branch.CALLS,
        )
```

`run_chain.py`, the unrolled chain. It takes the chain lengths as arguments:

```python
import sys

from hamilton import ad_hoc_utils, driver


def make_step(i: int):
    prev = "x0" if i == 1 else f"x{i - 1}"
    ns: dict = {}
    exec(f"def x{i}({prev}: int) -> int:\n    return {prev} + 1\n", ns)
    return ns[f"x{i}"]


for n in [int(a) for a in sys.argv[1:]]:
    mod = ad_hoc_utils.create_temporary_module(*[make_step(i) for i in range(1, n + 1)])
    dr = driver.Builder().with_modules(mod).build()
    try:
        out = dr.execute([f"x{n}"], inputs={"x0": 0})
        print(n, "nodes ->", out[f"x{n}"])
    except RecursionError as e:
        print(n, "nodes -> RecursionError:", str(e)[:80])
print("recursionlimit", sys.getrecursionlimit(), "python", sys.version.split()[0])
```

```text
$ uv run --python 3.15 python -I /tmp/t26demo/run_chain.py 500 900 950 990 1000 1500
500 nodes -> 500
900 nodes -> 900
950 nodes -> 950
990 nodes -> 990
1000 nodes -> RecursionError: maximum recursion depth exceeded
1500 nodes -> RecursionError: maximum recursion depth exceeded
recursionlimit 1000 python 3.15.0
$ uv run --python 3.11 python -I /tmp/t26demo/run_chain.py 500 900 950 990 1000 1500
500 nodes -> 500
900 nodes -> 900
950 nodes -> 950
990 nodes -> RecursionError: maximum recursion depth exceeded
1000 nodes -> RecursionError: maximum recursion depth exceeded
1500 nodes -> RecursionError: maximum recursion depth exceeded
recursionlimit 1000 python 3.11.15
```
