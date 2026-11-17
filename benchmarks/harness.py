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

"""Measures Hamilton's build and execution paths; see benchmarks/README.md.

    python benchmarks/harness.py list
    python benchmarks/harness.py run --out result.json [--side SPEC]... [--scenario NAME]...
    python benchmarks/harness.py compare result.json [--baseline LABEL]
    python benchmarks/harness.py profile SCENARIO [--side SPEC]

A side is ``LABEL[:key=value,...]`` with the keys ``switch`` (``1x`` or ``new``; default ``1x``),
``python`` (an interpreter; default the one running this script) and ``checkout`` (a source tree
whose ``hamilton/`` package is measured; default the checkout holding this script). With two or
more sides, ``run`` alternates them round by round and compares them at the end.

This script imports only the standard library; Hamilton is imported by the worker processes.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime
import json
import os
import pathlib
import platform
import pstats
import statistics
import subprocess
import sys
import tempfile
from typing import Any

import scenarios

HERE = pathlib.Path(__file__).resolve().parent
REPOSITORY = HERE.parent
FROZEN_FILE = HERE / "frozen.json"
RESULT_FORMAT = "hamilton-benchmark-result/1"


class HarnessError(Exception):
    """A problem the user must fix before anything can be measured."""


@dataclasses.dataclass(frozen=True)
class Side:
    label: str
    switch: str
    python: str
    checkout: str

    @classmethod
    def parse(cls, spec: str) -> Side:
        label, _, rest = spec.partition(":")
        if not label:
            raise HarnessError(f"The side {spec!r} has no label")
        fields = {"switch": "1x", "python": sys.executable, "checkout": str(REPOSITORY)}
        for item in filter(None, rest.split(",")):
            key, sep, value = item.partition("=")
            if not sep or key not in fields:
                raise HarnessError(
                    f"Cannot read {item!r} in the side {spec!r}: the keys are "
                    f"{', '.join(fields)}, as key=value"
                )
            fields[key] = value
        if fields["switch"] not in scenarios.SWITCHES:
            raise HarnessError(
                f"The side {label!r} names the switch {fields['switch']!r}; "
                f"the sides of the switch are {', '.join(scenarios.SWITCHES)}"
            )
        checkout = os.path.realpath(os.path.expanduser(fields["checkout"]))
        if not os.path.isfile(os.path.join(checkout, "hamilton", "__init__.py")):
            raise HarnessError(f"The side {label!r}: {checkout} holds no hamilton/ package")
        python = os.path.expanduser(fields["python"])
        if not os.access(python, os.X_OK):
            raise HarnessError(f"The side {label!r}: {python} is not an executable interpreter")
        return cls(label=label, switch=fields["switch"], python=python, checkout=checkout)

    def environment(self) -> dict[str, str]:
        env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        env.update(
            PYTHONPATH=self.checkout,
            BENCHMARK_CHECKOUT=self.checkout,
            HAMILTON_TELEMETRY_ENABLED="false",
        )
        return env

    def worker(self, args: list[str]) -> dict[str, Any]:
        """Runs the worker in this side's interpreter and checkout and returns its result."""
        with tempfile.TemporaryDirectory(prefix="hamilton-benchmark-") as tmp:
            result_path = os.path.join(tmp, "result.json")
            completed = subprocess.run(
                [
                    self.python,
                    str(HERE / "worker.py"),
                    "--result",
                    result_path,
                    "--switch",
                    self.switch,
                    *args,
                ],
                cwd=tmp,
                env=self.environment(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            if not os.path.exists(result_path):
                raise HarnessError(
                    f"The worker for the side {self.label!r} failed with exit code "
                    f"{completed.returncode}:\n{completed.stdout}"
                )
            result = json.loads(pathlib.Path(result_path).read_text())
        if "error" in result:
            raise HarnessError(f"The side {self.label!r}: {result['error']}")
        return result


def git(checkout: str, *args: str) -> str | None:
    completed = subprocess.run(
        ["git", "-C", checkout, *args], capture_output=True, text=True, check=False
    )
    return completed.stdout.strip() if completed.returncode == 0 else None


def source_state(checkout: str, *paths: str) -> dict[str, Any]:
    """The commit of ``checkout`` and any uncommitted change under ``paths``."""
    changes = git(checkout, "status", "--porcelain", "--", *paths)
    state: dict[str, Any] = {
        "commit": git(checkout, "rev-parse", "HEAD"),
        "uncommitted_changes": changes.splitlines() if changes else [],
    }
    if changes:
        state["uncommitted_diff"] = git(checkout, "diff", "HEAD", "--", *paths)
    return state


def machine() -> dict[str, Any]:
    info: dict[str, Any] = {
        "system": platform.system(),
        "release": platform.release(),
        "architecture": platform.machine(),
        "logical_cpus": os.cpu_count(),
    }
    if hasattr(os, "sched_getaffinity"):
        info["usable_cpus"] = len(os.sched_getaffinity(0))
    cpuinfo = pathlib.Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text().splitlines():
            if line.startswith("model name"):
                info["cpu"] = line.split(":", 1)[1].strip()
                break
    meminfo = pathlib.Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text().splitlines():
            if line.startswith("MemTotal"):
                info["memory_gib"] = round(int(line.split()[1]) / 1024**2, 1)
                break
    if "cpu" not in info:
        info["cpu"] = platform.processor() or None
    return info


def load_average() -> float | None:
    return os.getloadavg()[0] if hasattr(os, "getloadavg") else None


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def frozen_fingerprints() -> dict[str, str]:
    return json.loads(FROZEN_FILE.read_text())


def summarize(rounds: list[list[float]]) -> dict[str, Any]:
    """The value a comparison uses, its noise floor, and the range of all samples.

    Each round is a fresh worker process. A round's value is its fastest sample: work that shares
    the machine only adds time, so the minimum is the round's least disturbed measurement. The
    side's value is the median of its rounds' values, and the noise floor is the spread between
    the rounds' values as a fraction of it: the run-to-run variation a gap must exceed to count.
    With five or more rounds the fastest and the slowest round are left out of the spread, so
    that one round disturbed from start to end does not hide every difference.
    """
    samples = [value for round_samples in rounds for value in round_samples]
    round_values = [min(round_samples) for round_samples in rounds]
    value = statistics.median(round_values)
    ordered = sorted(round_values)
    spread = ordered[1:-1] if len(ordered) >= 5 else ordered
    noise = (spread[-1] - spread[0]) / value if len(rounds) > 1 else None
    return {
        "value": value,
        "noise_floor": noise,
        "round_values": round_values,
        "n": len(samples),
        "min": min(samples),
        "median": statistics.median(samples),
        "max": max(samples),
    }


def verdict(gap: float, floor: float | None) -> str:
    if floor is None:
        return "no noise floor (one round)"
    if abs(gap) <= floor:
        return "no measurable difference"
    return "slower" if gap > 0 else "faster"


def comparisons(result: dict[str, Any], baseline: str | None) -> list[dict[str, Any]]:
    labels = [side["label"] for side in result["sides"]]
    if len(labels) < 2:
        raise HarnessError(
            "A comparison needs two sides measured alternately in one run; this file holds "
            f"{len(labels)}. A stored result file is a record, never one side of a comparison."
        )
    baseline = baseline or labels[0]
    if baseline not in labels:
        raise HarnessError(f"No side is labelled {baseline!r}; the sides are {labels}")
    rows = []
    for name, scenario in result["scenarios"].items():
        for metric in scenario["metrics"]:
            base = scenario["sides"][baseline]["summary"][metric]
            for label in labels:
                if label == baseline:
                    continue
                other = scenario["sides"][label]["summary"][metric]
                floors = [base["noise_floor"], other["noise_floor"]]
                floor = None if None in floors else max(floors)
                gap = other["value"] / base["value"] - 1
                rows.append(
                    {
                        "scenario": name,
                        "metric": metric,
                        "baseline": baseline,
                        "side": label,
                        "gap": gap,
                        "noise_floor": floor,
                        "verdict": verdict(gap, floor),
                    }
                )
    return rows


def seconds(value: float) -> str:
    for unit, scale in (("s", 1), ("ms", 1e-3), ("us", 1e-6)):
        if abs(value) >= scale:
            return f"{value / scale:.3g} {unit}"
    return f"{value / 1e-9:.3g} ns"


def percent(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def report(result: dict[str, Any]) -> str:
    lines = []
    for name, scenario in result["scenarios"].items():
        lines.append(f"{name}: {scenario['description']}")
        for label, side in scenario["sides"].items():
            for metric in scenario["metrics"]:
                s = side["summary"][metric]
                lines.append(
                    f"  {label:<12} {metric:<30} value {seconds(s['value']):>9}  "
                    f"noise floor {percent(s['noise_floor']):>6}  "
                    f"range {seconds(s['min'])} .. {seconds(s['max'])}  "
                    f"median {seconds(s['median'])}  n={s['n']}"
                )
    if len(result["sides"]) > 1:
        lines.append("")
        lines.append(compare_text(comparisons(result, None)))
    for warning in result.get("warnings", []):
        lines.append(f"WARNING: {warning}")
    return "\n".join(lines)


def compare_text(rows: list[dict[str, Any]]) -> str:
    lines = [f"{'scenario':<24} {'metric':<30} {'side vs baseline':<26} {'gap':>8} {'floor':>8}"]
    for row in rows:
        lines.append(
            f"{row['scenario']:<24} {row['metric']:<30} "
            f"{row['side'] + ' vs ' + row['baseline']:<26} {percent(row['gap']):>8} "
            f"{percent(row['noise_floor']):>8}  {row['verdict']}"
        )
    return "\n".join(lines)


def selected_scenarios(names: list[str] | None) -> list[scenarios.Scenario]:
    if not names:
        return list(scenarios.SCENARIOS.values())
    unknown = [name for name in names if name not in scenarios.SCENARIOS]
    if unknown:
        raise HarnessError(
            f"Unknown scenarios {unknown}; `python benchmarks/harness.py list` names them"
        )
    return [scenarios.SCENARIOS[name] for name in names]


def parse_sides(specs: list[str] | None) -> list[Side]:
    sides = [Side.parse(spec) for spec in specs or ["1x"]]
    labels = [side.label for side in sides]
    if len(set(labels)) != len(labels):
        raise HarnessError(f"Side labels must be unique: {labels}")
    return sides


def probe_sides(sides: list[Side]) -> list[dict[str, Any]]:
    """Checks every side can be measured, before any measurement, and describes it."""
    described = []
    for side in sides:
        info = side.worker(["probe"])
        described.append(
            {
                "label": side.label,
                "switch": side.switch,
                "checkout": source_state(side.checkout, "hamilton"),
                **info,
            }
        )
    return described


def command_run(args: argparse.Namespace) -> int:
    sides = parse_sides(args.side)
    chosen = selected_scenarios(args.scenario)
    out = pathlib.Path(args.out)
    if out.exists() and not args.force:
        raise HarnessError(f"{out} exists; pass --force to replace it")
    rounds = args.rounds if args.rounds is not None else scenarios.ROUNDS
    overridden = any(value is not None for value in (args.rounds, args.warmup, args.samples))
    frozen = frozen_fingerprints()

    result: dict[str, Any] = {
        "format": RESULT_FORMAT,
        "started_utc": now(),
        "note": args.note,
        "machine": machine(),
        "harness": {
            **source_state(str(REPOSITORY), "benchmarks", ":(exclude)benchmarks/results"),
            "rounds": rounds,
            "settings_overridden": overridden,
            "order": (
                "scenario by scenario; within a scenario, round by round, each side once per "
                "round in a fresh worker process, the order of the sides reversed every other "
                "round"
            ),
        },
        "sides": probe_sides(sides),
        "scenarios": {},
        "warnings": [],
    }
    if overridden:
        result["warnings"].append(
            "Run counts were overridden on the command line: this file is not a measurement "
            "with the frozen settings."
        )

    for scenario in chosen:
        warmup = args.warmup if args.warmup is not None else scenario.warmup
        samples = args.samples if args.samples is not None else scenario.samples
        per_side: dict[str, Any] = {side.label: {"rounds": []} for side in sides}
        for round_index in range(rounds):
            order = sides if round_index % 2 == 0 else sides[::-1]
            for side in order:
                load = load_average()
                outcome = side.worker(
                    [
                        "run",
                        "--scenario",
                        scenario.name,
                        "--warmup",
                        str(warmup),
                        "--samples",
                        str(samples),
                    ]
                )
                per_side[side.label]["rounds"].append({"load_average_1m": load, **outcome})
                primary = min(s[scenario.metrics[0]] for s in outcome["samples"])
                print(
                    f"[{scenario.name}] round {round_index + 1}/{rounds} {side.label}: "
                    f"{seconds(primary)} (load {load})",
                    file=sys.stderr,
                    flush=True,
                )
        for label, side_result in per_side.items():
            side_result["summary"] = {
                metric: summarize(
                    [[s[metric] for s in r["samples"]] for r in side_result["rounds"]]
                )
                for metric in scenario.metrics
            }
            gil_states = {r["gil_enabled_after_setup"] for r in side_result["rounds"]}
            description = next(s for s in result["sides"] if s["label"] == label)
            if description["python"]["free_threaded_build"] and True in gil_states:
                result["warnings"].append(
                    f"{scenario.name} on {label}: the GIL was enabled after setup on a "
                    "free-threaded build; the result describes a different interpreter"
                )
        result["scenarios"][scenario.name] = {
            "description": scenario.description,
            "fingerprint": scenario.fingerprint(),
            "frozen": frozen.get(scenario.name) == scenario.fingerprint(),
            "uses_hamilton": scenario.uses_hamilton,
            "metrics": list(scenario.metrics),
            "warmup": warmup,
            "samples_per_round": samples,
            "settings": scenario.settings,
            "sides": per_side,
        }

    result["finished_utc"] = now()
    if len(sides) > 1:
        result["comparison"] = comparisons(result, None)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n")
    print(report(result))
    print(f"\nWrote {out}")
    return 0


def command_compare(args: argparse.Namespace) -> int:
    result = json.loads(pathlib.Path(args.result).read_text())
    if result.get("format") != RESULT_FORMAT:
        raise HarnessError(f"{args.result} is not a result file of this harness")
    print(compare_text(comparisons(result, args.baseline)))
    for warning in result.get("warnings", []):
        print(f"WARNING: {warning}")
    return 0


def command_list(args: argparse.Namespace) -> int:
    frozen = frozen_fingerprints()
    for scenario in scenarios.SCENARIOS.values():
        state = "frozen" if frozen.get(scenario.name) == scenario.fingerprint() else "NOT FROZEN"
        print(f"{scenario.name:<24} {state:<10} {scenario.description}")
    return 0


def command_fingerprints(args: argparse.Namespace) -> int:
    fingerprints = {name: s.fingerprint() for name, s in scenarios.SCENARIOS.items()}
    print(json.dumps(fingerprints, indent=2))
    return 0


def command_profile(args: argparse.Namespace) -> int:
    (side,) = parse_sides([args.side])
    scenario = selected_scenarios([args.scenario])[0]
    probe_sides([side])
    with tempfile.TemporaryDirectory(prefix="hamilton-benchmark-") as tmp:
        path = args.out or os.path.join(tmp, "profile")
        side.worker(
            [
                "run",
                "--scenario",
                scenario.name,
                "--warmup",
                str(scenario.warmup),
                "--samples",
                str(scenario.samples),
                "--profile",
                path,
                "--profile-limit",
                str(args.limit),
            ]
        )
        if scenario.name == "import-driver":
            print(pathlib.Path(path).read_text())
        else:
            stats = pstats.Stats(path)
            stats.sort_stats(args.sort).print_stats(args.limit)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="measure scenarios and write a result file")
    run.add_argument("--out", required=True, help="the JSON result file to write")
    run.add_argument("--side", action="append", help="a side to measure; repeat for more")
    run.add_argument("--scenario", action="append", help="a scenario; default all")
    run.add_argument("--note", help="free text stored in the result, e.g. what else ran")
    run.add_argument("--force", action="store_true", help="replace an existing result file")
    run.add_argument("--rounds", type=int, help="override the frozen rounds (smoke runs only)")
    run.add_argument("--warmup", type=int, help="override the frozen warm-ups (smoke runs only)")
    run.add_argument("--samples", type=int, help="override the frozen samples (smoke runs only)")
    run.set_defaults(handler=command_run)

    compare = commands.add_parser("compare", help="compare the sides of one result file")
    compare.add_argument("result")
    compare.add_argument("--baseline", help="the side to compare against; default the first")
    compare.set_defaults(handler=command_compare)

    listing = commands.add_parser("list", help="list the scenarios and whether they are frozen")
    listing.set_defaults(handler=command_list)

    fingerprints = commands.add_parser(
        "fingerprints", help="print every scenario's settings fingerprint as JSON"
    )
    fingerprints.set_defaults(handler=command_fingerprints)

    profile = commands.add_parser("profile", help="profile one scenario on one side")
    profile.add_argument("scenario")
    profile.add_argument("--side", default="1x")
    profile.add_argument("--sort", default="cumulative", choices=["cumulative", "tottime"])
    profile.add_argument("--limit", type=int, default=30)
    profile.add_argument("--out", help="keep the profile (pstats, or text for import-driver)")
    profile.set_defaults(handler=command_profile)

    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except HarnessError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
