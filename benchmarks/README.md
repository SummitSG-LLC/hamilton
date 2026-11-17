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

# Benchmark harness

One command measures how fast Hamilton imports, builds graphs and executes them, and writes the measurements to a JSON file. It exists so that a claim that one version or path is faster, slower or unchanged than another rests on a measure that was proven to detect a slowdown and then frozen. The harness imports only the standard library; Hamilton is imported by worker processes in the interpreter and checkout under test.

```bash
python benchmarks/harness.py list                       # the scenarios, and whether each is frozen
python benchmarks/harness.py run --out result.json      # every scenario, on this checkout
python benchmarks/harness.py compare result.json        # verdicts between the sides of one run
python benchmarks/harness.py profile build-1k           # where one scenario spends its time
```

## Scenarios

Each scenario is addressable by name with `--scenario NAME` (repeat it for several). Every scenario checks its output against an oracle computed without Hamilton (`fixtures.py`) after the warm-up and after the last sample; a wrong output stops the run, because a scenario that returns wrong results fast is not a measurement.

| Scenario | Measures | Named by |
| --- | --- | --- |
| `import-driver` | `import hamilton.driver` in a fresh interpreter for every sample | Ticket 21 |
| `build-1k`, `build-10k` | building a Driver from a generated layered graph of 1,000 or 10,000 integer nodes | (Ticket 19 adds its own scenarios on the 1,000-node graph) |
| `execute-default-1k`, `execute-default-10k` | executing those graphs on the default path, requesting every node of the last layer | Ticket 10 |
| `execute-tasks-sync-1k` | executing the 1,000-node graph on the task-based path, with `SynchronousLocalTaskExecutor` as the local and the remote executor | |
| `tiny-nodes` | per-execution overhead: 200 executes of a 10-node graph of tiny nodes per sample, reported per execute | Ticket 10 |
| `cpu-sequential` | the 32-kernel CPU workload with one node per item, on the default path | Ticket 13 |
| `cpu-mapped-4` | the same workload expanded with `Parallelizable` and collected, on four `MultiThreadingExecutor` workers | Ticket 13 |
| `cpu-threadpool-4` | the same kernels on a plain `ThreadPoolExecutor` with four workers, without Hamilton | Ticket 13 |

The layered graphs have 20 layers; node `j` of each layer depends on node `j` of the previous layer and on up to two more nodes of it, so every node is upstream of the requested outputs. All 1.x paths call nodes through one recursive function, and a linear chain of 1,500 nodes raises `RecursionError`; at a depth of 20 the graphs stay far from the recursion limit, so the harness leaves the limit alone and records it. The CPU workload is the one the 2.0 outline defines: 32 identical pure-Python integer kernels with distinct item IDs and 262,144 iterations each.

The task-based path is measured at 1,000 nodes only. In a one-off measurement outside the harness, on the machine of the reference results with CPython 3.15, two executes of the 10,000-node graph on that path took 35.4 and 36.2 seconds, against 0.28 to 0.32 seconds for the 1,000-node graph: its cost grows faster than the node count, and seven rounds of it would take most of an hour.

Every scenario reports wall time and the CPU time of the thread that calls the measured operation. For a threaded run that second metric is the coordinator's share: process CPU time would include the workers and hide a coordinator that polls while they run.

## Sides

A side is what one set of measurements runs against: `--side LABEL[:key=value,...]`, with these keys.

- `switch`: `1x` (the 1.x build and execution paths; the default) or `new` (the new compiler and runtime).
- `python`: the interpreter, and with it the environment of installed packages. Default: the interpreter running `harness.py`.
- `checkout`: a source tree whose `hamilton/` package is measured. Default: the checkout holding `harness.py`. The worker puts it first on `PYTHONPATH` and fails if `hamilton` is imported from anywhere else; an installed copy of Hamilton in the environment can shadow it, so uninstall it there.

With two or more sides, `run` measures them alternately: for each scenario and each round, every side runs once in a fresh worker process, and the order of the sides is reversed every other round. It then prints a comparison. This is how a comparison is made, in one invocation on one machine:

```bash
# This checkout against the commit before a change, in one shared environment
git worktree add --detach /tmp/before HEAD~1
python benchmarks/harness.py run --out compare.json --side before:checkout=/tmp/before --side after

# Each side in its own environment, e.g. when a change removes a required dependency
python benchmarks/harness.py run --out compare.json --scenario import-driver \
  --side before:python=/tmp/env-before/bin/python,checkout=/tmp/before \
  --side after:python=/tmp/env-after/bin/python
```

A stored result file is a reference record. It is never one side of a comparison: both sides of a comparison run alternately in the same invocation, and `compare` reads only the sides of one file.

The switch that selects the new side does not exist yet (Ticket 07 adds it). Until it does, a side with `switch=new` stops the run before anything is measured, with a message that says so; the harness never measures the 1.x paths under the name `new`. The functions under "Side hooks" in `scenarios.py` are the only code that selects a side, and they are where the new side is wired in.

## Noise floor and verdicts

Each scenario runs `ROUNDS` (7) rounds per side. A round is a fresh worker process that builds its fixture, runs the warm-up samples and then the measured samples; the garbage collector runs before every sample. A round's value is its fastest sample, because work that shares the machine only adds time. A side's value is the median of its rounds' values. Its noise floor is the spread between its rounds' values, leaving out the fastest and the slowest round, as a fraction of that value: the run-to-run variation of the measure on that machine at that time. The result file keeps every sample, and for each metric the value, the noise floor, each round's value, and the count, minimum, median and maximum of all samples.

These statistics were chosen before the reference results were taken, from runs on a machine shared with other CPU-heavy work (load average 4 to 10 on 8 logical CPUs). In an A/A pilot (one side under two labels, 5 rounds) the spread of the rounds' medians was 10% to 60% for `build-1k`, the two default-path execute scenarios and `tiny-nodes`, and the spread of the rounds' minima 3.5% to 12.4%; `build-10k`, the task-based scenario and the three CPU workloads stayed noisy under both (up to 40%, 180% and 90%), because contention there lasted whole rounds. A first run of the slowdown proof then showed that one round disturbed from start to end widens a full range enough to hide a 50% slowdown, so the spread leaves out the extreme rounds and the rounds went from 5 to 7. In a simulation with normally distributed round values, an A/A gap exceeded this floor in 1.8% of trials, against 0.4% for the full range of 5 rounds and 15% for the middle three of 5.

`compare` gives each side's gap to the baseline side (the first, or `--baseline LABEL`) as the ratio of the two values minus one, and its verdict: "no measurable difference" when the gap is no larger than the larger of the two sides' noise floors, otherwise "slower" or "faster". A performance claim in this effort cites the verdict, the scenario, the run count and range on each side, the noise floor, the machine and Python build from the result file, and the limiter named from a profile.

`profile SCENARIO` runs one round of a scenario under `cProfile` and prints the top functions (`--sort tottime` for own time, `--out FILE` to keep the stats). For `import-driver` it prints the slowest imports from `python -X importtime` instead.

## What is frozen

`frozen.json` holds a fingerprint of each scenario's settings: its fixture source, sizes, inputs, outputs, path and executors, metrics, warm-up and sample counts, and the number of rounds. `benchmarks/tests/test_harness.py` fails when a fingerprint changes, so a frozen scenario changes only by a deliberate edit of `frozen.json` that a reviewer sees. `python benchmarks/harness.py fingerprints` prints the current fingerprints, and every result file records each scenario's fingerprint and whether it matched `frozen.json`.

The fingerprint does not cover how a scenario selects a side. Later Tickets may wire the new side into the side hooks, and may add scenarios with their own entries in `frozen.json`; they do not change a frozen scenario. The `--rounds`, `--warmup` and `--samples` options exist for smoke runs, and a result file made with them says that it is not a measurement with the frozen settings.

## Result files

A result file records what a reader needs to judge it: the machine (operating system, CPU, CPU count, memory), the start and end time, the load average before every worker, a free-text `--note`, the harness commit, and for each side its switch, the commit of its checkout with any uncommitted change under `hamilton/` (the diff included), the Python build, whether the build is free-threaded and whether the GIL was enabled after the imports and after each round's setup, the recursion limit, and the version of every installed package. On a free-threaded build an extension that is not free-threading-safe turns the GIL back on when it is imported; the harness then adds a warning to the file, because the result describes a different interpreter than its label says.

## Reference results

`results/` holds the 1.x paths measured at the `2.0` branch point, commit `077b7a1d` of `apache/hamilton` `main`. Its `hamilton/` is identical to that of `ef88b1e9`, the commit the effort's front file was measured at. It is not the tip of `2.0`: fixes on `2.0` already change `hamilton/` (one of them, the fix of type hints of a function behind a wrapper, on the build path). `benchmarks/reference.sh OUT_DIR` repeats the measurement on another machine, for CPython 3.15 and free-threaded 3.14 by default: a detached worktree of the branch point, and for each Python a new environment holding Hamilton's required dependencies and nothing else.

- `reference-1x-077b7a1d-python-3.15.json` and `reference-1x-077b7a1d-python-3.14t.json`: the reference records, made with `reference.sh`, on CPython 3.15.0 and on free-threaded CPython 3.14.9 with the GIL disabled throughout.
- `proof-delay-5us-per-node.json`: the proof that the measure detects a slowdown. The side `delayed` is the branch point with a scratch busy-wait of 5 microseconds at the start of `execute_lifecycle_for_node`, which every 1.x path calls once per node; the file holds its diff. The change is not part of the repository. Both default-path execute scenarios report it as slower by far more than their noise floors, and by 5.4 to 5.8 microseconds per node executed. `tiny-nodes` and `execute-tasks-sync-1k` report no measurable difference in this run: under the load of that hour their noise floors (46% and 97%) exceeded the gaps measured (35% and -11%). The delay adds about 50 microseconds to an execute of the tiny graph (about 50% of its undisturbed time) and about 5 milliseconds to the task-based execute (about 2%), which is below even the 6% floor of `execute-tasks-sync-1k` in the A/A run.
- `proof-a-a.json`: the branch point under two labels, the check that the noise floor does not report a difference where there is none.

These files were measured with the harness before its commits were squashed, so the harness commit they name is not in the history; each scenario's fingerprint in them matches `frozen.json`. They were measured on a desktop that other CPU-heavy jobs shared at the same time, and the load average before each worker is in the files: rerun `reference.sh` on a quiet machine for a cleaner record.
