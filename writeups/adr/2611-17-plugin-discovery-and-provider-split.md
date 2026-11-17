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

# 2611-17. How Hamilton discovers its extensions, and which integrations get their own distribution

**Status:** Proposed (2026-11, awaiting the owner's decision; the evidence is the survey [`writeups/surveys/plugin-discovery-and-provider-split.md`](../surveys/plugin-discovery-and-provider-split.md); the outline is apache/hamilton discussion #1645, "Hamilton 2.0: Architecture and Roadmap Reassessment")

This record holds the decisions the survey asks for. Until the owner decides, the Decision section lists each question with the survey's recommendation. When the owner has decided, the section is rewritten from the owner's statement, the status becomes Accepted, and the statement is cited here.

## Context

Importing the decorator package calls `registry.initialize()`, which imports `hamilton.plugins.<name>_extensions` for each of the 21 names in `registry.ExtensionName`, unless `HAMILTON_AUTOLOAD_EXTENSIONS` is `0`. In an environment with the test dependency group and the `dask` and `pyspark` extras, `import hamilton.driver` took a median of 5.6 s with autoloading and 1.0 s without (CPython 3.12, ten alternating runs each, ranges not overlapping; the survey gives the setup). A third party cannot add an extension without changing the core. Several extensions already share materializer names (five provide `parquet`), resolved by type with the last registered winning, so the load order is part of the behavior.

The outline asks to replace the eager imports with discovery and explicit loading, with rules for collision, compatibility and registration, and to settle which integrations need independent distributions. The 2.0 prototype leaves both out until this record is decided (ADR 2611-12).

The survey compared pytest 9.2.0, Airflow 3.4.0 providers and stevedore 5.10.0. Only Airflow keeps what exists separate from what is imported, through a metadata callable per provider; all three let a duplicate name win silently in at least one path; runtime compatibility checks are thin in all three. For distributions, the survey found Polars and pandas to be the only integrations with both repeated upstream-forced changes and more than a thousand lines of code; both are broken in the newest Hamilton release against their library's newest release, with the fixes merged and waiting for a core release. Each release of each distribution needs a podling and an Incubator PMC vote, measured at three to seven weeks per round.

## Decision

Pending. The questions, each with the survey's recommendation:

1. **Discovery model.** Recommended: entry points in the group `hamilton.extensions`, each pointing to a static manifest readable without importing the extension or its library, with the core's own extensions declared the same way; extensions loaded lazily. Alternative: the same manifests listed in the core, without entry points.
2. **Public extension contract.** Recommended: the manifest becomes a public, versioned contract (contract version 1), with only the fields the survey lists.
3. **Default loading in 2.0.** Recommended: lazy loading by default, on materializer resolution for a declared type, on a registry lookup for a declared type, or on explicit request; `HAMILTON_AUTOLOAD_EXTENSIONS=0` keeps meaning that nothing is loaded automatically.
4. **Collisions.** Recommended: duplicate extension names and duplicate dataframe types are errors naming both distributions; materializer ties keep "registered last wins" over a fixed registration order (the core's own extensions in today's `ExtensionName` order, then third-party extensions by name, then adapters the user registers in code), with the existing warning.
5. **Compatibility.** Recommended: a packaging floor `apache-hamilton>=X` plus a contract version checked before import; a core-side table of blocked provider versions; skip with a warning unless the user asked for the extension, then raise.
6. **Distributions.** Recommended: Polars and pandas become providers, as later work after discovery and the removal of the data stack from the core; every other integration stays an extra. Alternative: no provider, with patch releases.
7. **Release practice.** Recommended: propose to the PPMC one vote per release wave covering the core and any providers, and patch releases when an integration breaks against a new release of its library.
8. **Provider import paths.** Recommended: keep `hamilton.plugins.*` by making `hamilton.plugins` a namespace that providers extend.
9. **Missing extras.** Recommended: add an extra for each integration that has none, as a separate change.

## Consequences

To be written from the owner's decision. If the recommendations are accepted:

- The eager list in `registry.initialize()`, the eager pandera import in `hamilton/data_quality/default_validators.py`, and the extension-loading assertions are replaced by manifest-based discovery; code that reads the registries directly needs the migration note for explicit loading.
- The extension manifest and the entry-point group become public API, versioned by the contract version.
- Two provider distributions are added later, each with a compatibility range against the core tested in CI and released in the same vote as the core.

## Alternatives considered

- **Keep the eager fixed list with its opt-out.** Rejected in the survey's ranking: it imports every installed library the core knows, measured at about 4.6 s in a full environment, and can fail the import because of a library the graph never uses.
- **Entry points loaded eagerly, as pytest does.** Rejected in the ranking: it keeps the eager cost and extends it to third-party code.
- **One distribution per integration, as Airflow does.** Rejected in the ranking: it pays the fixed cost of a distribution about 25 times for integrations whose code changed because of their library once or never in two years.
