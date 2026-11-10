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

import os
import pathlib
import sys
import sysconfig
import uuid

import pytest

# Skip tests that require packages not yet available on Python 3.14+
collect_ignore = []
if sys.version_info >= (3, 14):
    collect_ignore.extend(
        [
            # xgboost - no Python 3.14 support yet
            "plugins/test_xgboost_extensions.py",
            # lightgbm - no Python 3.14 support yet
            "plugins/test_lightgbm_extensions.py",
            # mlflow - no Python 3.14 support yet
            "plugins/test_mlflow_extension.py",
            # kedro - no Python 3.14 support yet
            "plugins/test_h_kedro.py",
            "plugins/test_kedro_extensions.py",
            # lancedb - no Python 3.14 support yet
            "plugins/test_huggingface_extensions.py",
        ]
    )

# Tests that a free-threaded build cannot run, under the dependency that keeps them out. The
# free-threaded CI job installs the `test-free-threaded` dependency group, which leaves these
# dependencies out, and fails when anything it does import turns the GIL back on. An entry is a
# test module, or one test in it written as "module::test"; both are relative to this directory.
# The 3.14 list above holds on a free-threaded 3.14 build too, and so do the tests that skip
# themselves on every 3.14 build: plugins/test_h_mlflow.py (mlflow) and
# plugins/test_pandas_extensions.py::test_pandas_spss_reader (pyreadstat).
FREE_THREADED_SKIPS = {
    "dlt, whose dependency orjson refuses to build for a free-threaded interpreter": [
        "plugins/test_dlt_extensions.py",
    ],
    "polars, which publishes no wheel that a free-threaded interpreter can install": [
        "plugins/test_polars_extensions.py",
        "plugins/test_polars_lazyframe_extensions.py",
        "caching/test_fingerprinting.py::test_hash_polars_different_columns_differ",
        "caching/test_fingerprinting.py::test_hash_polars_same_schema_same_data_matches",
        "caching/test_fingerprinting.py::test_hash_polars_different_dtypes_differ",
    ],
    "lxml, which installs but turns the GIL back on when imported": [
        "plugins/test_pandas_extensions.py::test_pandas_xml_reader",
        "plugins/test_pandas_extensions.py::test_pandas_xml_writer",
        "plugins/test_pandas_extensions.py::test_pandas_html_reader",
    ],
}
# Tests that fail now and then on a free-threaded build because of a defect in Hamilton, not a
# missing dependency. They still run, and a failure is reported without failing the job. An entry
# is the start of a test's name, written as above with its parameters, and the defect behind it.
# Remove an entry with the fix for its defect.
FREE_THREADED_KNOWN_FAILURES = {
    "caching/test_integration.py::test_parallel_synchronous_step_by_step[MultiThreadingExecutor-": (
        "the cache adapter's per-run maps are written by mapped tasks on several threads without "
        "a lock, and an entry is sometimes lost"
    ),
}
_FREE_THREADED_BUILD = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
if _FREE_THREADED_BUILD:
    collect_ignore.extend(
        entry for entries in FREE_THREADED_SKIPS.values() for entry in entries if "::" not in entry
    )


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Applies ``FREE_THREADED_SKIPS`` and ``FREE_THREADED_KNOWN_FAILURES`` to single tests."""
    if not _FREE_THREADED_BUILD:
        return
    dependency_of = {
        entry: dependency
        for dependency, entries in FREE_THREADED_SKIPS.items()
        for entry in entries
        if "::" in entry
    }
    tests_dir = pathlib.Path(__file__).parent
    for item in items:
        if not item.path.is_relative_to(tests_dir):
            continue
        module = item.path.relative_to(tests_dir).as_posix()
        dependency = dependency_of.get(f"{module}::{getattr(item, 'originalname', item.name)}")
        if dependency is not None:
            item.add_marker(pytest.mark.skip(reason=f"free-threaded build: needs {dependency}"))
        for name_start, defect in FREE_THREADED_KNOWN_FAILURES.items():
            if f"{module}::{item.name}".startswith(name_start):
                item.add_marker(
                    pytest.mark.xfail(strict=False, reason=f"free-threaded build: {defect}")
                )


@pytest.fixture
def postgres_schema():
    """A throwaway schema on the PostgreSQL server named by ``HAMILTON_TEST_POSTGRES_URL``.

    Yields ``(engine, schema_name)``; skips when the variable is unset. Only that schema is
    created and it is dropped afterwards, so any server the variable points at stays clean.
    """
    url = os.environ.get("HAMILTON_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("HAMILTON_TEST_POSTGRES_URL not set")
    sqlalchemy = pytest.importorskip("sqlalchemy")
    engine = sqlalchemy.create_engine(url)
    schema = f"lineage_{uuid.uuid4().hex[:8]}"
    with engine.begin() as conn:
        conn.execute(sqlalchemy.text(f"CREATE SCHEMA {schema}"))
    try:
        yield engine, schema
    finally:
        with engine.begin() as conn:
            conn.execute(sqlalchemy.text(f"DROP SCHEMA {schema} CASCADE"))
        engine.dispose()
