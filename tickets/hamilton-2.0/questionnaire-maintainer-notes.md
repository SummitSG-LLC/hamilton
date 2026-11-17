# Questions on the maintainer's layering note

Source: apache/hamilton discussion #1645, skrawcz's reply of 2026-11-17 (discussioncomment-19685905), "Some old notes I dug up". This file compares the note with the Hamilton 2.0 first plan and lists what the plan cannot settle from the note, the outline, the code or the issue tracker. Each question has options and the default the plan follows until answered. Nothing here has been sent to the maintainer; posting it is the owner's act.

## How the four layers map onto the plan

| Layer in the note | In the plan | Agreement |
| --- | --- | --- |
| 1. Generation: f(code + config) -> graph | The compiler and the immutable compiled graph (Tickets 08, 09, 18) | Agree. |
| 2. Augmentation: f(graph, config, ?) -> graph | No named stage. Materializers derive a new compiled graph (Tickets 09, 14); validation nodes come from decorators at compile time; the cache and fingerprints attach as a node-call wrapper and an observer (Ticket 14); fusion and checkpointing are absent. | Differ in shape. Nothing in the plan forbids a graph-to-graph step; one is now required to be public (Ticket 09). |
| 3. Walking: f(graph, ?) -> paths | The plan (selected nodes and their prerequisite relation) and the coordinator, which releases a node when its prerequisites finish (Tickets 07, 10) | Differ: start order is decided at run time, not computed beforehand as a value. The plan is now required to be public and buildable without executing (Ticket 07). |
| 4. Execution: f(paths, ?) -> objects | Coordinator, execution backend, run state, result builder (Tickets 07, 10 to 13, 15) | Agree for single process, asynchronous and task-at-a-time delegation. Process pools and Ray, Dask and Spark ports are ruled out of this plan by the owner; code generation is left out by the plan. |

## What went into the Tickets without asking

- Ticket 07: a task template may hold more than one node (fusion, issue #45); the plan is a public read-only value that can be built without executing; the decision record answers whether a module may supply bindings before the plan is made, and whether a backend may return deferred handles or take the whole plan.
- Ticket 09: one public way to derive a new compiled graph from an existing one plus extra nodes, and no other graph-to-graph step.
- Ticket 10: the inline backend starts nodes in a deterministic, documented order.
- Tickets 14 and 19: pointers to the questions below.

## Questions

Q1. **BFS.** The outline replaced "BFS" with ready-work scheduling: sources run first and each node is released when its prerequisites finish, with no level barrier, because a level barrier can hold ready work behind an unrelated slow task. Is anything you want from BFS missing?
- (a) No, ready-work scheduling is what was meant. **Default.**
- (b) Strict level-by-level order is wanted as a selectable strategy.
- (c) A forward walk in which a node decides what runs next. That is runtime branching, surveyed in Ticket 26 (fork pull request #10), which recommends deferring it.

Q2. **"Paths".** What is the output of the walking layer?
- (a) The selected subgraph with its prerequisite relation, which is the plan's "plan"; order is the coordinator's. **Default.**
- (b) A precomputed total order of nodes, swappable between BFS and DFS. This cannot hold with map and collect, where task instances are known only at run time.
- (c) Alternative branches to choose from at run time.

Q3. **"Running DAG through to leaf nodes".** 1.x requires `final_vars`; issue #836 asks to execute all nodes.
- (a) `execute()` with no requested outputs runs to every sink node. The plan would add a catalog query for sink nodes to Ticket 19. **Default.**
- (b) Run everything reachable forward from the supplied inputs, skipping nodes whose other inputs are missing. New work.
- (c) A push-style walk needed for branching (see Q1c).

Q4. **The asterisks** on input validation, output validation and running to leaf nodes: do they mean "not in 1.x today"? **Default: yes.**

Q5. **"Automatic" input and output validation.** `@check_output` is listed under generation ("checking outputs"), so this is something else.
- (a) Checks derived from annotations (`Annotated` metadata, pydantic models, Pandera types) with no decorator, as issue #786 proposed. **Default**, deferred past the first plan; Ticket 09 preserving `Annotated` metadata is the enabling step.
- (b) A Driver setting that turns strict type checks on for every node, as `FunctionInputOutputTypeChecker` does today.
- (c) Today's `@check_output`, moved from decoration to a later pass.

Q6. **Where automatic checks live.** Graph nodes, as in 1.x, or plan steps that the catalog does not show? **Default: plan steps.** The outline reports 576 of 1,002 nodes in one user's library as validation plumbing. The plan today rules out any change to how `@check_output` nodes are named or exposed.

Q7. **"Checking outputs" under generation.**
- (a) Requested outputs exist and are reachable, and (b) decorator-declared outputs are unique and consistent. **Default: both**, covered by Tickets 18 and 19.
- (c) `@check_output`.

Q8. **Short-circuiting from cached values.** Today overrides prune the walk, and the cache does not: it visits every node on the path and fetches results. Should a stored value remove everything upstream of it from the plan?
- (a) Not in the first plan; the contract records whether it is possible (Ticket 07). **Default.**
- (b) Yes, in 2.0.

Q9. **Checkpointing.** Nothing in 1.x has that name. Issue #940 separates `.with_cache()` (fingerprints) from `.with_checkpointing()` (restart from stored outputs), and the outline lists durable recovery under separate proofs.
- (a) The #940 meaning: store chosen node outputs by run and node, and start a later run from them without fingerprints. **Default.** The plan would add a survey Ticket, "Checkpoint and resume", after Tickets 07, 11 and 14; it is not created yet.
- (b) Durable crash recovery with replay and side-effect handling.
- (c) Both, in that order.

Q10. **Node fusion or grouping.** Is 1.x's `with_grouping_strategy` needed on the new runtime in 2.0, or is it enough that the contract allows a task of several nodes? **Default: the contract allows it; no grouping option in the prototype** (Ticket 11 refuses `with_grouping_strategy` with the switch on).

Q11. **"Adding nodes for materialization/other concerns".** Which other concerns should add nodes to the graph? **Default: none in the first plan.**

Q12. **The `?` arguments.** For augmentation: per-Driver settings give a graph, and per-run facts (inputs, overrides, cache state) give a plan? For walking: requested outputs, inputs and overrides? For execution: the backend and attached modules? **Default: yes to all three.**

Q13. **Multi process.** The owner ruled a process-pool backend out of this plan; the contract is proven by a test backend that runs each task in another process, and the conformance kit must pass a backend that shares no memory. 1.x's `MultiProcessingExecutor` says of itself "not yet augmented to handle the right serialization, so use at your own risk". Is contract plus kit enough for 2.0, with free-threaded threads as the CPU-parallel path? **Default: yes.**

Q14. **Delegated systems.** 1.x has two shapes: task-at-a-time submission (`RayTaskExecutor`, `DaskExecutor`) and lazy handles, where the other system owns ordering (`RayGraphAdapter`, `DaskGraphAdapter`, the Spark adapters). Issue #16 reads as whole-DAG hand-off.
- (a) Task-at-a-time only.
- (b) Lazy handles or whole-graph hand-off only.
- (c) Both named in the contract, only task-at-a-time proven in 2.0. **Default.** No Ray, Dask or Spark port is built in this plan.

Q15. **Generating code for other systems.** The outline puts general code generation in the research backlog and names a runnable driver script as the narrow first step.
- (a) Not in 2.0; the catalog artifact of Ticket 19 is the foundation. **Default** for the prototype.
- (b) The driver-script emitter only.
- (c) One orchestrator target.
