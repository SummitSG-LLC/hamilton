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

# Survey: plugin discovery and the provider split

Two questions from the 2.0 outline (apache/hamilton discussion #1645, "Hamilton 2.0: Architecture and Roadmap Reassessment"). First, which rules Hamilton should use to discover and load integrations through entry points: what happens when two plugins claim one name, how a plugin and the core state and check compatibility, and how a plugin is loaded only when used. Second, which of Hamilton's integrations earn their own distribution and which stay an extra of `apache-hamilton`. This report compares pytest, Apache Airflow's providers and OpenStack stevedore, measures Hamilton's own integrations, and ends in a proposal and the decisions the owner must make. It changes no code. The decisions it asks for are recorded in ADR 2611-17, which stays Proposed until the owner decides.

Written 2026-11-17 against branch `2.0` at `31b3a832` of the fork `SummitSG-LLC/hamilton`, whose code under `hamilton/` is that of `upstream/main` at `077b7a1d` plus two fixes in `hamilton/caching/adapter.py` and `hamilton/node.py` (`e6bebcd1`, `716969b4`), neither of which touches the integrations. Line references to Hamilton files are at that commit.

## The answer in one minute

- **Discovery.** Replace the eager walk over a fixed list with entry points that point to a static manifest per extension, and load an extension only when a graph needs it: when a materializer name it declares is resolved for a type it declares, when a value or annotation of a type from its library reaches a registry lookup, or when the user asks for it. The manifest, not the import, answers "which extensions exist and what do they provide". This is Airflow's model (a metadata callable per provider, hooks imported on first use), with stricter collision handling than any of the three systems, because all three let a duplicate name win silently in at least one path.
- **Collisions.** Hamilton's real key is not the extension name: today five extension modules register a loader or saver named `parquet`, and resolution is by type with "last registered wins". With entry points, "last registered" becomes install order. The proposal makes every collision either an error that names both distributions or a deterministic, logged choice.
- **Compatibility.** A provider declares `apache-hamilton>=X` in its packaging and an integer extension-contract version in its manifest; the core checks the contract version before importing the extension, and skips with a warning that names the distribution and the range it needs.
- **Distributions.** Two integrations meet the criteria for their own distribution: Polars and pandas. Both have had repeated upstream-forced changes, ship over a thousand lines that move at their library's pace, and are broken today against their library's newest release in the newest Hamilton release, with the fix merged and waiting for a core release. Every other integration stays an extra. The strongest counter-argument is that the root cause is the core's release frequency (two releases since entering the Incubator), and that each extra distribution costs its own ASF vote. The proposal therefore pairs the split with one vote per release wave and patch releases for broken integrations, and ranks "no split, patch releases only" a close second.
- **Confidence.** High on the comparison of the three systems and on Hamilton's facts (each checked in source at a stated version, or measured). High that eager loading must go (measured: 5.6 s against 1.0 s for `import hamilton.driver` in a full environment). Medium on entry points over a fixed in-core manifest, since evidence of third-party demand is thin. Medium-low on the split, which turns on the PPMC's release capacity, a fact only the owner and the PPMC can supply.

## Terms

These terms are used with one meaning throughout.

- **Integration:** Hamilton code that adapts a third-party library. Every module under `hamilton/plugins/` is one, and so is `hamilton/data_quality/pandera_validators.py`.
- **Extension:** an integration whose import registers something in Hamilton's registries (dataframe and column types, `get_column`/`fill_with_scalar` implementations, data loaders and savers). Today these are the 21 modules named by `registry.ExtensionName`. An extension needs discovery, because user code reaches what it registers by name or by type without importing it.
- **User-imported module:** an integration the user imports by its path (`hamilton.plugins.h_ray`, `h_tqdm`, ...) to get an adapter, decorator or result builder. It needs no discovery.
- **Discovery:** finding out which extensions are installed and what each provides, without importing them.
- **Loading:** importing an extension module so that its registrations run.
- **Lazy loading:** loading an extension only when a graph needs something it provides.
- **Manifest:** a static description of an extension, readable without importing the extension or its library: its name, contract version, the libraries it adapts, and the materializer names and types it registers.
- **Collision:** two extensions claiming the same key. Hamilton has three kinds of key: an extension name, a materializer name together with the type it applies to, and a dataframe type in the type registries.
- **Compatibility:** whether an extension works with the installed core and with the installed version of its library.
- **Distribution:** a package on PyPI with its own name, version and release. **Extra:** an optional-dependency set of `apache-hamilton` (`pip install apache-hamilton[polars]`). **Provider:** an integration shipped as its own distribution.
- **Operator:** the person who installs and runs Hamilton (in a service, a notebook or CI). **Plugin author:** whoever writes an integration, in this repository or outside it. **Maintainer:** a Hamilton committer who reviews, releases and supports the integrations.

## Method and sources

- **Versions compared.** pytest 9.2.0 (released 2026-10-27, tag commit `ae1d0ff5`) with pluggy 1.7.0 (2026-10-14, `4c7f6365`); Apache Airflow 3.4.0 (2026-11-06, `619a787a`), providers read in-tree at that tag (postgres 7.1.1, google 22.7.0); stevedore 5.10.0 (2026-11-12, `c9f616a6`). Each is the newest release on PyPI on 2026-11-17. The base layer is CPython 3.13.9's `importlib.metadata` and the PyPA entry points specification at commit `585cc8c0` of `pypa/packaging.python.org`.
- **Kind of source.** Each claim about another system cites that system's source at its tag (GitHub permalinks with line ranges) or its own documentation. Where no versioned documentation exists, the report says so and cites the documentation source file at the tag: pytest 9.2 and pluggy 1.x publish only `stable` pages, Airflow's provider summary pages exist only unversioned, and stevedore's `latest` build is `5.10.0.dev14`. Issue-tracker and mailing-list statements are marked as such; none carries a key claim alone.
- **How the reading was split.** The reading of each system was handed to a separate helper with the same nine facets (discovery, naming, collision, compatibility, lazy loading, failed load, the three frames, distribution model, pain points) and the same rules: tagged sources, at least two query formulations per facet, every citation re-opened. The comparison and the proposal were written by one author who read all three reports. The citations the proposal turns on were then re-opened by that author in the cloned sources at the tags: pluggy's entry-point loop, pytest's autoload switch and `-p no:` blocking, Airflow's discovery loop, its minimum-version tables, its lazy hook dictionary, its connection-type collision warning, its provider release cadence and its wave vote template, stevedore's two conflict resolvers, its DriverManager conflict path, its `verify_requirements` deprecation, its name filter and its load-failure handler, CPython's distribution deduplication, and the PyPA specification's sentence on name conflicts. Each said what it is credited with. The queries run per facet are in the appendix.
- **Hamilton facts** were derived from the code at `31b3a832`, from `git log` on the same branch, from PyPI's JSON API (fetched 2026-11-17), and from the Hamilton and Incubator mailing-list archives at lists.apache.org (fetched 2026-11-17).
- **Measurements.** The benchmark harness of Ticket 03 is not yet on `2.0`, so the measurements here are ad-hoc scripts, described with each result. They describe dependency weight and import cost; no claim here says that a change of Hamilton's own code is faster or slower. Machine: Intel Core i7-3770 (2012, 8 threads, no AVX2), 31 GiB RAM, Linux 7.0; CPython 3.12.14 from uv (python-build-standalone). Other work ran on the machine during the runs, so ranges are wide; each result gives its run count and range. The CPU's missing AVX2 matters twice: the default Polars build and lancedb cannot run on it (see the inventory).

## Hamilton today

### How extensions are found and loaded

- `hamilton/registry.py` lists 21 names in `ExtensionName` (L31-L53): `yaml`, `matplotlib`, `numpy`, `pandas`, `plotly`, `polars`, `polars_lazyframe`, `pyspark_pandas`, `spark`, `dask`, `geopandas`, `xgboost`, `lightgbm`, `sklearn_plot`, `vaex`, `ibis`, `dlt`, `kedro`, `huggingface`, `mlflow`, `pydantic`. The list is unchanged since the Ticket was written.
- Importing `hamilton.function_modifiers.base` calls `registry.initialize()` (L37-L41), and `hamilton.driver` imports it. `initialize()` (L100-L114) imports `hamilton.plugins.<name>_extensions` for each name, unless `HAMILTON_AUTOLOAD_EXTENSIONS` is `"0"`, and logs a failed import at DEBUG. The variable can also be set from `~/.hamilton.conf`, which two console scripts edit (`hamilton-disable-autoload-extensions`, `hamilton-enable-autoload-extensions`).
- `load_extension` (L79-L97) treats a module as a dataframe extension unless it sets `COLUMN_FRIENDLY_DF_TYPE = False`, and then asserts `register_types`, `get_column_<name>` and `fill_with_scalar_<name>`. Seven extensions are dataframe extensions (`pandas`, `polars`, `pyspark_pandas`, `dask`, `geopandas`, `ibis`, `vaex`); fourteen set the flag to false and register only loaders, savers or types.
- Extensions register loaders and savers by calling `registry.register_adapter`, which appends to `LOADER_REGISTRY[name]` and `SAVER_REGISTRY[name]` (L224-L234). `from_.<name>`, `to.<name>`, `load_from.<name>` and `save_to.<name>` look the name up in those dictionaries and raise `AttributeError` when it is absent (`hamilton/function_modifiers/adapters.py` L367-L381, `hamilton/io/materialization.py` L46-L63 and L89-L102). A lookup by name therefore needs every extension that could provide the name to be loaded first. This is the constraint any lazy scheme must meet.
- When several adapters share a name, `resolve_adapter_class` (`adapters.py` L119-L147) keeps those that apply to the requested type and returns the most recently registered one, logging a WARNING when more than one applies. The `get_column` and `fill_with_scalar` dispatchers (`registry.py`) and the cache fingerprint functions (`hamilton/caching/fingerprinting.py`) are `functools.singledispatch` functions, where a second registration for a type replaces the first without a message.
- Hamilton already has internal collisions in the materializer namespace. Counting the modules whose adapter class returns a given name (script in the appendix): `parquet` from 5 integrations (pandas, Polars, Polars LazyFrame, Spark, Hugging Face), `csv` from 4, `json` from 4 (the core's default loaders, pandas, Polars, XGBoost), `feather` from 3, and `file`, `html` and `pickle` from 2 each. The effective rule today is "the order of `ExtensionName`", because that list fixes the load order.
- Two other eager lists exist outside the registry. `hamilton/data_quality/default_validators.py` imports pandera at module import when it is installed (L512-L526), whatever `HAMILTON_AUTOLOAD_EXTENSIONS` says. The SDK distribution's `hamilton_sdk/tracking/runs.py` (L43-L62) imports `hamilton_sdk.tracking.<name>_stats` for a fixed list of eight libraries, the same pattern as `registry.initialize()`.
- `hamilton/plugins/README.md` says of the extension mechanism: "Note this is not a public-facing API -- this is for managing internal plugins." Adding an extension today means editing `ExtensionName` in the core.

### What eager loading costs, measured

Environment: a fresh virtual environment with CPython 3.12.14, `apache-hamilton` installed editable from `31b3a832` with the `dask` and `pyspark` extras and the `test` dependency group (`uv pip install -e .[dask,pyspark] --group test`), plus `polars[rtcompat]` because the default Polars build cannot run on this CPU, and without lancedb (see the next paragraph). `~/.hamilton.conf` had no autoload key. Each run is a fresh process timing `import hamilton.driver` with `time.perf_counter`, after one warm-up run per mode that writes bytecode; the two modes alternated, 10 runs each.

| `import hamilton.driver` | median | range | modules in `sys.modules` |
| --- | --- | --- | --- |
| autoload on (default) | 5,600 ms | 5,147 to 8,786 ms | 4,510 |
| `HAMILTON_AUTOLOAD_EXTENSIONS=0` | 1,038 ms | 863 to 1,425 ms | 1,064 |

The difference of the medians is about 4.6 s, and the ranges do not overlap: the slowest run with autoload off (1,425 ms) is well below the fastest run with autoload on (5,147 ms). The difference is not noise. One `python -X importtime` profile with autoload on names the limiter: cumulative import time attributed to the first importer was mlflow 1.49 s, xgboost 0.80 s, scikit-learn 0.71 s, dlt 0.51 s and pandas 0.45 s. With autoload on, 22 extension modules were loaded and 16 heavy libraries imported; with autoload off, four: numpy and pandas (still core dependencies on this branch; Ticket 21 removes them) and pydantic and pyspark, which arrive through the eager pandera import in `default_validators`. The Ticket's figure of 431 ms was measured on a different machine with CPython 3.15 and a smaller environment, and is not comparable with these.

A second observation from the same environment, before lancedb was removed: with lancedb 0.41.0 installed, `import hamilton.driver` with autoload on killed the interpreter with SIGILL (exit code 132) while `huggingface_extensions` imported lancedb; with autoload off it imported normally. The cause is this CPU's missing instruction-set extensions, an uncommon condition. It still shows the operator's exposure under eager loading: a library the user never uses, installed for another purpose, can break the import of Hamilton.

### Evidence on demand from outside the project

GitHub code search (2026-11-17; it indexes only default branches of a subset of repositories, so this is limited evidence) found four repositories outside Hamilton and its forks that use `from hamilton import registry`, and one (`Jybbs/thermur`) that calls `registry.register_adapter` from its own code. Five repositories outside Hamilton and its forks reference `HAMILTON_AUTOLOAD_EXTENSIONS`; every match shown sets it to disable autoloading: `legout/flowerpower`, a framework built on Hamilton, defaults it to `0`, `datashaman/hamilton-example` sets it to `0` in its scripts, and `kelsayed17/fnloom` sets it in its benchmarks "so its import loads no heavy extensions". This is evidence that operators pay for and avoid the eager import. It is not evidence that third parties want to publish extensions: no package outside the project was found that ships a Hamilton extension.

### Release history

| Distribution | Releases (PyPI upload date) |
| --- | --- |
| `sf-hamilton` / `apache-hamilton` | 1.86.1 2025-01-04, 1.87.0 2025-02-12, 1.88.0 2025-03-29, 1.89.0 2025-10-12, 1.90.0 2026-04-25 |
| `apache-hamilton-sdk`, `-ui`, `-lsp`, `-contrib` | one release each since the rename, all 2026-07-14 |

Hamilton entered the Incubator on 2025-04-10 (Incubator general list, "[RESULT] [VOTE] Accept Hamilton into the Apache Incubator"). Since then each release needs a podling vote and an Incubator PMC vote, with at least three binding +1 votes from Incubator PMC members ([Incubator policy, "Releases"](https://incubator.apache.org/policy/incubation.html), accessed 2026-11-17) and votes that should stay open at least 72 hours ([ASF release policy, "Release approval"](https://www.apache.org/legal/release-policy.html), accessed 2026-11-17). The dev list archive shows how long that took: 1.89.0 from the first vote call on 2025-09-14 to PyPI on 2025-10-12, after a second release candidate; 1.90.0 from 2026-04-04 to 2026-04-25; the four sub-distributions from 2026-05-26 to 2026-07-14, in one vote thread per distribution (a combined call on 2026-05-26 was followed by separate threads) and two rounds of candidates. The release tag of 1.90.0 is at commit `e84ed90b` of 2026-04-03; everything merged since waits for the next release.

That wait has a cost for integrations, visible today in three that are broken in the newest release against their library's newest release, with the fix merged:

- **Polars.** Polars 2.0 (first release 2026-10-06) removed reader arguments that Hamilton passes; commit `a9ce4117` (2026-11-05) says "Every one of these readers failed with its default settings" and adds a third set of reader modules for Polars 2. Unreleased.
- **pandas.** Commit `6f1f9df5` (2026-11-03): pandas 3.1 "broke every table load" through `PandasTableReader`. Commit `2206e09d` (2026-09-25) handles parameters pandas 3.0 removed from `read_table`. Both unreleased.
- **Datadog.** The released 1.90.0 metadata requires `ddtrace<3.0` for the `datadog` extra (PyPI JSON), while ddtrace 3.0 appeared on 2025-02-20 and 4.0 on 2025-11-20; commit `e10f6b27` (2026-04-26, a day after the release) moves the plugin to the ddtrace 4 API. Unreleased.

A fourth, Plotly, has a merged fix for an argument Plotly removed (`76758bc8`, 2026-09-20), also unreleased.

## How the three systems do it

Each system is described along the same facets; the table after the three sections lines them up. Citations are permalinks at the tags named in "Method and sources".

### pytest 9.2.0 (with pluggy 1.7.0)

- **Discovery.** Installed distributions declare entry points in the `pytest11` group ([docs source](https://github.com/pytest-dev/pytest/blob/9.2.0/doc/en/how-to/writing_plugins.rst#L153-L171): "pytest looks up the ``pytest11`` entrypoint to discover its plugins"). Other mechanisms are `-p name`, the `PYTEST_PLUGINS` variable, a `pytest_plugins` variable in the root `conftest.py`, and `conftest.py` files. At startup pytest applies `-p no:` blocks, imports its built-in plugins, loads `-p` plugins, then autoloads every `pytest11` entry point ([config/\_\_init\_\_.py L1762-L1772](https://github.com/pytest-dev/pytest/blob/9.2.0/src/_pytest/config/__init__.py#L1762-L1772)). Filtering reads only metadata, but every entry point that is not blocked is imported: pluggy iterates `importlib.metadata.distributions()` and calls `ep.load()` for each match ([pluggy \_manager.py L511-L523](https://github.com/pytest-dev/pluggy/blob/1.7.0/src/pluggy/_manager.py#L511-L523)).
- **Naming.** An autoloaded plugin is registered under its entry-point name (`self.register(plugin, name=ep.name)`, same lines); a plugin named on the command line under its module path; a `conftest.py` under its file path. The distribution is kept only on a side list, for the header and for `required_plugins`.
- **Collision.** A second entry point with a name already registered is skipped silently, without being imported (`# already registered` / `or self.has_plugin(ep.name)` / `continue`, same lines). Which one wins depends on the order of `importlib.metadata.distributions()`, which follows `sys.path`. Registering the same name with a different object raises `ValueError("Plugin name already registered: ...")` ([pluggy L206-L218](https://github.com/pytest-dev/pluggy/blob/1.7.0/src/pluggy/_manager.py#L206-L218)). The cost is visible in pytest-dev's own extracted `pytest-pastebin`, which renamed its entry point to `pastebin2` to avoid the built-in plugin's name ([pyproject.toml L34-L36 at v1.0.0](https://github.com/pytest-dev/pytest-pastebin/blob/v1.0.0/pyproject.toml#L34-L36)). A way to order plugins has been requested since 2015 (issue #935, open).
- **Compatibility.** A plugin states compatibility only as a packaging dependency (`pytest>=X`), which the installer enforces; pytest does not read it at runtime. Projects can require a minimum pytest (`minversion`, [L1624-L1632](https://github.com/pytest-dev/pytest/blob/9.2.0/src/_pytest/config/__init__.py#L1624-L1632)) and required plugins with version specifiers (`required_plugins`, [L1648-L1669](https://github.com/pytest-dev/pytest/blob/9.2.0/src/_pytest/config/__init__.py#L1648-L1669)). pluggy validates hook implementations at registration: an implementation with an argument the specification lacks is rejected ([pluggy L444-L454](https://github.com/pytest-dev/pluggy/blob/1.7.0/src/pluggy/_manager.py#L444-L454)), while an implementation may take fewer arguments, which is pluggy's forward-compatibility mechanism ([pluggy docs, "Opt-in arguments"](https://pluggy.readthedocs.io/en/stable/#opt-in-arguments), stable only). pytest removes deprecated behavior only in major releases ([backwards-compatibility.rst](https://docs.pytest.org/en/stable/backwards-compatibility.html), stable only).
- **Lazy loading.** None. Every installed, non-blocked plugin is imported on every run ([plugins.rst L18-L19](https://github.com/pytest-dev/pytest/blob/9.2.0/doc/en/how-to/plugins.rst#L18-L19): "If a plugin is installed, ``pytest`` automatically finds and integrates it"). The operator can block one plugin with `-p no:name` before it is imported ([L869-L887](https://github.com/pytest-dev/pytest/blob/9.2.0/src/_pytest/config/__init__.py#L869-L887)), or turn autoloading off with `PYTEST_DISABLE_PLUGIN_AUTOLOAD` (since 3.8.0) or `--disable-plugin-autoload` (since 8.4.0) and then name the plugins wanted. pytest offers no listing of installed but unloaded plugins.
- **Failed load.** The run aborts. Since 9.2.0 a plugin that is found but raises on import exits with code 3 and "Error while loading plugin" ([L966-L975](https://github.com/pytest-dev/pytest/blob/9.2.0/src/_pytest/config/__init__.py#L966-L975)); a plugin that cannot be found is a usage error, code 4.
- **Frames.** The plugin author writes one entry point and a module of `pytest_*` functions. The operator controls installation, `-p`, `-p no:` and the autoload switch. The maintainer keeps hard-coded tuples of built-in plugins ([L338-L381](https://github.com/pytest-dev/pytest/blob/9.2.0/src/_pytest/config/__init__.py#L338-L381)) and a list of external plugins merged into the core.
- **Distribution model.** Every third-party plugin is its own distribution, by convention named `pytest-*`; pytest ships none of them. Code moves both ways: `pytest-subtests` was merged into the core in 9.0, and the pastebin plugin was extracted. The plugin list page is generated weekly from PyPI by name prefix and "is not a curated collection" ([plugin\_list.rst L8-L20](https://github.com/pytest-dev/pytest/blob/9.2.0/doc/en/reference/plugin_list.rst#L8-L20)).
- **Pain points from its own tracker.** Autoloading every installed plugin broke unrelated test runs (issue #3784, 2018, which produced `PYTEST_DISABLE_PLUGIN_AUTOLOAD`); registering one plugin by two mechanisms raises "Plugin already registered under a different name" (issues #12647, #13983); plugin import failures had a wrong exit code from 2015 until 9.2.0 (issue #993). No issue quantifies the startup cost of autoloading.

### Apache Airflow 3.4.0 providers

- **Discovery.** Providers declare one entry point in the group `apache_airflow_provider`, naming a callable that returns a metadata dictionary ([postgres pyproject.toml L161-L162](https://github.com/apache/airflow/blob/3.4.0/providers/postgres/pyproject.toml#L161-L162)). Discovery walks the group once per process and calls each callable ([providers\_discovery.py L320-L334](https://github.com/apache/airflow/blob/3.4.0/shared/providers_discovery/src/airflow_shared/providers_discovery/providers_discovery.py#L320-L334)). It runs on first use of the providers manager when `[core] lazy_discover_providers` is true, the default since 2.0.0 ([configuration reference 3.4.0](https://airflow.apache.org/docs/apache-airflow/3.4.0/configurations-ref.html)). Discovery imports each provider's small top-level package and its generated `get_provider_info` module, not the hooks or operators.
- **Naming.** The registry key is the provider's normalized distribution name, and the `package-name` in its metadata must match it or discovery raises `ValueError` ([L348-L359](https://github.com/apache/airflow/blob/3.4.0/shared/providers_discovery/src/airflow_shared/providers_discovery/providers_discovery.py#L348-L359)). Capabilities are registered as dotted-path strings in the metadata: a hook is declared by connection type and class path ([postgres provider.yaml L118-L124](https://github.com/apache/airflow/blob/3.4.0/providers/postgres/provider.yaml#L118-L124)). The metadata of community providers is generated from `provider.yaml` ([get\_provider\_info.py L18-L26](https://github.com/apache/airflow/blob/3.4.0/providers/postgres/src/airflow/providers/postgres/get_provider_info.py#L18-L26)); a third party writes the callable by hand.
- **Collision.** A second distribution with the same name is skipped silently (`if package_name in provider_dict:` / `continue`, [L323-L325](https://github.com/apache/airflow/blob/3.4.0/shared/providers_discovery/src/airflow_shared/providers_discovery/providers_discovery.py#L323-L325)); the warning written for that case further down the loop cannot be reached, by reading of the control flow. Two providers declaring one connection type: providers are sorted by name before hooks are registered ([providers\_manager.py L560](https://github.com/apache/airflow/blob/3.4.0/airflow-core/src/airflow/providers_manager.py#L560)), so the alphabetically first wins, and the loser logs a WARNING naming the winner ([L811-L818](https://github.com/apache/airflow/blob/3.4.0/airflow-core/src/airflow/providers_manager.py#L811-L818)). The how-to says only that "only one of them will succeed".
- **Compatibility.** Four layers. (1) Packaging: each provider requires `apache-airflow>=X`; at 3.4.0, 99 of 108 providers require `>=2.11.0`. (2) Each provider's generated `__init__.py` raises `RuntimeError` on an older core ([postgres \_\_init\_\_.py L32-L39](https://github.com/apache/airflow/blob/3.4.0/providers/postgres/src/airflow/providers/postgres/__init__.py#L32-L39)). (3) The core keeps two tables: `MIN_PROVIDER_VERSIONS`, which only warns, and `BLOCKED_PROVIDER_MIN_VERSIONS`, which skips a provider before importing it ([L56-L62](https://github.com/apache/airflow/blob/3.4.0/airflow-core/src/airflow/providers_manager.py#L56-L62)). (4) Metadata is validated against a JSON schema and a non-conforming provider is skipped. The documented policy raises the providers' minimum core version to the next minor release twelve months after that minor's first release, and says it "has not yet been finalized for Airflow 3" ([PROVIDER\_RELEASES.rst L73-L98](https://github.com/apache/airflow/blob/3.4.0/providers/PROVIDER_RELEASES.rst#L73-L98)); its own example date for the next floor (May 2026) had passed at 3.4.0 without the floor moving.
- **Lazy loading.** Three levels: discovery on first use; each category (hooks, extra links, secrets backends, ...) initialized on first access; and hooks imported one by one on first lookup through a lazy dictionary keyed by connection type ([L730-L739](https://github.com/apache/airflow/blob/3.4.0/airflow-core/src/airflow/providers_manager.py#L730-L739): "Defer importing hook to access time"). Most other categories import every class of the category when first accessed. `airflow providers list` reads only metadata; listing hooks imports all of them.
- **Failed load.** Inside a category, an import failure is logged (INFO for an optional feature, WARNING otherwise) and the class is skipped. A provider whose metadata fails the schema is skipped with a WARNING; until 3.4.0 one malformed provider stopped discovery for all the others (apache/airflow pull request #72854, merged 2026-09-10). An exception from the metadata callable itself is still not caught, by reading of the code.
- **Frames.** The operator chooses providers by installing them (extras of `apache-airflow` or direct installs) and pins versions with per-release constraint files; there is no setting to disable one installed provider. A third-party author writes an entry point and a metadata callable. The maintainers keep `provider.yaml` and two schemas, generators for metadata, `__init__.py` and `pyproject.toml`, per-provider changelogs and a compatibility test matrix.
- **Distribution model.** The root `apache-airflow` is a metapackage pinned to `apache-airflow-core` and the task SDK, with one extra per provider ([pyproject.toml L58-L65](https://github.com/apache/airflow/blob/3.4.0/pyproject.toml#L58-L65)). Each of the 109 providers has its own `pyproject.toml` and version. Providers are released "usually every 2 weeks in batches" ([PROVIDER\_RELEASES.rst L28-L33](https://github.com/apache/airflow/blob/3.4.0/providers/PROVIDER_RELEASES.rst#L28-L33)), with one vote per batch: the vote email template calls "a vote on the release" of the whole wave and points to one source tarball of the repository ([README\_RELEASE\_PROVIDERS.md L1260-L1282](https://github.com/apache/airflow/blob/3.4.0/dev/README_RELEASE_PROVIDERS.md#L1260-L1282)). In the twelve months to 2026-10-31 there were 43 provider waves against 15 core releases, and the Google provider went through four major versions. Current provider sources are tested against released cores 2.11.1 to 3.3.2 in CI. Provider wheels share the `airflow.providers` namespace: a provider's flit module is `airflow.providers.postgres` ([L164-L165](https://github.com/apache/airflow/blob/3.4.0/providers/postgres/pyproject.toml#L164-L165)) and the core's `airflow/__init__.py` extends its path ([L26](https://github.com/apache/airflow/blob/3.4.0/airflow-core/src/airflow/__init__.py#L26)).
- **Pain points from its own tracker and list.** The minimum-version gate reaches users when pip resolves an incompatible provider (issue #57026: "needs Apache Airflow 3.0.2+"). Raising the providers' floor across a major release was debated on the dev list in March 2026 with maintainer burden named as the deciding cost; the outcome was not found. No issue quantifies discovery cost; the code carries a CI check that discovery did not run during CLI parsing.

### stevedore 5.10.0

- **Discovery.** A plugin is an entry point in a namespace (an entry-point group). A manager discovers in its constructor; listing reads only metadata, and import happens per plugin through `ep.load()` ([extension.py L275-L284 and L336-L338](https://github.com/openstack/stevedore/blob/5.10.0/stevedore/extension.py#L275-L284)). Listings are cached in memory per namespace and on disk in one JSON file for all groups of the environment, keyed by the interpreter, `sys.path` and the modification times of every `entry_points.txt` ([\_cache.py L83-L99](https://github.com/openstack/stevedore/blob/5.10.0/stevedore/_cache.py#L83-L99)).
- **Naming.** The key is the namespace and the entry-point name. The documentation says namespaces belong to the consuming application and that names "must be unique within a given distribution, but are not necessarily unique in a namespace" ([naming.rst L33-L38](https://github.com/openstack/stevedore/blob/5.10.0/doc/source/user/tutorial/naming.rst#L33-L38)), which repeats the PyPA specification: "If different distributions provide the same name, the consumer decides how to handle such conflicts" ([entry-points.rst L44-L46](https://github.com/pypa/packaging.python.org/blob/585cc8c019b905dc50e03a331ad45a0b1e6d3bac/source/specifications/entry-points.rst#L44-L46)).
- **Collision.** Managers take a `conflict_resolver` (since 5.6.0). The default for most managers, `ignore_conflicts`, logs a WARNING and returns the last one found; `error_on_conflict` raises `MultipleMatches` ([extension.py L110-L138](https://github.com/openstack/stevedore/blob/5.10.0/stevedore/extension.py#L110-L138)). `DriverManager`, which loads exactly one named plugin, defaults to raising ([driver.py L155-L171](https://github.com/openstack/stevedore/blob/5.10.0/stevedore/driver.py#L155-L171)). `HookManager` loads every plugin with the requested name on purpose. Every duplicate is imported before the resolver runs. By reading of the code, name lookup groups duplicates with an unsorted `itertools.groupby` ([L255-L273](https://github.com/openstack/stevedore/blob/5.10.0/stevedore/extension.py#L255-L273)), so duplicates from two distributions that are not adjacent bypass the resolver and the last one silently wins.
- **Compatibility.** None. `verify_requirements` stopped working when stevedore moved to `importlib.metadata` in 3.0.0 and is deprecated as a no-op ([extension.py L184-L189](https://github.com/openstack/stevedore/blob/5.10.0/stevedore/extension.py#L184-L189); bug 1897969, Won't Fix). The only gate is `EnabledExtensionManager`'s `check_func`, which runs after the plugin is imported. Version checks are left to the application.
- **Lazy loading.** `ExtensionManager` imports every plugin of the namespace ([loading.rst L69-L71](https://github.com/openstack/stevedore/blob/5.10.0/doc/source/user/tutorial/loading.rst#L69-L71): "It loads all of the plugins it finds"). `NamedExtensionManager`, `DriverManager` and `HookManager` check the name before importing, "to prevent undesirable code from being loaded at all" ([named.py L203-L207](https://github.com/openstack/stevedore/blob/5.10.0/stevedore/named.py#L203-L207)). There is no deferred proxy: what is selected is imported when the manager is built.
- **Failed load.** Log at ERROR ("Could not load %r: %s") and skip, unless the application passes `on_load_failure_callback` ([L305-L323](https://github.com/openstack/stevedore/blob/5.10.0/stevedore/extension.py#L305-L323)); `DriverManager` re-raises by default.
- **Frames.** The plugin author writes one entry-point line. The operator controls what is installed and whatever names the application reads from its configuration; stevedore reads no configuration. The application maintainer writes everything else: the plugin interface, the selection, the failure, conflict and compatibility policy.
- **Distribution model.** None of its own. Its documentation stresses that plugins "can be distributed independently of an application", and the essay on Ceilometer records the practice of registering in-tree plugins through the same entry points: "we always use entry points, even for the plugins we distribute with our core. That eliminates any special cases" ([pycon2013.rst L395-L397](https://github.com/openstack/stevedore/blob/5.10.0/doc/source/user/essays/pycon2013.rst#L395-L397)).
- **Pain points from its own tracker.** The disk cache was corrupted by concurrent cold starts (bug 2169851, fixed in 5.10.0); an importlib\_metadata maintainer asked whether the cache is still needed (bug 1942209, closed as "Opinion"; the removal patch was abandoned); newly installed plugins stay invisible to a running process (bug 1627906, "working as designed").

### The base layer: `importlib.metadata`

`importlib.metadata.entry_points()` returns entry points of distributions made unique by normalized name, so a distribution found twice on `sys.path` contributes once and the first one wins ([CPython 3.13.9 L990-L1011](https://github.com/python/cpython/blob/v3.13.9/Lib/importlib/metadata/__init__.py#L990-L1011)); the documentation does not state this, only the source does. Listing imports nothing; `EntryPoint.load()` imports the module ([L173-L181](https://github.com/python/cpython/blob/v3.13.9/Lib/importlib/metadata/__init__.py#L173-L181)). The `group=` selection used below is available on every Python Hamilton supports (3.11 and later), so no backport package is needed.

### Side by side

| Facet | pytest 9.2.0 | Airflow 3.4.0 providers | stevedore 5.10.0 | Hamilton 1.90 / `2.0` today |
| --- | --- | --- | --- | --- |
| Discovery mechanism | entry-point group `pytest11`, plus `-p`, env, conftest | entry-point group `apache_airflow_provider` | entry-point namespace chosen by the application | fixed list `ExtensionName` in the core |
| What discovery imports | every non-blocked plugin | each provider's metadata module only | nothing until a manager loads | every listed extension and its library |
| Registration key | entry-point name | distribution name; connection type for hooks | (namespace, entry-point name) | extension name; materializer name + type; dataframe type |
| Duplicate name | first in `sys.path` order wins, silently | first distribution wins silently; connection type: alphabetical, WARNING | WARNING, last wins (default); error for drivers; non-adjacent duplicates bypass the resolver | list order; materializer ties WARNING, last wins; singledispatch silent |
| Plugin states compatibility | packaging `pytest>=X` | packaging floor, generated import-time gate | nothing | nothing (in-tree only; Polars dispatches on its library version) |
| Host checks at runtime | `minversion`, `required_plugins`, hook signatures | warn table, block table, schema | none (`verify_requirements` is a no-op) | assertions on three function names |
| Lazy loading | none | discovery, category and per-hook | by name, at manager construction | none; one global off switch |
| Metadata without import | not offered | `providers list` | `entry_points_names()` | not offered |
| Failed load | run aborts (code 3 or 4) | log and skip, mostly; a few paths raise | log ERROR and skip | log DEBUG and skip |
| Operator controls | install, `-p`, `-p no:`, autoload off | install, constraints, lazy switches; no per-provider disable | whatever the application exposes | install, autoload off (env or `~/.hamilton.conf`) |
| Distribution model | every plugin separate, third-party | metapackage, 109 separate providers, batch votes | none | one distribution with extras, plus 4 tools |

## What the comparison shows

Each lesson names its evidence and what it implies for Hamilton.

1. **Eager loading is what operators fight in every system that has it.** pytest added an off switch after autoloading broke unrelated runs (#3784) and a second form of it in 8.4; Hamilton users set `HAMILTON_AUTOLOAD_EXTENSIONS=0` in their own code; Airflow made discovery lazy by default in 2.0.0 and guards it in CI. Hamilton's own measurement is a 4.6 s difference in a full environment, and one environment where an unused library broke the import. Implication: Hamilton should load extensions lazily, not just offer a switch.
2. **The only lazy design among the three that keeps "what exists" separate from "what is imported" is Airflow's metadata callable.** stevedore is lazy only when the application already knows the names it wants; pytest is not lazy. Hamilton's lookups are by materializer name and by type, so it needs to answer "which extensions provide `parquet` for `polars.DataFrame`" before importing any of them. Implication: a static manifest per extension, readable without importing the extension or its library. The same manifest serves the docs build and the outline's catalog inspection "without installing every provider".
3. **All three systems let a duplicate win silently somewhere,** and each has paid for it: pytest-dev's own plugin had to rename to `pastebin2`; Airflow's warning for duplicate providers cannot be reached; stevedore's resolver is bypassed when duplicates are not adjacent. The PyPA specification leaves conflicts to the consumer. Implication: Hamilton should decide every collision explicitly, either as an error naming both distributions or as a deterministic choice that is logged, and should not rely on install order. This matters more for Hamilton than for the others because its main key, a materializer name, is shared on purpose by several extensions and disambiguated by type.
4. **Packaging floors are the compatibility mechanism everyone actually relies on; runtime checks are thin.** pytest reads nothing at runtime beyond what a project asks for; stevedore's one check rotted silently for five years; Airflow's runtime tables have one entry each, and its real gate is a generated check in each provider's `__init__.py`. Implication: keep the runtime check small and cheap, versioned on the extension contract rather than on the core's version, and make the packaging floor the primary statement.
5. **Failing open versus failing closed differs by system, and both have costs.** pytest aborts the run; Airflow learned in 3.4.0 that one bad provider must not stop the others; stevedore logs and skips. Implication: skip with a visible warning when an extension cannot be loaded in the background, and raise when the user asked for what it provides.
6. **Independent distributions pay off at a cadence Hamilton does not have, at a release cost Hamilton must count.** Airflow releases providers every two weeks with one vote per wave and tests each provider against five released cores; that machinery (generated metadata, schemas, constraint files, release tooling) is maintained by a large PMC. pytest's plugins are third-party and cost pytest nothing. Hamilton's distributions are all released by its own small PPMC, one vote thread each, and the measured round trip is three to seven weeks. Implication: split only where the cadence need is recurring and the code large, and vote on a release wave once.

## Question 1: discovery rules

### Options

- **A. Today's eager fixed list with an opt-out.** The counter-hypothesis in its present form.
- **B. A fixed manifest list in the core, loaded on demand, without entry points.** The counter-hypothesis in its strongest form: it keeps everything in-tree, as today, and fixes the import cost.
- **C. Entry points that point to static manifests, loaded on demand.** The core's own extensions are declared through the same group.
- **D. Entry points loaded eagerly,** as pytest does.

### Criteria and ranking

| Criterion | A | B | C | D |
| --- | --- | --- | --- | --- |
| Operator: libraries not used by the graph are not imported | no | yes | yes | no |
| Plugin author: an integration can be added without changing the core | no | no | yes | yes |
| Collisions decided deterministically, independent of install order | yes (one list) | yes (one list) | yes, with the rules below | needs the same rules as C |
| Compatibility checked before import | no | in-tree only | yes | no (imports first) |
| Catalog and docs read without importing libraries | no | yes | yes | no |
| Maintainer: one mechanism for in-tree and external extensions | n/a | n/a | yes | yes |
| Maintainer: extension contract becomes public API | no | no | yes (a cost) | yes (a cost) |
| Migration from 1.x | none | small | small | small |
| A provider split can follow without core changes | no | no | yes | yes |

Ranking: **C, then B, then A, then D.** D keeps the eager cost and adds third-party code to it. A fails the operator. B and C share all of the work that matters to the operator (manifests, lazy triggers, collision rules); they differ in where the list of manifests lives. C wins on two criteria: an integration can be added or moved to its own distribution without editing the core, and in-tree and external extensions take one path ("That eliminates any special cases", stevedore's Ceilometer essay). B wins on one: the extension contract stays private.

### Strongest counter-argument

"Nobody outside the project publishes Hamilton extensions, and the plugins README calls the mechanism internal. Entry points turn an internal contract into a public one that must be versioned and kept, for a demand that the evidence does not show. B delivers everything the operator needs." The evidence supports the first sentence: code search found no external extension package and one repository registering an adapter from its own code. The answer is that the public-contract cost is paid anyway the moment Hamilton ships one integration as a separate distribution (Question 2), because the core then has to find code it does not ship; and that C can start with a contract version of 1 and a narrow manifest, so the public surface is small. If the owner rejects every split in Question 2, B is the better choice, and the rules below apply to it unchanged except for R1.

### Proposed rules

- **R1. Discovery.** An extension is an entry point in the group `hamilton.extensions` (following stevedore's naming guideline: application name plus API name). Its name is the extension name (`[a-z][a-z0-9_]*`); its value is `module:attr` of a callable that returns the manifest. The manifest module imports only the standard library and Hamilton's manifest types. `apache-hamilton` declares its own extensions in the same group. The core reads the group once per process with `importlib.metadata.entry_points(group=...)`, which deduplicates a distribution found twice on `sys.path`, and caches the manifests in memory; it keeps no disk cache (stevedore's disk cache produced bug 2169851, and its value is disputed in bug 1942209).
- **R2. Manifest.** Fields: `name`; `contract_version` (an integer, R5); `libraries` (top-level import names it adapts, such as `polars`, with an optional version specifier for diagnostics); `module` (the import path whose import performs the registration); `materializers` (name, `load` or `save`, and the qualified names of the types each applies to, as strings such as `"polars.DataFrame"`); `dataframe_types` (qualified names, for extensions that register `get_column` and `fill_with_scalar`). Every type is a string, so reading a manifest never imports the library.
- **R3. Lazy loading.** An extension is loaded at the first of: (a) a materializer lookup (`from_.x`, `to.x`, `load_from.x`, `save_to.x`) resolves name `x` for a type that the extension's manifest lists for `x`; the attribute lookup itself succeeds from the manifests, and the import happens when the type is known, in `resolve_adapter_class`; (b) a registry lookup by value or annotation type (`get_column`, `fill_with_scalar`, `get_column_type_from_df_type`, fingerprinting) sees a type whose qualified name a manifest lists; the user has then already imported that library, so the extension's own import is all that is added; (c) an explicit call, `registry.load_extension(name)` or a Builder option. Before importing, the core checks with `importlib.util.find_spec` that each of the manifest's `libraries` is installed, without importing it. A lookup for a name no manifest declares fails as today, with the names that are available.
- **R4. Collisions.** (1) Two distributions declaring the same extension name: an error at discovery that names both distributions and their versions, unless the operator disables one (R7). (2) Two extensions declaring the same materializer name for an overlapping type: allowed, because this is how pandas and Polars both provide `parquet`; ties keep today's rule that the adapter registered last wins, with the registration order fixed instead of left to install order: the core's default loaders first, then the core's own extensions in the order of today's `ExtensionName` (so that, with the switch off, every tie between in-tree extensions resolves as it does in 1.x), then third-party extensions sorted by extension name, then adapters the user registers in code, which therefore win; the existing WARNING names both. (3) Two extensions declaring the same dataframe type: an error at load naming both, since `singledispatch` would otherwise replace one silently.
- **R5. Compatibility.** A provider declares `apache-hamilton>=X` in its packaging metadata. Its manifest carries `contract_version`; the core knows the set of contract versions it supports and checks the manifest before importing the extension. A mismatch skips the extension with a WARNING naming the distribution, its version, the contract version it has and the ones the core accepts; if the user explicitly requested that extension or a materializer only it provides, the core raises with the same text. The core keeps a table of minimum versions for providers it knows to be broken, applied before import, as Airflow's `BLOCKED_PROVIDER_MIN_VERSIONS` does. An extension that supports several versions of its library dispatches internally, as `polars_extensions` does today, and may name its supported range in `libraries` so that an out-of-range library produces a WARNING, not a failure.
- **R6. Failures.** A library that is not installed makes the extension unavailable, logged at DEBUG (this is the normal case). A manifest callable that raises or returns an invalid manifest: WARNING, skip that extension, keep the others (Airflow's lesson from pull request #72854). An extension module that fails to import although its libraries are installed: WARNING with the traceback at DEBUG, and raise with the original error chained when the user asked for what it provides.
- **R7. Operator controls.** `HAMILTON_AUTOLOAD_EXTENSIONS=0` (and the `~/.hamilton.conf` key) keeps its meaning: nothing is loaded automatically, only on explicit request. A disable list (`HAMILTON_DISABLE_EXTENSIONS=name,...`, in the spirit of pytest's `-p no:`) removes extensions before import. A command, `hamilton extensions`, lists discovered manifests, their distributions, versions and status, without importing any extension.
- **R8. Scope.** The same rules replace the eager pandera import in `hamilton/data_quality/default_validators.py`, and can replace the SDK's fixed list in `hamilton_sdk/tracking/runs.py` through its own group. User-imported modules (`h_*`) and the IPython extension need no discovery and are untouched.

### What changes for users

With the switch off, 1.x behavior must stay; lazy loading changes behavior only in ways a migration note covers. Code that reads `registry.LOADER_REGISTRY` directly, or that relies on an extension's registration having happened at `import hamilton.driver`, sees fewer entries until a graph needs them; the migration note points it to the explicit `load_extension` call. Before and after for an operator with the full environment measured above: `import hamilton.driver` imports 16 heavy libraries and takes about 5.6 s today, and under R3 would import none of them until a graph uses one (the expected result; this is a proposal, not a measurement of an implementation).

## Question 2: which integrations earn their own distribution

### Criteria

The outline's position is that a provider is separated "when dependency conflicts, ownership, or release cadence justify a distribution", and stays an extra otherwise. Applied to the evidence, the three reasons separate cleanly:

- **Conflicts in the user's environment are not solved by a split.** A `apache-hamilton-pyspark` distribution would carry the same `pandas<3.1` requirement as today's extra, because the conflict is between PySpark and pandas: PySpark 4.3.0, the newest release, fails to import with pandas 3.1.1 (measured: `ImportError: cannot import name 'DateOffset' from 'pandas.tseries.frequencies'`).
- **Conflicts in the repository's lock and CI are solved by a separate environment, not by a separate distribution.** A uv workspace member shares the lockfile, as the outline notes; CI already installs vaex outside the resolution.
- **Release cadence is solved by a split,** because a provider can be released when its library breaks it, without a core release.
- **Ownership** gives no signal today: every integration is maintained by the same PPMC.

The criteria used here are therefore: (1) **a recurring cadence need**: at least two Hamilton changes forced by upstream releases in the 24 months to 2026-11-17, or code kept in parallel copies per library version; and (2) **a body of code large enough that versioning it on its own pays**, which this report sets at about a thousand lines across the integration's modules, a judgment the owner may change. Both must hold. These thresholds were set after reading the evidence, not before, and the verdicts are sensitive to them: without the parallel-copies clause Polars, with one forced event in the window, would stay an extra; with a threshold of 500 lines instead of 1,000 the Datadog integration (521 lines, two forced changes) would become a provider; with a threshold of 1,500 lines pandas (2,064) and Polars (3,177) would still qualify. Against them stands the fixed cost of each distribution: a version, a changelog, a compatibility range to test, and a release vote (podling and Incubator PMC) for every release, measured at three to seven weeks per round.

### Inventory

**Library facts.** One fresh virtual environment per row, CPython 3.12.14, the library installed alone with uv on 2026-11-17 (its newest release that installs on 3.12). "Distributions" counts installed distributions and "size" is the size of `site-packages`, both including the library's own dependencies. "Import" is the median and range of 7 fresh-process timings of the import statements the Hamilton module runs, after one warm-up run; the baseline row (`import json`) shows the noise floor of 9 to 17 ms. Releases and majors come from PyPI's JSON API: final releases in the 12 months to 2026-11-17, and major versions first released in the 24 months to that date.

| Library (as imported by Hamilton) | Version | Releases, 12 months | New majors, 24 months | Distributions | Size | Import, median (range) |
| --- | --- | --- | --- | --- | --- | --- |
| baseline (`import json`) | n/a | n/a | n/a | 1 | 1 MB | 12 ms (9 to 17) |
| numpy | 2.5.5 | 13 | none | 1 | 54 MB | 122 ms (100 to 143) |
| pandas, with `pyarrow.fs` | 3.1.1 | 9 | 3.x 2026-01-21 | 6 | 268 MB | 495 ms (469 to 600) |
| polars (`polars[rtcompat]`; the default build crashes on this CPU) | 2.1.0 | 24 | 2.x 2026-10-06 | 4 | 345 MB | 263 ms (184 to 279) |
| PyYAML | 6.0.3 | 0 | none | 1 | 3 MB | 26 ms (23 to 36) |
| matplotlib (`matplotlib.figure`) | 3.11.2 | 5 | none | 11 | 132 MB | 710 ms (554 to 883) |
| plotly (`plotly.graph_objects`) | 7.1.0 | 9 | 6.x 2025-01-28, 7.x 2026-08-25 | 3 | 42 MB | 60 ms (53 to 72) |
| pyspark, `pyspark.pandas`, with `pandas<3.1` | 4.3.0 | 14 | none | 7 | 741 MB | 708 ms (520 to 738) |
| pyspark, `pyspark.sql` | 4.3.0 | 14 | none | 2 | 479 MB | 201 ms (156 to 244) |
| dask, `dask.dataframe` | 2026.8.0 | 13 | calendar versions | 14 | 279 MB | 904 ms (837 to 997) |
| dask[complete], with `dask.distributed` | 2026.8.0 | 13 | calendar versions | 28 | 346 MB | 1,214 ms (1,066 to 1,280) |
| geopandas | 1.2.0 | 4 | none | 10 | 247 MB | 599 ms (524 to 731) |
| xgboost | 3.4.1 | 6 | 3.x 2025-03-15 | 4 | 453 MB | 493 ms (398 to 655) |
| lightgbm | 4.7.0 | 1 | none | 4 | 176 MB | 307 ms (280 to 562) |
| scikit-learn and `matplotlib.pyplot` | 1.9.1 | 3 | none | 17 | 279 MB | 1,854 ms (1,732 to 1,928) |
| vaex | 4.20.0 | 2 | none | 119 | 1,514 MB | 1,409 ms (1,202 to 1,766) |
| ibis-framework | 12.0.0 | 1 | 10.x, 11.x, 12.x | 8 | 26 MB | 312 ms (249 to 505) |
| dlt, with pyarrow | 1.32.0 | 22 | none | 38 | 207 MB | 583 ms (516 to 668) |
| kedro | 1.8.0 | 10 | 1.x 2025-07-22 | 38 | 26 MB | 130 ms (92 to 337) |
| datasets | 5.2.0 | 15 | 4.x 2025-07, 5.x 2026-06 | 24 | 297 MB | 1,246 ms (877 to 1,435) |
| lancedb | 0.41.0 | 19 | none | 16 | 417 MB | not measured: the process dies on this CPU |
| mlflow | 3.18.0 | 25 | 3.x 2025-06-10 | 89 | 630 MB | 1,750 ms (1,470 to 1,899) |
| pydantic | 2.14.3 | 14 | none | 5 | 8 MB | 72 ms (59 to 89) |
| ray, with pyarrow | 2.60.0 | 17 | none | 19 | 379 MB | 656 ms (426 to 1,010) |
| ddtrace | 4.17.0 | 121 | 3.x 2025-02-20, 4.x 2025-11-20 | 7 | 34 MB | 337 ms (232 to 421) |
| diskcache | 5.6.3 | 0 | none | 1 | 1 MB | 35 ms (27 to 45) |
| fastapi, fastui, uvicorn | 0.163.1 (fastui 0.9.0: 0 releases) | 126 | none | 17 | 14 MB | 679 ms (522 to 761) |
| fastmcp (`fastmcp>=3,<4`, as the extra) | 3.4.11 | 56 | 3.x 2026-02-18, 4.x 2026-08-31 | 68 | 66 MB | 1,380 ms (1,310 to 1,584) |
| openlineage-python and openlineage-sql | 1.55.0 | 18 | none | 18 | 20 MB | 475 ms (383 to 522) |
| opentelemetry-sdk | 1.45.2 | 12 | none | 4 | 3 MB | 93 ms (75 to 138) |
| pandera | 0.36.0 | 17 | none | 10 | 12 MB | 82 ms (66 to 188) |
| narwhals | 2.28.0 | 21 | 2.x 2025-07-28 | 1 | 3 MB | 99 ms (84 to 108) |
| pyarrow | 26.0.1 | 7 | eight (19.x to 26.x) | 1 | 166 MB | 188 ms (169 to 211) |
| rich (`rich.progress`) | 15.0.0 | 6 | 14.x, 15.x | 4 | 8 MB | 91 ms (59 to 197) |
| slack-sdk | 3.47.0 | 11 | none | 1 | 3 MB | 132 ms (122 to 153) |
| tqdm | 4.70.1 | 11 | none | 1 | 1 MB | 83 ms (78 to 119) |
| ipython | 9.18.1 | 18 | 9.x 2025-02-28 | 16 | 49 MB | 120 ms (95 to 179) |
| graphviz and networkx | 0.21 and 3.7 | 0 and 3 | none | 2 | 9 MB | 205 ms (161 to 250) |

**Hamilton changes forced by upstream releases**, 24 months to 2026-11-17, found by reading every commit in that window that touches `hamilton/plugins/`, `pyproject.toml` or the main CI workflow, and keeping those whose message or diff responds to a library release (licence-header, lint and rename sweeps excluded): pandas 4 (`157ecd60` and `4dbaf085`, February 2026; `2206e09d` and `6f1f9df5`, after the 1.90.0 tag); Polars 1 event in the window (Polars 2.0: `6f1f9df5` cap, `a9ce4117` and `1a31768d` readers) on top of the Polars 1.0 split made before it, which left three parallel module sets; ddtrace 2 (`fbded2f6` pin, March 2025; `e10f6b27`, April 2026); dask 1 (`e3573a11`); dlt 1 (`fe481ad1`); numpy 1 (`5d57508c`, removing `numpy<2` pins); Plotly 1 (`76758bc8`); PySpark 1 (the `pandas<3.1` cap in `pyproject.toml`); all others 0. `f0b80121` (Spark on Python 3.14) responds to a Python release, not a library release.

**Every name in `registry.ExtensionName` and every module under `hamilton/plugins/`.** Kinds: **E** extension in `ExtensionName`, loaded by `registry.initialize()`; **V** version-specific module that an extension imports; **U** user-imported module; **I** IPython extension loaded with `%load_ext`; **P** package with a console script; **S** deprecated shim. Lines are counted with `wc -l`. "Weight" and "Cadence need" repeat the library facts above for the library the module imports; "as Polars" and similar point to the row of the integration's main module. "Verdict" says extra or separate distribution; "extra (add)" means no extra exists today and one should be added under the integration's name.

| Module | Kind | Imports at module level (including those inside `try`) | Extra today | Lines | Weight: size, import median | Cadence need: forced changes in 24 months; library releases in 12 months | Known conflicts | Verdict and why |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `yaml_extensions` | E | PyYAML | none | 89 | 3 MB, 26 ms | 0; 0 | none found | extra (add): light, no cadence need |
| `matplotlib_extensions` | E | matplotlib | none | 108 | 132 MB, 710 ms | 0; 5 | none found | extra (add): heavy to import, no cadence need |
| `numpy_extensions` | E | numpy | core dependency until Ticket 21 | 105 | 54 MB, 122 ms | 1; 13 | numpy 2.5 requires Python 3.12, so 3.11 users get an older numpy | extra `numpy` (Ticket 21): one forced change, small |
| `pandas_extensions` | E | pandas, pyarrow, fsspec | core dependency until Ticket 21 | 1,807 | 268 MB, 495 ms | 4; 9, new major 3.x | `pyspark` extra caps pandas below 3.1; table reader broken on pandas 3.1 in 1.90.0 | **separate distribution** with `h_pandas`: 4 forced changes, 2,064 lines |
| `plotly_extensions` | E | plotly (kaleido for static export) | `plotly-static` | 150 | 42 MB, 60 ms | 1; 9, two new majors | `kaleido!=1.5.1`; removed `write_image` argument, fix unreleased | extra: one forced change, small |
| `polars_extensions` | E | polars, xlsxwriter | none | 73 | 345 MB, 263 ms (`rtcompat` build) | 1 event plus three parallel module sets; 24, new major 2.x | no free-threaded wheel; readers broken on Polars 2 in 1.90.0 | **separate distribution** with all Polars modules: parallel code per major version, 3,177 lines |
| `polars_lazyframe_extensions` | E | polars | none | 77 | as Polars | as Polars | as Polars | with the Polars distribution |
| `pyspark_pandas_extensions` | E | pyspark | `pyspark` | 47 | 741 MB, 708 ms | 1; 14 | PySpark 4.3.0 fails to import with pandas 3.1.1 (measured), hence `pandas<3.1`; needs a JRE | extra: the conflict is the user's and a split would carry it; one forced change |
| `spark_extensions` | E | pyspark, pandas | `pyspark` | 105 | 479 MB, 201 ms (`pyspark.sql`) | as above | as above | extra, with `h_spark` |
| `dask_extensions` | E | dask | `dask`, `dask-*` | 47 | 279 MB, 904 ms | 1; 13 | vaex pins `dask<2024.9` | extra: one forced change, small |
| `geopandas_extensions` | E | geopandas | none | 49 | 247 MB, 599 ms | 0; 4 | none found | extra (add) |
| `xgboost_extensions` | E | xgboost | none | 91 | 453 MB, 493 ms | 0; 6, new major 3.x | xgboost 3.4 requires Python 3.12; tests skipped on 3.14 and later (`tests/conftest.py`) | extra (add) |
| `lightgbm_extensions` | E | lightgbm | none | 99 | 176 MB, 307 ms | 0; 1 | tests skipped on 3.14 and later | extra (add) |
| `sklearn_plot_extensions` | E | scikit-learn, matplotlib | none | 129 | 279 MB, 1,854 ms | 0; 3 | none found | extra (add) |
| `vaex_extensions` | E | vaex, numpy | `vaex`, Python below 3.13 | 51 | 1,514 MB, 1,409 ms | 0; 2 | vaex-core 4.20.0 pins `dask<2024.9` and `pandas<3` (below Python 3.15), so CI installs it outside the resolution on 3.11 and 3.12 only; the `python_version < '3.13'` marker is out of date, since vaex-core 4.20.0 (2026-11-05) ships wheels up to CPython 3.15 | extra: the conflict is environmental; upstream released twice in 12 months |
| `ibis_extensions` | E | ibis-framework | none | 93 | 26 MB, 312 ms | 0; 1, three new majors | none found | extra (add) |
| `dlt_extensions` | E | dlt, pandas, pyarrow | none | 161 | 207 MB, 583 ms | 1; 22 | dlt requires Python below 3.15; orjson has no free-threaded build | extra (add), with a Python marker: one forced change |
| `kedro_extensions` | E | kedro | none | 117 | 26 MB, 130 ms | 0; 10, new major 1.x | tests skipped on 3.14 and later | extra (add), with `h_kedro` |
| `huggingface_extensions` | E | datasets, lancedb | none | 236 | datasets 297 MB, 1,246 ms; lancedb 417 MB, not timed | 0; 15 and 19, two new majors of datasets | lancedb tests skipped on 3.14 and later; lancedb kills an eager import on CPUs without AVX2 (measured here) | extra (add) |
| `mlflow_extensions` | E | mlflow | none | 216 | 630 MB, 1,750 ms | 0; 25, new major 3.x | test group pins `mlflow>=3` to Python 3.13 and below; mlflow caps pyarrow below 26 | extra (add), with `h_mlflow`: heaviest import, no forced change |
| `pydantic_extensions` | E | pydantic | `pydantic` | 98 | 8 MB, 72 ms | 0; 14 | none found | extra |
| `polars_pre_1_0_0_extension` | V | polars, xlsxwriter | none | 864 | as Polars | as Polars | Polars below 1.0; its own warning schedules removal for Hamilton 2.0 | with the Polars distribution, or removed at 2.0 |
| `polars_post_1_0_0_extensions` | V | polars, xlsxwriter | none | 957 | as Polars | as Polars | Polars 1.x | with the Polars distribution |
| `polars_post_2_0_0_extensions` | V | (through `polars_post_1_0_0_extensions`) | none | 168 | as Polars | as Polars | Polars 2.x | with the Polars distribution |
| `polars_lazyframe_pre_2_0_0_extensions` | V | polars | none | 268 | as Polars | as Polars | Polars below 2.0 | with the Polars distribution |
| `polars_lazyframe_post_2_0_0_extensions` | V | polars | none | 156 | as Polars | as Polars | Polars 2.x | with the Polars distribution |
| `polars_implementations` | S | (`h_polars`) | none | 28 | as Polars | none | emits `FutureWarning` | remove at 2.0 |
| `jupyter_magic` | I | IPython | none | 622 | 49 MB, 120 ms | 0; 18, new major 9.x | none found | extra (add): loaded by IPython, needs no discovery |
| `h_dask` | U | dask, numpy, pandas | `dask` | 331 | 346 MB, 1,214 ms (`dask[complete]`) | 1; 13 | as dask (dask's own dependencies bring numpy and pandas) | extra |
| `h_ddog` | U | ddtrace | `datadog` | 521 | 34 MB, 337 ms | 2; 121, two new majors | 1.90.0 requires `ddtrace<3.0` though 4.x is current; a ddtrace pre-release is needed on Python 3.15 | extra: meets the cadence criterion but is one small module; a core patch release fixes it |
| `h_diskcache` | U | diskcache | `diskcache` | 166 | 1 MB, 35 ms | 0; 0 | none found | extra |
| `h_kedro` | U | kedro | none | 152 | as kedro | as kedro | as kedro | extra (add) |
| `h_logging` | U | standard library only | none needed | 454 | none | none | none | stays in `apache-hamilton`, no extra |
| `h_mlflow` | U | mlflow (matplotlib and plotly when installed) | none | 336 | as mlflow | as mlflow | as mlflow | extra (add) |
| `h_narwhals` | U | narwhals | none | 134 | 3 MB, 99 ms | 0; 21, new major 2.x | none found | extra (add) |
| `h_openlineage` | U | openlineage-python, attrs (openlineage-sql inside a function) | `openlineage` | 769 | 20 MB, 475 ms | 0; 18 | openlineage-sql publishes no Windows wheel | extra: no forced change |
| `h_opentelemetry` | U | opentelemetry | none | 167 | 3 MB, 93 ms | 0; 12 | none found | extra (add) |
| `h_pandas` | U | pandas (through `pandas_extensions`) | as pandas | 257 | as pandas | as pandas | as pandas | with the pandas distribution |
| `h_pandera` | U | pandera | `pandera` | 136 | 12 MB, 82 ms | 0; 17 | pandera is also imported eagerly by `hamilton/data_quality/default_validators.py` | extra; the eager core import moves under R8 |
| `h_polars` | U | polars | none | 304 | as Polars | as Polars | as Polars | with the Polars distribution |
| `h_polars_lazyframe` | U | polars | none | 282 | as Polars | as Polars | as Polars | with the Polars distribution |
| `h_pyarrow` | U | pyarrow | none | 56 | 166 MB, 188 ms | 0; 7, eight new majors | none found | extra (add) |
| `h_pydantic` | U | pydantic | `pydantic` | 127 | 8 MB, 72 ms | 0; 14 | none found | extra |
| `h_ray` | U | ray | `ray`, Python below 3.15 | 242 | 379 MB, 656 ms | 0; 17 | ray publishes no CPython 3.15 wheel (newest is cp314) | extra, with its Python marker |
| `h_rich` | U | rich | `rich` | 142 | 8 MB, 91 ms | 0; 6, two new majors | none found | extra |
| `h_schema` | U | pyarrow (pyspark inside a function) | none | 493 | 166 MB, 188 ms | 0; 7 | none found | extra (add) |
| `h_slack` | U | slack-sdk | `slack` | 100 | 3 MB, 132 ms | 0; 11 | none found | extra |
| `h_spark` | U | pyspark, pandas, numpy | `pyspark` | 1,380 | 741 MB, 708 ms (`pyspark.pandas`) | 1; 14 | as PySpark | extra: large, but one forced change in 24 months |
| `h_threadpool` | U | standard library only | none needed | 125 | none | none | none | stays in `apache-hamilton`, no extra |
| `h_tqdm` | U | tqdm | `tqdm` | 128 | 1 MB, 83 ms | 0; 11 | none found | extra |
| `h_vaex` | U | vaex, numpy, pandas | `vaex` | 129 | as vaex | as vaex | as vaex (vaex-core's own dependencies bring numpy and pandas) | extra |
| `h_experiments/` | P | fastapi, fastui, pandas, pydantic (uvicorn inside a function) | `experiments` | 785 | 14 MB, 679 ms (fastapi, fastui, uvicorn) | 0; fastapi 126, fastui 0 | fastui has had no release in 12 months; needs pandas declared in its extra after Ticket 21 | extra |
| `h_mcp/` | P | fastmcp (graphviz, numpy, pandas and polars inside `try` or functions) | `mcp` | 935 | 66 MB, 1,380 ms (fastmcp); graphviz and networkx 9 MB, 205 ms | 0; 56, two new majors | the extra caps `fastmcp<4` while 4.x has been current since 2026-08-31 | extra |

Modules that import pandas or numpy at module level get them today from the core's dependencies. For `h_dask`, `h_vaex` and `vaex_extensions` the library's own dependencies bring them too; `h_experiments/server.py` imports pandas and its extra (`fastapi`, `fastui`, `uvicorn`) does not bring it, so once Ticket 21 removes pandas from the core the `experiments` extra must declare it.

### Options

- **Q2-A. Every integration stays an extra** (the counter-hypothesis), with patch releases of the core when an integration breaks.
- **Q2-B. Selective split: Polars and pandas become providers** (`apache-hamilton-polars`, `apache-hamilton-pandas`), every other integration stays an extra, and each release wave (core and providers together) is voted in one thread, as Airflow does.
- **Q2-C. One distribution per integration,** as Airflow does for its 109 providers.

| Criterion | Q2-A | Q2-B | Q2-C |
| --- | --- | --- | --- |
| A broken integration is fixed for users without a core release | no | for Polars and pandas | yes |
| Release votes per year at Hamilton's present volume of fixes | lowest, if patch releases are batched | one more per wave only when a provider changes | many; one per changed provider unless batched |
| Compatibility ranges to test (core × provider) | none | two | about 25 |
| Old library versions can be dropped without a core major | no | for Polars and pandas | yes |
| Install command for users | unchanged | unchanged: `apache-hamilton[polars]` depends on the provider | unchanged with extras |
| Import paths | unchanged | unchanged if `hamilton.plugins` becomes a shared namespace (Airflow's `airflow.providers` model) | same |
| Fits the outline's "small core" and "separate where justified" | partly | yes | over-splits small integrations |

Ranking: **Q2-B, then Q2-A, then Q2-C.** Q2-C pays the fixed cost of a distribution about 25 times for integrations whose code changed because of their library once or never in two years. Between B and A the difference is whether the two integrations that churn with their library can ship on their own schedule.

### Strongest counter-argument

"The root cause is the core's release frequency, not packaging. Two core releases since entering the Incubator left four integrations broken with fixes merged; a patch-release practice fixes all four, not two, at no new packaging cost. A split adds distributions that each need a vote, a version and a compatibility matrix, and the PPMC has shown that four distributions take seven weeks to release." This is strong, and the evidence for its first half is the same evidence that motivates the split. The reasons it does not win outright: after Ticket 21 the core no longer depends on pandas or numpy, so it can stay stable while the dataframe integrations move at pandas' and Polars' pace (Polars published 24 releases in 12 months); a provider can drop support for old library versions on its own schedule, which would let the Polars provider delete one of its three parallel module sets without a core major; and a provider release is a smaller artifact to verify. Q2-B does not replace patch releases; it needs them for every other integration. If the PPMC cannot commit to wave votes, Q2-A is the better choice.

### What a split would require (later work, not this Ticket)

Discovery under Question 1 first, since the core must find code it does not ship. Then, per provider: its own `pyproject.toml` with `apache-hamilton>=X`, its modules moved into a package under a shared `hamilton.plugins` namespace (Airflow ships `airflow.providers.postgres` as a flit module of a namespace that the core's `__init__.py` extends), the core's extra repointed to the provider, a CI job testing the provider against the oldest supported and the current core, and a release recipe that adds it to the wave. The `src/` layout move of ADR 2611-14 would carry the providers' source trees.

## Three frames

- **The plugin author** wants one obvious way to make an extension work without asking the core to change, and to find out early that it is incompatible. Today an author outside the project cannot do this at all; under R1 to R5 the author writes one entry point and one manifest, and gets a warning or error that names the contract version. Under B the author still has to edit the core.
- **The maintainer** wants determinism, a small public surface and few release streams. R4 replaces "list order" with written rules; the contract version keeps the public surface explicit; Q2-B adds two release streams, bounded by wave voting. The maintainer pays for C with a contract to keep, and for B with nothing new.
- **The operator** wants `import hamilton` to cost only what the graph uses, never to break because of an unrelated library, and to see what was loaded. R3 and R7 give that: nothing heavy is imported until needed, a disable list and the old global switch remain, and `hamilton extensions` lists what is installed. The operator's install command does not change under Q2-B.

## Gaps and assumptions

- No data on how many users use each integration. PyPI download statistics do not record extras; this report weighs integrations by code, churn and conflicts, not by users.
- Third-party demand for extensions rests on code search, which indexes a subset of default branches.
- The PPMC's capacity for release votes is not known to this report; the Q2 ranking depends on it.
- Import timings were taken on an old CPU with other work running; the ranges are wide and the absolute numbers will be lower on current hardware. The ordering of heavy and light libraries is the usable result. Polars was timed with its `rtcompat` runtime, which is not the build most users get, and lancedb could not be timed.
- The cost of reading the entry-point group once per process was not measured; pytest reads all distributions twice per run and no issue in its tracker reports the cost.
- The forced-change counts depend on reading commit messages; a change made silently inside a larger commit would be missed.
- Airflow's provider files were read at the core's 3.4.0 tag, not at each provider's own release tag.
- The decision is a comparison of documented systems, as the plan expected; it did not need novel research.

## Decisions for the owner

Each decision carries a recommendation. ADR 2611-17 will record the owner's statement.

1. **Discovery model.** Recommendation: option C, entry points with static manifests and lazy loading, rules R1 to R8. Alternative: B, if the owner rejects every split in decision 6.
2. **The extension contract becomes public.** Recommendation: yes, under the group name `hamilton.extensions`, starting at contract version 1, with the manifest fields of R2 and nothing more.
3. **Default loading in 2.0.** Recommendation: lazy by default (R3); `HAMILTON_AUTOLOAD_EXTENSIONS=0` keeps meaning "nothing automatic"; a migration note for code that reads the registries directly.
4. **Collision policy.** Recommendation: R4 as written: an error for duplicate extension names and for duplicate dataframe types, a fixed and logged order for materializer ties.
5. **Compatibility policy.** Recommendation: R5: packaging floor plus a contract version checked before import, a core-side table of blocked provider versions, and skip-with-warning unless the user asked for the extension.
6. **Which integrations earn a distribution.** Recommendation: Q2-B, Polars and pandas, as later work after Question 1's discovery and Ticket 21 land; every other integration stays an extra. Alternative: Q2-A.
7. **Release practice.** Recommendation: take to the PPMC one vote thread per release wave covering the core and any providers, and patch releases when an integration is broken against a new release of its library.
8. **Provider import paths.** Recommendation: keep the `hamilton.plugins.*` paths by making `hamilton.plugins` a namespace that providers extend, as Airflow does with `airflow.providers`, so no user import changes.
9. **Extras for integrations that have none.** Recommendation: add an extra named after each integration marked "extra (add)" in the inventory, as a separate change.

Independent of these decisions, two small fixes surfaced that stand on their own and could be proposed for `main`: the `vaex` extra's `python_version < '3.13'` marker is out of date, and the `mcp` extra excludes the current major of fastmcp.

## Appendix

### Queries per facet

The helpers' searches, each facet with at least two formulations (code greps at the tag unless marked).

- **pytest and pluggy.** Discovery: `load_setuptools_entrypoints`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD`, `disable_plugin_autoload`, `pytest11`, `entry_points`, `consider_module`, `consider_conftest`. Naming: `def register`, `get_canonical_name`, `builtin_plugins`. Collision: `already registered`, `Plugin name already`, `DEPRECATED_EXTERNAL_PLUGINS`; tracker searches "Plugin already registered", "entry point name conflict plugin", "duplicate plugin entry point", "load order plugins". Compatibility: `minversion`, `required_plugins`, `warn_on_impl`, `historic`, `requires_dist`, `canonicalize_name`; tracker "required_plugins", "unknown hook", "incompatible plugin". Lazy loading: `essential_plugins`, `set_blocked`, `is_blocked`; tracker "autoload", "slow", "startup time", "import time", "plugin loading performance". Failure: `PluginImportFailure`, `Error while loading plugin`, `skipped plugin`. Distribution: `scripts/update-plugin-list.py`, changelog "merged into the core", PyPI JSON for pytest-pastebin, pytest-xdist, pytest-subtests.
- **Airflow.** Discovery: `entry_points_with_dist`, `apache_airflow_provider`, `provider.yaml`, `walk_packages`, `airflow.providers.__path__`, `LAZY_LOAD_PROVIDERS`. Naming: `connection-types`, `hook-class-names`, `package-name`, the schema files. Collision: `already been registered`, `already registered`, `duplicate registration`, `sorted(self._provider_dict`. Compatibility: `MIN_PROVIDER_VERSIONS`, `BLOCKED_PROVIDER_MIN_VERSIONS`, `MIN_AIRFLOW_VERSION`, `needs Apache Airflow`, a tally of `"apache-airflow>=` over provider manifests; dev list "minimum airflow version providers", "2.11 providers support". Lazy loading: `lazy_discover_providers`, `lazy_load_plugins`, `LazyDictWithCache`, `_import_info_from_all_hooks`, `provider_command.py`. Failure: `import_string`, `log_import_warning`, `log_optional_feature_disabled`, `ValidationError`. Distribution: root and core manifests, `PROVIDERS_COMPATIBILITY_TESTS_MATRIX`, "every 2 weeks", PyPI release dates, tracker "Status of testing Providers that were prepared on". Pain points: tracker "providers manager", "provider discovery slow", "ProvidersManager slow", "does not conform to the provider_info schema".
- **stevedore and importlib.metadata.** Discovery: `environ`, `STEVEDORE`, `.disable`, `_cache.py` in full; bugs 1942209 and 1627906. Naming: `user-visible`, `unique`, `namespace`; the PyPA specification for `unique`. Collision: `multiple`, `duplicate`, `conflict`, `MultipleMatches`, release notes 5.6.0 and 5.9.1. Compatibility: `verify_requirements`, `no-op`, `def extras` at 4.0.0, 5.5.0, 5.6.0 and 5.10.0; CPython `def resolve`, `def require`; bugs 1897969, 1874001, 1560361. Lazy loading: `_load_one_plugin`, `list_entry_points`, `names`, `sphinxext.py`. Failure: `LOG.`, `raise`, `propagate`; bugs 1298529, 1611387, 1994051. Distribution: `openstack`, `ceilometer`, `third.party`, `in-tree`, `distributed`. Pain points: all 47 bugs on Launchpad, all release notes.
- **Hamilton.** Code: `registry.initialize`, `load_extension`, `register_adapter`, `LOADER_REGISTRY`, `hamilton.plugins` outside `hamilton/plugins/`, `import_module` in `ui/sdk`. GitHub code search: `"registry.register_adapter" hamilton`, `"from hamilton import registry"`, `"hamilton.registry" register_types`, `"HAMILTON_AUTOLOAD_EXTENSIONS"`, each excluding the Hamilton repositories. Mailing lists: `[VOTE]` on dev@hamilton.apache.org and `hamilton` on general@incubator.apache.org through the lists.apache.org API.

### Scripts used for the measurements

Kept outside the repository; reproduced here in outline so the runs can be repeated.

- **Materializer names per module:** parse each module under `hamilton/plugins/` and `hamilton/io/default_data_loaders.py` with `ast`, find every method named `name`, and collect the string constant it returns.
- **Library weight:** for each row, `uv venv -p 3.12`, `uv pip install <library>`, count `importlib.metadata.distributions()`, `du -sm` of `site-packages`, then one warm-up and seven runs of `python -I -c "import time; t=time.perf_counter(); <imports>; print(...)"`.
- **Autoload cost:** the environment described under "What eager loading costs", then ten alternating pairs of `python -c "<timed import hamilton.driver>"` with and without `HAMILTON_AUTOLOAD_EXTENSIONS=0`, and one `python -X importtime -c "import hamilton.driver"` profile.
- **Forced changes:** `git log --since=2024-11-17` over `hamilton/plugins/`, `pyproject.toml`, `.github/workflows/hamilton-main.yml` and `tests/conftest.py` on `31b3a832`, each commit's message and diff read.
