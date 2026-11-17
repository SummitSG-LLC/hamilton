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

"""Checks the benchmark harness for correctness only: no test here asserts a timing."""

import json
import pathlib
import subprocess
import sys
import sysconfig

import fixtures
import harness
import pytest
import scenarios

HARNESS = pathlib.Path(harness.__file__)


def evaluate_generated(graph: fixtures.LayeredGraph, x: int) -> dict[str, int]:
    """Runs the generated functions in plain Python, layer by layer, without Hamilton."""
    namespace: dict = {}
    exec(compile(graph.source(), "<generated>", "exec"), namespace)
    values: dict[str, int] = {}
    for i in range(graph.layers):
        for j in range(graph.width):
            function = namespace[graph.name(i, j)]
            if i == 0:
                values[graph.name(i, j)] = function(x)
            else:
                deps = [graph.name(i - 1, d) for d in graph.dependencies(i, j)]
                values[graph.name(i, j)] = function(**{d: values[d] for d in deps})
    return {name: values[name] for name in graph.final_nodes()}


def test_layered_oracle_matches_hand_computed_values():
    # Layer 0: n0_0 = 7 * 1 + 0 = 7 and n0_1 = 7 * 2 + 1 = 15.
    # n1_0 depends on n0_0 and n0_1: 1 * 7 + 2 * 15 + 0 = 37. n1_1 depends on n0_1: 15 + 1 = 16.
    graph = fixtures.LayeredGraph(layers=2, width=2)
    assert graph.dependencies(1, 0) == (0, 1)
    assert graph.dependencies(1, 1) == (1,)
    assert graph.oracle(7) == {"n1_0": 37, "n1_1": 16}


@pytest.mark.parametrize(
    "graph",
    [
        fixtures.LayeredGraph(layers=1, width=1),
        fixtures.LayeredGraph(layers=7, width=1),
        fixtures.LayeredGraph(layers=6, width=3),
        scenarios.GRAPH_TINY,
        scenarios.GRAPH_1K,
    ],
    ids=str,
)
def test_generated_layered_source_agrees_with_oracle(graph):
    assert evaluate_generated(graph, scenarios.GRAPH_INPUT) == graph.oracle(scenarios.GRAPH_INPUT)


@pytest.mark.parametrize("graph", [scenarios.GRAPH_1K, scenarios.GRAPH_10K], ids=str)
def test_layered_graph_shape(graph):
    """Each node depends on one to three nodes of the previous layer, its own index included."""
    for i in range(1, graph.layers):
        for j in range(graph.width):
            deps = graph.dependencies(i, j)
            assert 1 <= len(deps) <= 3
            assert deps[0] == j
            assert len(set(deps)) == len(deps)
            assert all(0 <= d < graph.width for d in deps)
    counts = [
        len(graph.dependencies(i, j)) for i in range(1, graph.layers) for j in range(graph.width)
    ]
    assert {1, 2, 3} <= set(counts)
    assert graph.node_count in (1_000, 10_000)


@pytest.mark.parametrize("item", [0, 1, 37, 255, 256, 1_000])
@pytest.mark.parametrize("iterations", [0, 1, 255, 256, 257, 1_000])
def test_kernel_reference_matches_kernel(item, iterations):
    namespace: dict = {}
    exec(fixtures.KERNEL_SOURCE, namespace)
    assert namespace["_kernel"](item, iterations) == fixtures.kernel_reference(item, iterations)


def test_sequential_cpu_source_agrees_with_oracle():
    workload = fixtures.CpuWorkload(items=(3, 5, 300), iterations=777)
    namespace: dict = {}
    exec(workload.sequential_source(), namespace)
    outputs = {f"item_{i}": namespace[f"item_{i}"](workload.iterations) for i in workload.items}
    assert namespace["results"](**outputs) == workload.oracle()


def test_mapped_cpu_source_agrees_with_oracle():
    workload = fixtures.CpuWorkload(items=(3, 5, 300), iterations=777)
    namespace: dict = {}
    exec(workload.mapped_source(), namespace)
    outputs = [namespace["kernel_output"](i, workload.iterations) for i in namespace["item_id"]()]
    assert namespace["results"](outputs) == workload.oracle()


def test_cpu_workload_rejects_repeated_items():
    with pytest.raises(ValueError, match="distinct"):
        fixtures.CpuWorkload(items=(1, 1), iterations=1)


def test_frozen_scenarios_are_unchanged():
    """A frozen scenario's settings change only with a deliberate edit of frozen.json."""
    frozen = json.loads((HARNESS.parent / "frozen.json").read_text())
    current = {name: scenario.fingerprint() for name, scenario in scenarios.SCENARIOS.items()}
    assert current == frozen


def test_new_side_is_refused_before_anything_is_measured(tmp_path, capsys):
    out = tmp_path / "result.json"
    code = harness.main(["run", "--out", str(out), "--side", "new:switch=new"])
    assert code == 2
    assert "Ticket 07" in capsys.readouterr().err
    assert not out.exists()


@pytest.mark.parametrize(
    "spec",
    [
        "a:switch=2x",
        "a:colour=blue",
        "a:switch",
        ":switch=1x",
        "a:checkout=/nonexistent-checkout",
        "a:python=/nonexistent-python",
    ],
)
def test_bad_side_specs_are_reported(spec):
    with pytest.raises(harness.HarnessError):
        harness.Side.parse(spec)


def synthetic_result(minima_a, minima_b) -> dict:
    """Two sides whose rounds have the given fastest samples, plus slower ones that must not count."""

    def side(minima):
        rounds = [[m * 1.3, m, m * 2.0] for m in minima]
        return {"summary": {"wall_s": harness.summarize(rounds)}}

    return {
        "sides": [{"label": "a"}, {"label": "b"}],
        "scenarios": {
            "s": {"metrics": ["wall_s"], "sides": {"a": side(minima_a), "b": side(minima_b)}}
        },
    }


def test_summary_uses_the_fastest_sample_of_each_round():
    summary = harness.summarize([[3.0, 2.0, 2.5], [2.2, 9.0, 2.4], [1.9, 2.0, 5.0]])
    assert summary["round_values"] == [2.0, 2.2, 1.9]
    assert summary["value"] == 2.0
    assert summary["noise_floor"] == pytest.approx((2.2 - 1.9) / 2.0)
    assert (summary["min"], summary["median"], summary["max"], summary["n"]) == (
        1.9,
        2.4,
        9.0,
        9,
    )


def test_noise_floor_leaves_out_the_extreme_rounds_from_five_rounds_on():
    # Round values 1.0, 1.1, 1.2, 1.3 and one disturbed round at 3.0: the spread is 1.3 - 1.1.
    summary = harness.summarize([[1.2], [3.0], [1.0], [1.1], [1.3]])
    assert summary["value"] == 1.2
    assert summary["noise_floor"] == pytest.approx((1.3 - 1.1) / 1.2)


@pytest.mark.parametrize(
    ("minima_b", "expected"),
    [
        ([1.0, 1.05, 0.95], "no measurable difference"),  # 0% gap, 10% floor
        ([1.08, 1.0, 1.0], "no measurable difference"),  # gap inside the floor
        ([1.5, 1.55, 1.45], "slower"),
        ([0.5, 0.52, 0.48], "faster"),
    ],
)
def test_verdict_compares_gap_with_the_larger_noise_floor(minima_b, expected):
    result = synthetic_result([1.0, 1.05, 0.95], minima_b)
    (row,) = harness.comparisons(result, None)
    assert row["noise_floor"] == pytest.approx(0.1)
    assert row["verdict"] == expected


def test_one_round_gives_no_verdict():
    result = synthetic_result([1.0], [2.0])
    (row,) = harness.comparisons(result, None)
    assert row["verdict"] == "no noise floor (one round)"


def test_a_file_with_one_side_is_not_compared():
    result = {"sides": [{"label": "a"}], "scenarios": {}}
    with pytest.raises(harness.HarnessError, match="never one side of a comparison"):
        harness.comparisons(result, None)


def test_every_scenario_runs_and_matches_its_oracle(tmp_path):
    """One sample of every scenario on this checkout; a wrong output fails the worker."""
    out = tmp_path / "result.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(HARNESS),
            "run",
            "--out",
            str(out),
            "--rounds",
            "1",
            "--warmup",
            "0",
            "--samples",
            "1",
        ],
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    result = json.loads(out.read_text())
    assert set(result["scenarios"]) == set(scenarios.SCENARIOS)
    assert result["harness"]["settings_overridden"] is True
    (side,) = result["sides"]
    assert side["switch"] == "1x"
    for name, scenario in result["scenarios"].items():
        (round_,) = scenario["sides"]["1x"]["rounds"]
        (sample,) = round_["samples"]
        assert set(sample) == set(scenarios.SCENARIOS[name].metrics)
        if sysconfig.get_config_var("Py_GIL_DISABLED"):
            assert round_["gil_enabled_after_setup"] is False, name
