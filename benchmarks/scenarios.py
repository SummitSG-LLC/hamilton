# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""The benchmark scenarios: what each one measures, how often, and how its output is checked.

A scenario's *settings* are its fixture, its inputs, its run counts and its setup. They are frozen
in ``frozen.json`` by a fingerprint, and a test fails when a frozen scenario's settings change.
How a scenario selects a side of the switch is not part of the settings: the Tickets that build
the new side wire it in here, in the functions marked as side hooks.

This module imports Hamilton only inside ``prepare`` functions, which run in a worker process with
the side's interpreter and checkout. The controller imports it to list scenarios and their
fingerprints.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Any, Protocol

import fixtures

if TYPE_CHECKING:
    import pathlib
    from collections.abc import Callable

# The sides of the switch. "1x" is the 1.x build and execution paths; "new" is the new compiler and
# runtime, which do not exist yet.
SWITCHES = ("1x", "new")

# Worker processes per scenario and side. Every round is a fresh process, and the noise floor is the
# spread between the rounds' values, so this also fixes how well the noise floor is estimated.
ROUNDS = 7

# The layered graphs. Twenty layers keep the recursive 1.x execution far from the recursion limit
# (a linear chain of 1,500 nodes raises RecursionError), so the harness leaves the limit alone.
GRAPH_1K = fixtures.LayeredGraph(layers=20, width=50)
GRAPH_10K = fixtures.LayeredGraph(layers=20, width=500)
GRAPH_TINY = fixtures.LayeredGraph(layers=5, width=2)
GRAPH_INPUT = 7
TINY_EXECUTES_PER_SAMPLE = 200

CPU_WORKLOAD = fixtures.CpuWorkload(items=tuple(range(32)), iterations=262_144)
CPU_WORKERS = 4


class SwitchUnavailable(RuntimeError):
    """The selected side of the switch cannot be measured with this checkout."""


class ScenarioCheckFailed(AssertionError):
    """A scenario's output differs from its oracle: its timings are not a measurement."""


class Prepared(Protocol):
    def sample(self) -> dict[str, float]:
        """Runs the measured operation once and returns its metrics."""

    def check(self) -> None:
        """Raises ScenarioCheckFailed unless the last sample's output matches the oracle."""


@dataclasses.dataclass(frozen=True)
class Scenario:
    name: str
    description: str
    # The first metric is the one comparisons lead with.
    metrics: tuple[str, ...]
    warmup: int
    samples: int
    prepare: Callable[[str, pathlib.Path], Prepared]
    settings: dict[str, Any]
    # False for a baseline that runs without Hamilton and so measures the same code on every side.
    uses_hamilton: bool = True

    def fingerprint(self) -> str:
        frozen = {
            "rounds": ROUNDS,
            "warmup": self.warmup,
            "samples": self.samples,
            "metrics": list(self.metrics),
            "settings": self.settings,
        }
        return hashlib.sha256(json.dumps(frozen, sort_keys=True).encode()).hexdigest()


# --- Side hooks: the only code that knows how to select a side of the switch. -------------------


def check_switch(switch: str) -> None:
    """Fails unless the checkout in this process can run the given side of the switch."""
    if switch not in SWITCHES:
        raise SwitchUnavailable(f"Unknown side {switch!r}; the sides are {', '.join(SWITCHES)}.")
    if switch == "new":
        raise SwitchUnavailable(
            "The side 'new' (the new compiler and runtime) cannot be measured yet: the switch that "
            "selects it does not exist in this checkout (Ticket 07 adds it). The harness will not "
            "measure the 1.x paths under the name 'new'."
        )


def builder(switch: str):
    """A ``Builder`` for the given side, with nothing else set."""
    check_switch(switch)
    from hamilton import driver

    return driver.Builder()


def synchronous_task_builder(switch: str):
    """A ``Builder`` for the task-based path, running every task in the calling thread."""
    from hamilton.execution import executors

    return (
        builder(switch)
        .enable_dynamic_execution(allow_experimental_mode=True)
        .with_local_executor(executors.SynchronousLocalTaskExecutor())
        .with_remote_executor(executors.SynchronousLocalTaskExecutor())
    )


def threaded_task_builder(switch: str, workers: int):
    """A ``Builder`` for the task-based path, running mapped tasks on ``workers`` threads."""
    from hamilton.execution import executors

    return (
        builder(switch)
        .enable_dynamic_execution(allow_experimental_mode=True)
        .with_local_executor(executors.SynchronousLocalTaskExecutor())
        .with_remote_executor(executors.MultiThreadingExecutor(max_tasks=workers))
    )


# --- Measuring. ----------------------------------------------------------------------------------


def timed(operation: Callable[[], Any]) -> tuple[Any, dict[str, float]]:
    """Runs ``operation`` once; returns its result, wall time and the calling thread's CPU time.

    The thread's CPU time excludes worker threads, so for a threaded run it is the coordinator's
    share: a coordinator that polls while its workers run shows it here.
    """
    cpu_start = time.thread_time()
    wall_start = time.perf_counter()
    result = operation()
    wall = time.perf_counter() - wall_start
    cpu = time.thread_time() - cpu_start
    return result, {"wall_s": wall, "main_thread_cpu_s": cpu}


def expect(actual: Any, expected: Any, what: str) -> None:
    if actual != expected:
        raise ScenarioCheckFailed(f"{what}: the output differs from the oracle")


WALL_AND_CPU = ("wall_s", "main_thread_cpu_s")

# Measures one import of hamilton.driver in a fresh interpreter: a second import in one process
# would be served from sys.modules.
IMPORT_PROBE = """\
import time
cpu_start = time.thread_time()
wall_start = time.perf_counter()
import hamilton.driver
wall = time.perf_counter() - wall_start
cpu = time.thread_time() - cpu_start
import json, sys
print(json.dumps({"wall_s": wall, "main_thread_cpu_s": cpu, "file": hamilton.driver.__file__}))
"""


class ImportDriver:
    def __init__(self, switch: str, workdir: pathlib.Path) -> None:
        check_switch(switch)
        self._workdir = workdir
        self._file: str | None = None

    def sample(self) -> dict[str, float]:
        # -P keeps the working directory off sys.path; PYTHONPATH still selects the checkout.
        completed = subprocess.run(
            [sys.executable, "-P", "-c", IMPORT_PROBE],
            cwd=self._workdir,
            capture_output=True,
            text=True,
            check=True,
        )
        result = json.loads(completed.stdout.strip().splitlines()[-1])
        self._file = result.pop("file")
        return result

    def check(self) -> None:
        checkout = os.environ.get("BENCHMARK_CHECKOUT")
        expected = os.path.join(checkout, "hamilton", "driver.py") if checkout else None
        if self._file is None or (expected and os.path.realpath(self._file) != expected):
            raise ScenarioCheckFailed(
                f"The fresh interpreter imported {self._file}, not {expected}"
            )


class BuildLayered:
    def __init__(self, graph: fixtures.LayeredGraph, switch: str, workdir: pathlib.Path) -> None:
        self._graph = graph
        self._switch = switch
        self._module = fixtures.load_module(
            workdir, f"bench_layered_{graph.node_count}", graph.source()
        )
        self._driver = None

    def sample(self) -> dict[str, float]:
        self._driver, metrics = timed(
            lambda: builder(self._switch).with_modules(self._module).build()
        )
        return metrics

    def check(self) -> None:
        result = self._driver.execute(self._graph.final_nodes(), inputs={"x": GRAPH_INPUT})
        expect(result, self._graph.oracle(GRAPH_INPUT), f"{self._graph} built")


class ExecuteLayered:
    def __init__(
        self,
        graph: fixtures.LayeredGraph,
        make_builder: Callable[[], Any],
        workdir: pathlib.Path,
    ) -> None:
        self._graph = graph
        module = fixtures.load_module(workdir, f"bench_layered_{graph.node_count}", graph.source())
        self._driver = make_builder().with_modules(module).build()
        self._outputs = graph.final_nodes()
        self._result = None

    def sample(self) -> dict[str, float]:
        self._result, metrics = timed(
            lambda: self._driver.execute(self._outputs, inputs={"x": GRAPH_INPUT})
        )
        return metrics

    def check(self) -> None:
        expect(self._result, self._graph.oracle(GRAPH_INPUT), f"{self._graph} executed")


class TinyNodes:
    """Per-execution overhead: a graph of ten tiny nodes executed many times per sample."""

    def __init__(self, switch: str, workdir: pathlib.Path) -> None:
        module = fixtures.load_module(workdir, "bench_tiny", GRAPH_TINY.source())
        self._driver = builder(switch).with_modules(module).build()
        self._outputs = GRAPH_TINY.final_nodes()
        self._result = None

    def _run(self) -> Any:
        result = None
        for _ in range(TINY_EXECUTES_PER_SAMPLE):
            result = self._driver.execute(self._outputs, inputs={"x": GRAPH_INPUT})
        return result

    def sample(self) -> dict[str, float]:
        self._result, metrics = timed(self._run)
        return {
            "wall_per_execute_s": metrics["wall_s"] / TINY_EXECUTES_PER_SAMPLE,
            "main_thread_cpu_per_execute_s": metrics["main_thread_cpu_s"]
            / TINY_EXECUTES_PER_SAMPLE,
        }

    def check(self) -> None:
        expect(self._result, GRAPH_TINY.oracle(GRAPH_INPUT), "the tiny graph executed")


class CpuGraph:
    """The CPU workload as a Hamilton graph; ``results`` lists the kernels' outputs in item order."""

    def __init__(self, source: str, name: str, make_builder: Callable[[], Any], workdir) -> None:
        module = fixtures.load_module(workdir, name, source)
        self._driver = make_builder().with_modules(module).build()
        self._result = None

    def sample(self) -> dict[str, float]:
        self._result, metrics = timed(
            lambda: self._driver.execute(
                ["results"], inputs={"iterations": CPU_WORKLOAD.iterations}
            )
        )
        return metrics

    def check(self) -> None:
        expect(self._result["results"], CPU_WORKLOAD.oracle(), "the CPU workload")


class CpuThreadPool:
    """The same kernels on a plain ``ThreadPoolExecutor``, with no Hamilton involved."""

    def __init__(self, switch: str, workdir: pathlib.Path) -> None:
        check_switch(switch)
        # The kernel comes from the same generated source the Hamilton graphs run.
        module = fixtures.load_module(workdir, "bench_cpu_kernel", CPU_WORKLOAD.sequential_source())
        self._kernel = module._kernel
        self._result = None

    def _run(self) -> list[int]:
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=CPU_WORKERS) as pool:
            futures = [
                pool.submit(self._kernel, item, CPU_WORKLOAD.iterations)
                for item in CPU_WORKLOAD.items
            ]
            return [future.result() for future in futures]

    def sample(self) -> dict[str, float]:
        self._result, metrics = timed(self._run)
        return metrics

    def check(self) -> None:
        expect(self._result, CPU_WORKLOAD.oracle(), "the CPU workload on a thread pool")


def _layered_settings(graph: fixtures.LayeredGraph, **extra: Any) -> dict[str, Any]:
    return {
        "graph": dataclasses.asdict(graph),
        "fixture_sha256": fixtures.digest(graph.source()),
        "input_x": GRAPH_INPUT,
        "outputs": "every node of the last layer",
        **extra,
    }


def _cpu_settings(source: str, **extra: Any) -> dict[str, Any]:
    return {
        "items": list(CPU_WORKLOAD.items),
        "iterations": CPU_WORKLOAD.iterations,
        "fixture_sha256": fixtures.digest(source),
        **extra,
    }


SCENARIOS: dict[str, Scenario] = {
    scenario.name: scenario
    for scenario in [
        Scenario(
            name="import-driver",
            description="`import hamilton.driver` in a fresh interpreter per sample",
            metrics=WALL_AND_CPU,
            warmup=1,
            samples=4,
            prepare=ImportDriver,
            settings={"statement": "import hamilton.driver", "interpreter_flags": ["-P"]},
        ),
        Scenario(
            name="build-1k",
            description="build a Driver from a generated layered graph of 1,000 nodes",
            metrics=WALL_AND_CPU,
            warmup=1,
            samples=5,
            prepare=lambda switch, workdir: BuildLayered(GRAPH_1K, switch, workdir),
            settings=_layered_settings(GRAPH_1K, path="default Builder"),
        ),
        Scenario(
            name="build-10k",
            description="build a Driver from a generated layered graph of 10,000 nodes",
            metrics=WALL_AND_CPU,
            warmup=1,
            samples=3,
            prepare=lambda switch, workdir: BuildLayered(GRAPH_10K, switch, workdir),
            settings=_layered_settings(GRAPH_10K, path="default Builder"),
        ),
        Scenario(
            name="execute-default-1k",
            description="execute the 1,000-node layered graph on the default path",
            metrics=WALL_AND_CPU,
            warmup=2,
            samples=10,
            prepare=lambda switch, workdir: ExecuteLayered(
                GRAPH_1K, lambda: builder(switch), workdir
            ),
            settings=_layered_settings(GRAPH_1K, path="default"),
        ),
        Scenario(
            name="execute-default-10k",
            description="execute the 10,000-node layered graph on the default path",
            metrics=WALL_AND_CPU,
            warmup=1,
            samples=5,
            prepare=lambda switch, workdir: ExecuteLayered(
                GRAPH_10K, lambda: builder(switch), workdir
            ),
            settings=_layered_settings(GRAPH_10K, path="default"),
        ),
        Scenario(
            name="execute-tasks-sync-1k",
            description=(
                "execute the 1,000-node layered graph on the task-based path with "
                "SynchronousLocalTaskExecutor as the local and the remote executor"
            ),
            metrics=WALL_AND_CPU,
            warmup=1,
            samples=5,
            prepare=lambda switch, workdir: ExecuteLayered(
                GRAPH_1K, lambda: synchronous_task_builder(switch), workdir
            ),
            settings=_layered_settings(
                GRAPH_1K,
                path="task-based",
                local_executor="SynchronousLocalTaskExecutor",
                remote_executor="SynchronousLocalTaskExecutor",
            ),
        ),
        Scenario(
            name="tiny-nodes",
            description=(
                f"per-execution overhead: {TINY_EXECUTES_PER_SAMPLE} executes of a "
                f"{GRAPH_TINY.node_count}-node graph of tiny nodes per sample, on the default path"
            ),
            metrics=("wall_per_execute_s", "main_thread_cpu_per_execute_s"),
            warmup=1,
            samples=10,
            prepare=TinyNodes,
            settings=_layered_settings(
                GRAPH_TINY, path="default", executes_per_sample=TINY_EXECUTES_PER_SAMPLE
            ),
        ),
        Scenario(
            name="cpu-sequential",
            description="the 32-kernel CPU workload, one node per item, on the default path",
            metrics=WALL_AND_CPU,
            warmup=1,
            samples=3,
            prepare=lambda switch, workdir: CpuGraph(
                CPU_WORKLOAD.sequential_source(),
                "bench_cpu_sequential",
                lambda: builder(switch),
                workdir,
            ),
            settings=_cpu_settings(CPU_WORKLOAD.sequential_source(), path="default"),
        ),
        Scenario(
            name="cpu-mapped-4",
            description=(
                "the 32-kernel CPU workload, expanded and collected, with four "
                "MultiThreadingExecutor workers on the task-based path"
            ),
            metrics=WALL_AND_CPU,
            warmup=1,
            samples=3,
            prepare=lambda switch, workdir: CpuGraph(
                CPU_WORKLOAD.mapped_source(),
                "bench_cpu_mapped",
                lambda: threaded_task_builder(switch, CPU_WORKERS),
                workdir,
            ),
            settings=_cpu_settings(
                CPU_WORKLOAD.mapped_source(),
                path="task-based",
                local_executor="SynchronousLocalTaskExecutor",
                remote_executor=f"MultiThreadingExecutor(max_tasks={CPU_WORKERS})",
            ),
        ),
        Scenario(
            name="cpu-threadpool-4",
            description=(
                "the 32-kernel CPU workload on a plain ThreadPoolExecutor with four workers, "
                "without Hamilton"
            ),
            metrics=WALL_AND_CPU,
            warmup=1,
            samples=3,
            prepare=CpuThreadPool,
            settings=_cpu_settings(
                CPU_WORKLOAD.sequential_source(), workers=CPU_WORKERS, pool="ThreadPoolExecutor"
            ),
            uses_hamilton=False,
        ),
    ]
}
