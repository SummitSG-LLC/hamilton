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

"""Runs one round of one scenario, or probes a side, in the side's interpreter and checkout.

``harness.py`` starts this script with the side's Python and ``PYTHONPATH`` set to the side's
checkout, and reads the result from the JSON file named by ``--result``. It is not meant to be run
by hand.
"""

from __future__ import annotations

import argparse
import cProfile
import gc
import importlib.metadata
import json
import os
import pathlib
import platform
import re
import subprocess
import sys
import sysconfig
import tempfile
from typing import Any

import scenarios


def gil_enabled() -> bool | None:
    """Whether the GIL is enabled now; None on a build without ``sys._is_gil_enabled``."""
    probe = getattr(sys, "_is_gil_enabled", None)
    return probe() if probe is not None else None


def imported_hamilton() -> str:
    """Imports ``hamilton.driver`` and fails unless it comes from the side's checkout."""
    import hamilton
    import hamilton.driver  # noqa: F401

    location = os.path.realpath(hamilton.__file__)
    checkout = os.environ["BENCHMARK_CHECKOUT"]
    if os.path.dirname(os.path.dirname(location)) != checkout:
        raise RuntimeError(
            f"hamilton was imported from {location}, not from the side's checkout {checkout}. "
            "An installed copy of Hamilton in the side's environment takes precedence; "
            "uninstall it there or point the side at that copy's checkout."
        )
    return location


def probe(switch: str) -> dict[str, Any]:
    imported_hamilton()
    from hamilton import version

    gil = gil_enabled()  # after the imports: an extension may have turned the GIL back on
    packages = {dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions()}
    info: dict[str, Any] = {
        "python": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "build": " ".join(sys.version.split()),
            "free_threaded_build": bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
            "gil_enabled_after_imports": gil,
            "recursion_limit": sys.getrecursionlimit(),
        },
        "hamilton_version": ".".join(str(part) for part in version.VERSION),
        "packages": dict(sorted(packages.items(), key=lambda item: item[0].lower())),
        "environment": {
            name: os.environ[name]
            for name in ("HAMILTON_TELEMETRY_ENABLED", "PYTHON_GIL", "PYTHONHASHSEED")
            if name in os.environ
        },
    }
    try:
        scenarios.check_switch(switch)
    except scenarios.SwitchUnavailable as error:
        info["error"] = str(error)
    return info


def import_profile(workdir: pathlib.Path, limit: int) -> str:
    """The modules that take longest to import with ``hamilton.driver``, from ``-X importtime``."""
    completed = subprocess.run(
        [sys.executable, "-P", "-X", "importtime", "-c", "import hamilton.driver"],
        cwd=workdir,
        capture_output=True,
        text=True,
        check=True,
    )
    rows = []
    for line in completed.stderr.splitlines():
        match = re.match(r"import time:\s+(\d+) \|\s+(\d+) \|(\s*)(\S+)", line)
        if match:
            rows.append((int(match.group(2)), int(match.group(1)), match.group(4)))
    rows.sort(reverse=True)
    lines = [f"{'cumulative ms':>14} {'self ms':>9}  module"]
    lines += [f"{cum / 1000:14.1f} {own / 1000:9.1f}  {name}" for cum, own, name in rows[:limit]]
    return "\n".join(lines)


def run(
    scenario: scenarios.Scenario,
    switch: str,
    warmup: int,
    samples: int,
    profile_path: str | None,
    profile_limit: int,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="hamilton-benchmark-") as tmp:
        workdir = pathlib.Path(tmp)
        if scenario.uses_hamilton:
            imported_hamilton()
        prepared = scenario.prepare(switch, workdir)
        gil = gil_enabled()
        # Every sample starts with a collected heap, outside its timing and its profile.
        for _ in range(warmup):
            gc.collect()
            prepared.sample()
        if warmup:
            prepared.check()
        if profile_path and scenario.name == "import-driver":
            pathlib.Path(profile_path).write_text(import_profile(workdir, profile_limit) + "\n")
        profiler = cProfile.Profile() if profile_path else None
        measured = []
        for _ in range(samples):
            gc.collect()
            if profiler is not None:
                profiler.enable()
            measured.append(prepared.sample())
            if profiler is not None:
                profiler.disable()
        prepared.check()
        if profiler is not None and scenario.name != "import-driver":
            profiler.dump_stats(profile_path)
    return {"samples": measured, "gil_enabled_after_setup": gil}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", required=True)
    parser.add_argument("--switch", required=True, choices=scenarios.SWITCHES)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("probe")
    run_parser = subcommands.add_parser("run")
    run_parser.add_argument("--scenario", required=True, choices=sorted(scenarios.SCENARIOS))
    run_parser.add_argument("--warmup", type=int, required=True)
    run_parser.add_argument("--samples", type=int, required=True)
    run_parser.add_argument("--profile")
    run_parser.add_argument("--profile-limit", type=int, default=30)
    args = parser.parse_args()

    try:
        if args.command == "probe":
            result = probe(args.switch)
        else:
            result = run(
                scenarios.SCENARIOS[args.scenario],
                args.switch,
                args.warmup,
                args.samples,
                args.profile,
                args.profile_limit,
            )
    except (scenarios.SwitchUnavailable, scenarios.ScenarioCheckFailed, RuntimeError) as error:
        result = {"error": f"{type(error).__name__}: {error}"}
    pathlib.Path(args.result).write_text(json.dumps(result))
    return 3 if "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
