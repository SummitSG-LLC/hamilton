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

# Migration to 2.0

This page says how to move code from Apache Hamilton 1.x to 2.0: for each change after which code that works on 1.90 fails, warns differently or returns a different result, what changed, who is affected, the code before and after, and the error or warning that tells you that you hit it. 2.0 is in development; its pre-releases add entries here as they make changes.

Most entries are APIs that 1.x deprecated and promised to remove in 2.0. Each of them now raises an error whose message names what to use instead and ends with a pointer to its section here, in this form:

```text
hamilton.lifecycle.PrintLnHook has been removed, as of hamilton version: 2.0.0. It was another name for PrintLn. Instead, you should be using: hamilton.lifecycle.PrintLn. For migration, see: the section "PrintLnHook" of "Migration to 2.0" (docs/migration-to-2.0.md in the Apache Hamilton repository).
```

A removed function, class or attribute raises `hamilton.dev_utils.deprecation.DeprecationError`; a removed module raises an `ImportError`. To find the code that needs a change before you upgrade, run it on 1.90 with the deprecation warnings turned into errors, for example `python -W error::FutureWarning -W error::DeprecationWarning`.

## Changes in 2.0

These changes apply to everyone who installs 2.0, whichever graph builder and runtime the Driver uses.

### `hamilton.__version__`

**What changed:** on a pre-release, `hamilton.__version__` has a fourth part: 2.0.0.dev0 reports `(2, 0, 0, "dev0")`. A release keeps three parts.

**Who is affected:** code that unpacks `hamilton.__version__` into exactly three names.

**Before:**

```python
major, minor, patch = hamilton.__version__
```

**After:**

```python
major, minor, patch = hamilton.__version__[:3]
```

**What you see:** `ValueError: too many values to unpack (expected 3)`.

### Telemetry functions

**What changed:** `hamilton.telemetry.disable_telemetry()` and `hamilton.telemetry.is_telemetry_enabled()` raise a `DeprecationError`. Hamilton no longer collects telemetry, so 1.89 and 1.90 kept both as no-ops that warned with a `FutureWarning`.

**Who is affected:** code that calls either function, often to switch telemetry off at start-up.

**Before:**

```python
from hamilton import telemetry

telemetry.disable_telemetry()
```

**After:** delete the call; there is nothing to switch off. The `HAMILTON_TELEMETRY_ENABLED` environment variable has no effect either.

**What you see:** `DeprecationError: telemetry.disable_telemetry() has been removed, as of hamilton version: 2.0.0. Telemetry has been removed from Hamilton, so there is nothing to switch off or check. Remove the call. ...`

### `Driver.raw_execute`

**What changed:** `Driver.raw_execute` raises a `DeprecationError`. It returned the outputs without building the result, so it did not work with every adapter, and it warned with a `FutureWarning` throughout 1.x. `hamilton_sdk`'s `Driver` no longer overrides it. `AsyncDriver.raw_execute` was never deprecated and still works.

**Who is affected:** code that calls `raw_execute` on a `Driver`, or on a `hamilton_sdk` `Driver`. This includes Apache Burr: the `Hamilton` action in `burr.integrations.hamilton` calls `raw_execute` in Burr 0.43.0, so that action fails with Hamilton 2.0 until Burr changes the call.

**Before:**

```python
dr = driver.Driver(config, my_module)
results = dr.raw_execute(["a", "b"], inputs={"x": 1})  # a dict
```

**After:** call `execute` on a Driver whose result builder returns a dict. A Driver from `driver.Builder()` returns a dict unless you give it another result builder.

```python
dr = driver.Builder().with_config(config).with_modules(my_module).build()
results = dr.execute(["a", "b"], inputs={"x": 1})  # a dict
```

To keep the `Driver` constructor, pass `adapter=base.SimplePythonGraphAdapter(base.DictResult())`.

**What you see:** `DeprecationError: Driver.raw_execute has been removed, as of hamilton version: 2.0.0. ... Instead, you should be using: Driver.execute. ...`

### `display_graph`

**What changed:** `Driver.execute(..., display_graph=True)` raises a `DeprecationError`. In 1.x it rendered the graph to `test-output/execute.gv`, opened it, and warned with a `DeprecationWarning`. The parameter stays so that existing calls passing `display_graph=False` keep working.

**Who is affected:** code that passes `display_graph=True` to `Driver.execute`. `AsyncDriver.execute` already refused it in 1.x and still does, with a `ValueError`.

**Before:**

```python
results = dr.execute(["a"], inputs={"x": 1}, display_graph=True)
```

**After:** draw the graph with `visualize_execution`, then execute.

```python
dr.visualize_execution(["a"], "execute.gv", {"view": True}, inputs={"x": 1})
results = dr.execute(["a"], inputs={"x": 1})
```

**What you see:** `DeprecationError: display_graph=True has been removed, as of hamilton version: 2.0.0. Executing no longer displays the graph. Instead, you should be using: visualize_execution(). ...`

### `FunctionGraph.get_impacted_nodes`

**What changed:** `FunctionGraph.get_impacted_nodes` raises a `DeprecationError`. It was another name for `get_downstream_nodes` and warned with a `DeprecationWarning`.

**Who is affected:** code that calls it on a `FunctionGraph`, such as `dr.graph.get_impacted_nodes(...)`.

**Before:**

```python
impacted = dr.graph.get_impacted_nodes(["a"])
```

**After:** the replacement takes the same arguments and returns the same nodes.

```python
impacted = dr.graph.get_downstream_nodes(["a"])
```

**What you see:** `DeprecationError: FunctionGraph.get_impacted_nodes has been removed, as of hamilton version: 2.0.0. ... Instead, you should be using: FunctionGraph.get_downstream_nodes. ...`

### `parametrized`, `parametrized_input` and `parameterized_inputs`

**What changed:** the decorators `@parametrized`, `@parametrized_input` and `@parameterized_inputs` raise a `DeprecationError` when your module applies them, so building a Driver from that module fails. They warned with a `FutureWarning` since 1.10. `@parameterize`, `@parameterize_values` and `@parameterize_sources` replace them.

**Who is affected:** modules that use any of the three.

**Before:**

```python
from hamilton.function_modifiers import parameterized_inputs, parametrized, parametrized_input


@parametrized(parameter="year", assigned_output={("year_2023", "The 2023 value"): 2023})
def year_value(year: int) -> int:
    return year


@parametrized_input(
    parameter="column", variable_inputs={"spend": ("spend_doubled", "Spend, doubled")}
)
def doubled(column: float) -> float:
    return column * 2


@parameterized_inputs(total={"first": "spend", "second": "signups"})
def summed(first: float, second: float) -> float:
    return first + second
```

**After:** `@parameterize_values` takes the same arguments as `@parametrized`. `@parameterize_sources` takes, for each output, a mapping of parameter to upstream node; it reads the documentation of each output from the docstring, in which `{parameter}` is replaced by the node it is given.

```python
from hamilton.function_modifiers import parameterize_sources, parameterize_values


@parameterize_values(parameter="year", assigned_output={("year_2023", "The 2023 value"): 2023})
def year_value(year: int) -> int:
    return year


@parameterize_sources(spend_doubled={"column": "spend"})
def doubled(column: float) -> float:
    """{column}, doubled"""
    return column * 2


@parameterize_sources(total={"first": "spend", "second": "signups"})
def summed(first: float, second: float) -> float:
    return first + second
```

**What you see:** `DeprecationError: @parametrized has been removed, as of hamilton version: 2.0.0. Three decorators replace the older parameterization decorators: @parameterize, @parameterize_values and @parameterize_sources. Instead, you should be using: @parameterize_values. ...`

### `dynamic_transform` and `model`

**What changed:** the decorators `@dynamic_transform` and `@model` raise a `DeprecationError` when your module applies them. They warned with a `FutureWarning` since 1.20. `@resolve` (and its shorthand `@resolve_from_config`) replaces them: it chooses any decorator from the config, where these could only apply a transform class. `hamilton.models.BaseModel` stays for code that subclasses it.

**Who is affected:** modules that use `@model` or `@dynamic_transform`.

**Before:** a node whose inputs and weights come from the config.

```python
import pandas as pd

from hamilton import models
from hamilton.function_modifiers import model


class LinearCombination(models.BaseModel):
    def get_dependents(self) -> list[str]:
        return list(self.config_parameters.keys())

    def predict(self, **columns: pd.Series) -> pd.Series:
        return sum(self.config_parameters[name] * column for name, column in columns.items())


@model(LinearCombination, "weights")
def score() -> pd.Series:
    pass
```

**After:** write the computation in the function, and let `@resolve_from_config` choose its inputs from the config when the graph is built. Like every resolver, it needs `hamilton.enable_power_user_mode` set to `True` in the config.

```python
import pandas as pd

from hamilton.function_modifiers import group, inject, resolve_from_config, source


@resolve_from_config(
    decorate_with=lambda weights: inject(columns=group(**{name: source(name) for name in weights}))
)
def score(columns: dict[str, pd.Series], weights: dict[str, float]) -> pd.Series:
    return sum(weights[name] * column for name, column in columns.items())
```

```python
dr = (
    driver.Builder()
    .with_modules(my_module)
    .with_config({"hamilton.enable_power_user_mode": True, "weights": {"a": 0.5, "b": 0.5}})
    .build()
)
```

**What you see:** `DeprecationError: @model has been removed, as of hamilton version: 2.0.0. @resolve replaces it: it chooses any decorator from the config, where this one could only apply a transform class. Instead, you should be using: @resolve. ...`

### `pipe`

**What changed:** the decorator `@pipe` raises a `DeprecationError` when your module applies it. It warned with a `FutureWarning` since 1.20. `@pipe_input` is the same decorator under a clearer name, beside its counterpart `@pipe_output`.

**Who is affected:** modules that use `@pipe`.

**Before:**

```python
from hamilton.function_modifiers import pipe, step


@pipe(step(_add_one), step(_double))
def result(raw: int) -> int:
    return raw
```

**After:** rename the decorator; its arguments stay the same.

```python
from hamilton.function_modifiers import pipe_input, step


@pipe_input(step(_add_one), step(_double))
def result(raw: int) -> int:
    return raw
```

**What you see:** `DeprecationError: @pipe has been removed, as of hamilton version: 2.0.0. @pipe_input is the same decorator under a clearer name, beside its counterpart @pipe_output. Instead, you should be using: @pipe_input. ...`

### `PrintLnHook`

**What changed:** reading `hamilton.lifecycle.PrintLnHook` raises a `DeprecationError`, and the name left `hamilton.lifecycle.__all__`. It was another name for `PrintLn`; 1.x said it would go in 2.0 in a comment only, without a warning. The error is a `DeprecationError` rather than an `AttributeError` so that `from hamilton.lifecycle import PrintLnHook` shows its message; one consequence is that `hasattr(hamilton.lifecycle, "PrintLnHook")` raises instead of returning `False`.

**Who is affected:** code that imports or reads `PrintLnHook`.

**Before:**

```python
from hamilton.lifecycle import PrintLnHook

dr = driver.Builder().with_modules(my_module).with_adapters(PrintLnHook()).build()
```

**After:**

```python
from hamilton.lifecycle import PrintLn

dr = driver.Builder().with_modules(my_module).with_adapters(PrintLn()).build()
```

**What you see:** `DeprecationError: hamilton.lifecycle.PrintLnHook has been removed, as of hamilton version: 2.0.0. It was another name for PrintLn. Instead, you should be using: hamilton.lifecycle.PrintLn. ...`

### `hamilton.function_modifiers_base`

**What changed:** importing `hamilton.function_modifiers_base` raises an `ImportError`. It re-exported `hamilton.function_modifiers.base`, which is not a public API either, and warned with a `FutureWarning` on import.

**Who is affected:** code that imports the module, usually to write a custom decorator.

**Before:**

```python
from hamilton import function_modifiers_base

class my_decorator(function_modifiers_base.NodeTransformer): ...
```

**After:**

```python
from hamilton.function_modifiers import base

class my_decorator(base.NodeTransformer): ...
```

**What you see:** `ImportError: hamilton.function_modifiers_base has been removed, as of hamilton version: 2.0.0. ... Instead, you should be using: hamilton.function_modifiers.base. ...`

### `hamilton.experimental.h_async`

**What changed:** importing `hamilton.experimental.h_async` raises an `ImportError`. Async support left the experimental package; `hamilton.async_driver` holds the same `AsyncDriver`, and the module warned with a `FutureWarning` on import.

**Who is affected:** code that imports `AsyncDriver` from the experimental module.

**Before:**

```python
from hamilton.experimental import h_async

dr = h_async.AsyncDriver({}, my_module)
```

**After:**

```python
from hamilton import async_driver

dr = async_driver.AsyncDriver({}, my_module)
```

**What you see:** `ImportError: hamilton.experimental.h_async has been removed, as of hamilton version: 2.0.0. ... Instead, you should be using: hamilton.async_driver. ...`

### `hamilton.experimental.h_cache`

**What changed:** importing `hamilton.experimental.h_cache` raises an `ImportError`, so its `CachingGraphAdapter` and its readers and writers (`read_parquet`, `write_json` and the others) are gone. It warned with a `FutureWarning` on import. The caching built into the Driver replaces it, though not one-to-one: it decides what to recompute from the code and data versions of each node rather than from a list of nodes and a file format per type.

**Who is affected:** code that uses `CachingGraphAdapter` or the module's readers and writers.

**Before:**

```python
from hamilton import base, driver
from hamilton.experimental import h_cache

adapter = h_cache.CachingGraphAdapter("./cache", base.PandasDataFrameResult())
dr = driver.Driver({}, my_module, adapter=adapter)
```

**After:** turn caching on when you build the Driver. See [Caching](concepts/caching.rst) for what it stores and how to choose which nodes it caches.

```python
from hamilton import driver

dr = driver.Builder().with_modules(my_module).with_cache(path="./cache").build()
```

**What you see:** `ImportError: hamilton.experimental.h_cache has been removed, as of hamilton version: 2.0.0. ... Instead, you should be using: Builder.with_cache(). ...`

### `CacheAdapter`

**What changed:** constructing `hamilton.lifecycle.default.CacheAdapter` raises a `DeprecationError`. It warned with a `FutureWarning`. The caching built into the Driver replaces it, though not one-to-one. This is the adapter that stored results in a `shelve` file; the caching package `hamilton.caching` is a different thing and stays. Its class attributes went with it: `CacheAdapter.create_key` and `CacheAdapter.nodes_history_key` raise an `AttributeError`.

**Who is affected:** code that constructs `CacheAdapter`.

**Before:**

```python
from hamilton.lifecycle import default

dr = driver.Builder().with_modules(my_module).with_adapters(default.CacheAdapter()).build()
```

**After:**

```python
dr = driver.Builder().with_modules(my_module).with_cache().build()
```

**What you see:** `DeprecationError: hamilton.lifecycle.default.CacheAdapter has been removed, as of hamilton version: 2.0.0. The caching built into the Driver replaces it, though not one-to-one. Instead, you should be using: Builder.with_cache(). ...`

### `DiskCacheAdapter`

**What changed:** constructing `hamilton.plugins.h_diskcache.DiskCacheAdapter` raises a `DeprecationError`, and so does `evict_all_except_driver`, which needed one on the Driver. The adapter warned with a `FutureWarning`. `evict_all_except` stays: it still prunes a cache directory that the adapter wrote. `DiskCacheAdapter.nodes_history_key` and the module constant `MAX_KWARGS_REPR_LENGTH` went with the adapter and raise an `AttributeError`; the key the adapter used is `h_diskcache.NODES_HISTORY_KEY`.

**Who is affected:** code that constructs `DiskCacheAdapter` or calls `evict_all_except_driver`.

**Before:**

```python
from hamilton.plugins import h_diskcache

dr = (
    driver.Builder()
    .with_modules(my_module)
    .with_adapters(h_diskcache.DiskCacheAdapter(cache_path="./cache"))
    .build()
)
h_diskcache.evict_all_except_driver(dr)
```

**After:**

```python
dr = driver.Builder().with_modules(my_module).with_cache(path="./cache").build()
```

To prune a directory that `DiskCacheAdapter` wrote, call `h_diskcache.evict_all_except(nodes_to_keep=dr.graph.nodes, cache=diskcache.Cache("./cache"))`.

**What you see:** `DeprecationError: hamilton.plugins.h_diskcache.DiskCacheAdapter has been removed, as of hamilton version: 2.0.0. ... Instead, you should be using: Builder.with_cache(). ...`

### Polars older than 1.0

**What changed:** Hamilton's polars integration needs polars 1.0.0 or newer; the integration for older polars is gone. With an older polars installed, `hamilton.plugins.polars_extensions` logs a warning and raises an `ImportError` when imported. Hamilton loads its extensions when it is imported, skips one whose import fails, and runs without polars support, so the warning in the log is how you learn of it; importing `hamilton.plugins.h_polars` raises the error. 1.x logged a warning that support would stop in 2.0.

**Who is affected:** environments with polars older than 1.0.0 that use Hamilton's polars support.

**Before:** `pip install "polars<1"`

**After:** `pip install "polars>=1.0.0"`

**What you see:** `ImportError: Support for polars older than 1.0.0 (you have 0.20.31) has been removed, as of hamilton version: 2.0.0. Hamilton's polars integration needs polars 1.0.0 or newer. Instead, you should be using: polars>=1.0.0. ...`, and the same text in a warning in the log.

## When the new compiler and runtime become the default

This section will list the changes that apply only when the Driver builds graphs with the new compiler and runs them on the new runtime, which 2.0 makes available behind a switch before making it the default. There are no entries yet.
