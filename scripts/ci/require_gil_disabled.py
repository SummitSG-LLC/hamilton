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

"""Pytest plugin that fails a test run in which the GIL is, or becomes, enabled.

A free-threaded CPython build turns the GIL back on when it imports an extension module that
has not declared itself safe to run without it, and from then on the run proves nothing about
free-threading while every test still passes. The free-threaded CI job loads this plugin so
that such a run fails instead:

    PYTHONPATH=scripts/ci pytest -p require_gil_disabled tests/

The GIL is checked when the session starts, which catches an interpreter that is not a
free-threaded build or was started with ``PYTHON_GIL=1`` or ``-X gil=1``, and again when it
ends, after every import the suite makes.
"""

import sys
import warnings

import pytest

# CPython's RuntimeWarning for the import that turned the GIL on; it names the module.
_GIL_WARNING_MARKER = "global interpreter lock (GIL) has been enabled"

_gil_warnings: list[str] = []


def _gil_enabled() -> bool:
    # sys._is_gil_enabled() exists from Python 3.13; an older interpreter always has the GIL.
    is_gil_enabled = getattr(sys, "_is_gil_enabled", None)
    return True if is_gil_enabled is None else is_gil_enabled()


def pytest_sessionstart(session: pytest.Session) -> None:
    if _gil_enabled():
        pytest.exit(
            "require_gil_disabled: the GIL is enabled before any test module is imported. "
            f"Run on a free-threaded build without PYTHON_GIL=1 or -X gil=1 (got {sys.version}).",
            returncode=pytest.ExitCode.USAGE_ERROR,
        )


def pytest_warning_recorded(warning_message: warnings.WarningMessage, nodeid: str) -> None:
    message = str(warning_message.message)
    if _GIL_WARNING_MARKER in message:
        _gil_warnings.append(f"{nodeid or 'during collection'}: {message}")


def pytest_sessionfinish(session: pytest.Session) -> None:
    if _gil_enabled() and session.exitstatus == pytest.ExitCode.OK:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    if not _gil_enabled():
        terminalreporter.write_line("require_gil_disabled: the GIL stayed disabled for the run.")
        return
    terminalreporter.section("GIL enabled during the run", sep="=", red=True, bold=True)
    terminalreporter.write_line(
        "sys._is_gil_enabled() is true after the suite's imports: an extension module that is "
        "not free-threading-safe was imported. Remove it from the free-threaded job's "
        "dependencies and list the tests that need it in tests/conftest.py."
    )
    for line in _gil_warnings or ["(no import warning was recorded; rerun with -W error)"]:
        terminalreporter.write_line(f"  {line}")
