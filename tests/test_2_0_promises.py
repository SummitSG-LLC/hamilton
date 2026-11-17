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

"""Every promise the 1.x line made for 2.0 is in the ledger of tests/promises_for_2_0.py, and each one
that took effect raises an error naming its replacement and its section of docs/migration-to-2.0.md."""

import importlib
import pathlib
import re
import subprocess
import sys
from collections.abc import Callable

import pytest

import hamilton
from hamilton.dev_utils import deprecation

from tests.promises_for_2_0 import LEDGER, Promise, prose_promises, scan


def _ledger_promises(in_source: bool) -> list[Promise]:
    return [entry.promise for entry in LEDGER if entry.in_source == in_source]


def test_the_ledger_holds_every_promise_for_2_0_in_the_source():
    """A promise the ledger lacks fails here: decide what 2.0 does with it and record it in LEDGER, and
    give each change its migration instructions in docs/migration-to-2.0.md."""
    found = scan(pathlib.Path(hamilton.__file__).parent)
    assert sorted(map(str, found)) == sorted(map(str, _ledger_promises(in_source=True)))


def test_the_ledger_lists_each_promise_once():
    promises = [entry.promise for entry in LEDGER]
    assert len(promises) == len(set(promises))


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("# this will be removed in Hamilton 2.0", True),
        ("x = 'It will be removed in the 2.0.0 release.'", True),
        ("x = 'will be removed in a 2.0 release'", True),
        ("# alias -- this will be removed in 2.0", True),
        ("x = '''warns from 1.20.0 and fails from 2.0.0.'''", True),
        ("# TODO(2.0): revisit", True),
        ("x = 'the default will change in a future major release'", True),
        ("x = f'has been removed, as of hamilton version: {version}'", False),
        ("# polars 2.0.0 removed the argument", False),
        ("# requires pandas>=2.0", False),
        ("removed_in_2_0 = 1  # in 2.0 terms, a name only", True),
        ("removed_in_2_0 = 1", False),
    ],
)
def test_the_prose_scan_finds_promises_in_comments_and_strings_only(source, expected):
    assert bool(prose_promises("module.py", source)) is expected


def _scan_source(tmp_path: pathlib.Path, source: str) -> list[Promise]:
    package = tmp_path / "hamilton"
    package.mkdir()
    (package / "module.py").write_text(source)
    return scan(package)


@pytest.mark.parametrize(
    ("fail_starting", "expected"),
    [("(2, 0, 0)", True), ("(3, 0, 0)", False), ("FAIL_AT", True)],
    ids=["due", "not-yet-due", "unreadable"],
)
def test_the_decorator_scan_finds_deprecations_the_current_version_fails(
    tmp_path, fail_starting, expected
):
    source = (
        "from hamilton.dev_utils import deprecation\n"
        "@deprecation.deprecated(\n"
        f"    warn_starting=(1, 0, 0), fail_starting={fail_starting}, use_this=None,\n"
        "    explanation='', migration_guide='',\n"
        ")\n"
        "def old(): ...\n"
    )
    found = _scan_source(tmp_path, source)
    assert found == ([Promise("hamilton/module.py", "@deprecated old")] if expected else [])


# Each promise that took effect, exercised: the call that a 1.x user would make, the error it raises
# now, the replacement the error names, and the migration section it points to. The expected values
# are written out here, not read from hamilton, so a wrong message fails.
def _construct(module: str, name: str, *args, **kwargs) -> Callable[[], object]:
    return lambda: getattr(importlib.import_module(module), name)(*args, **kwargs)


def _driver():
    from hamilton import ad_hoc_utils, driver

    def a() -> int:
        return 1

    return driver.Builder().with_modules(ad_hoc_utils.create_temporary_module(a)).build()


def _read_print_ln_hook():
    from hamilton import lifecycle

    return lifecycle.PrintLnHook


def _import_print_ln_hook():
    from hamilton.lifecycle import PrintLnHook  # noqa: F401


def _guide(section: str) -> str:
    return (
        f'For migration, see: the section "{section}" of "Migration to 2.0" '
        "(docs/migration-to-2.0.md in the Apache Hamilton repository)."
    )


_REMOVED_NAMES = {
    "telemetry.disable_telemetry": (
        _construct("hamilton.telemetry", "disable_telemetry"),
        None,
        "Telemetry functions",
    ),
    "telemetry.is_telemetry_enabled": (
        _construct("hamilton.telemetry", "is_telemetry_enabled"),
        None,
        "Telemetry functions",
    ),
    "Driver.raw_execute": (
        lambda: _driver().raw_execute(["a"]),
        "Driver.execute",
        "Driver.raw_execute",
    ),
    "display_graph=True": (
        lambda: _driver().execute(["a"], display_graph=True),
        "visualize_execution()",
        "display_graph",
    ),
    "FunctionGraph.get_impacted_nodes": (
        lambda: _driver().graph.get_impacted_nodes(["a"]),
        "FunctionGraph.get_downstream_nodes",
        "FunctionGraph.get_impacted_nodes",
    ),
    "parametrized": (
        _construct("hamilton.function_modifiers", "parametrized", "x", {("y", "doc"): 1}),
        "@parameterize_values",
        "parametrized, parametrized_input and parameterized_inputs",
    ),
    "parametrized_input": (
        _construct("hamilton.function_modifiers", "parametrized_input", "x", {"y": ("z", "doc")}),
        "@parameterize_sources",
        "parametrized, parametrized_input and parameterized_inputs",
    ),
    "parameterized_inputs": (
        _construct("hamilton.function_modifiers", "parameterized_inputs", z={"x": "y"}),
        "@parameterize_sources",
        "parametrized, parametrized_input and parameterized_inputs",
    ),
    "dynamic_transform": (
        _construct("hamilton.function_modifiers", "dynamic_transform", object, "params"),
        "@resolve",
        "dynamic_transform and model",
    ),
    "model": (
        _construct("hamilton.function_modifiers", "model", object, "params"),
        "@resolve",
        "dynamic_transform and model",
    ),
    "pipe": (
        _construct("hamilton.function_modifiers", "pipe"),
        "@pipe_input",
        "pipe",
    ),
    "PrintLnHook read": (_read_print_ln_hook, "hamilton.lifecycle.PrintLn", "PrintLnHook"),
    "PrintLnHook import": (_import_print_ln_hook, "hamilton.lifecycle.PrintLn", "PrintLnHook"),
    "CacheAdapter": (
        _construct("hamilton.lifecycle.default", "CacheAdapter", cache_path="cache"),
        "Builder.with_cache()",
        "CacheAdapter",
    ),
}


@pytest.mark.parametrize(
    ("call", "use_this", "section"), _REMOVED_NAMES.values(), ids=list(_REMOVED_NAMES)
)
def test_removed_name_raises_naming_its_replacement_and_migration_section(call, use_this, section):
    with pytest.raises(deprecation.DeprecationError) as error:
        call()
    message = str(error.value)
    assert "has been removed, as of hamilton version: 2.0.0." in message
    if use_this is not None:
        assert f"Instead, you should be using: {use_this}." in message
    assert message.endswith(_guide(section))


def test_removed_disk_cache_adapter_raises_naming_its_replacement(tmp_path):
    h_diskcache = pytest.importorskip("hamilton.plugins.h_diskcache")
    for call in (
        lambda: h_diskcache.DiskCacheAdapter(cache_path=str(tmp_path)),
        lambda: h_diskcache.evict_all_except_driver(_driver()),
    ):
        with pytest.raises(deprecation.DeprecationError) as error:
            call()
        assert "Instead, you should be using: Builder.with_cache()." in str(error.value)
        assert str(error.value).endswith(_guide("DiskCacheAdapter"))


@pytest.mark.parametrize(
    ("module", "use_this"),
    [
        ("hamilton.function_modifiers_base", "hamilton.function_modifiers.base"),
        ("hamilton.experimental.h_async", "hamilton.async_driver"),
        ("hamilton.experimental.h_cache", "Builder.with_cache()"),
    ],
)
def test_removed_module_raises_an_import_error_naming_its_replacement(module, use_this):
    # A fresh interpreter, so the module is imported here and not found in sys.modules.
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"], capture_output=True, text=True
    )
    assert result.returncode != 0
    last_line = result.stderr.strip().splitlines()[-1]
    assert last_line.startswith(f"ImportError: {module} has been removed")
    assert f"Instead, you should be using: {use_this}." in last_line
    assert last_line.endswith(_guide(module))


def test_polars_older_than_1_0_raises_an_import_error_naming_the_minimum():
    pytest.importorskip("polars")
    # A fresh interpreter whose polars reports an old version before the extension reads it.
    program = (
        "import polars\npolars.__version__ = '0.20.31'\nimport hamilton.plugins.polars_extensions\n"
    )
    result = subprocess.run([sys.executable, "-c", program], capture_output=True, text=True)
    assert result.returncode != 0
    last_line = result.stderr.strip().splitlines()[-1]
    assert last_line.startswith(
        "ImportError: Support for polars older than 1.0.0 (you have 0.20.31) has been removed"
    )
    assert "Instead, you should be using: polars>=1.0.0." in last_line
    assert last_line.endswith(_guide("Polars older than 1.0"))


def _migration_sections() -> set[str]:
    guide = pathlib.Path(__file__).parents[1] / "docs" / "migration-to-2.0.md"
    return {
        line.lstrip("#").strip().replace("`", "")
        for line in guide.read_text().splitlines()
        if line.startswith("### ")
    }


def test_every_migration_section_an_error_names_exists():
    named = {section for _, _, section in _REMOVED_NAMES.values()} | {
        "DiskCacheAdapter",
        "hamilton.function_modifiers_base",
        "hamilton.experimental.h_async",
        "hamilton.experimental.h_cache",
        "Polars older than 1.0",
    }
    package = pathlib.Path(hamilton.__file__).parent
    in_source = set()
    for path in package.rglob("*.py"):
        in_source |= set(re.findall(r'section="([^"]+)"', path.read_text()))
        in_source |= set(re.findall(r'migration_to_2_0\(\s*"([^"]+)"', path.read_text()))
    assert named <= in_source
    assert in_source <= _migration_sections()
