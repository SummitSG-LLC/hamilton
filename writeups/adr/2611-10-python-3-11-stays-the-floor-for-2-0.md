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

# 2611-10. Python 3.11 stays the minimum for Hamilton 2.0

**Status:** Accepted (2026-11, a starting decision of the Hamilton 2.0 effort; the outline is apache/hamilton discussion #1645, "Hamilton 2.0: Architecture and Roadmap Reassessment")

## Context

Hamilton 1.x declares `requires-python = ">=3.11, <4"`. A major version is the usual moment to raise the minimum, and two things 2.0 wants come from newer Pythons: free-threading, supported but optional from 3.14, and newer typing and annotation features.

PyPI downloads of `apache-hamilton` by Python version, 2026-10-11 to 2026-11-09 (168,380 downloads with a known version):

| Python | Share of downloads |
|---|---|
| 3.10 | 11.9% |
| 3.11 | 6.0% |
| 3.12 | 60.0% |
| 3.13 | 7.0% |
| 3.14 | 14.6% |
| 3.15 | 0.5% |

The outline's section "Features usable without raising the minimum" lists the newer-Python features 2.0 has a use for, each with a path that works on 3.11:

| Feature | Compatibility path | Useful scope |
|---|---|---|
| 3.14 annotation inspection | `typing_extensions>=4.13`: format-aware `get_annotations`, `Format`, `evaluate_forward_ref` | One annotation-resolution boundary and better unresolved-reference diagnostics |
| 3.15 `TypeForm` | `typing_extensions>=4.13` | APIs accepting type expressions such as `list[int]` and unions, rather than only classes |
| 3.15 closed/extended `TypedDict` | Current PEP 728 behavior in `typing_extensions>=4.13` | Provider metadata and structured diagnostics with explicit extra-item policies |
| 3.15 named sentinels | `typing_extensions>=4.16` for current `sentinel` behavior | Distinguishing missing values from valid `None`, including copying/pickling |
| 3.15 immutable mappings | Third-party `frozendict` offers similar functionality; not an exact builtin backport | Graph indexes and metadata/configuration snapshots |
| 3.14 Zstandard compression | `backports.zstd` below 3.14 | Optional artifact/event compression |

The outline concludes: "No required feature found here warrants raising the core minimum. Free-threading itself cannot be supplied by a library backport."

## Decision

Hamilton 2.0 keeps `requires-python = ">=3.11"`. Features of newer Pythons are used through the compatibility paths in the table. Correctness of the core on a free-threaded build is tested as its own target, on a free-threaded CPython 3.14 job in CI, and is not a reason to raise the minimum.

The decision may be revised on evidence: a feature 2.0 needs that has no path on 3.11, or download shares that have moved.

## Consequences

- Code that uses a feature from the table depends on the `typing_extensions` release that carries it (4.13, or 4.16 for sentinels), which is above today's requirement of `typing_extensions > 4.0.0`. The change that first uses such a feature raises that requirement.
- The backports are not the newer interpreter. The outline notes that the annotation backport approximates `FORWARDREF`/`STRING` behavior on older interpreters and does not reproduce deferred annotation execution on 3.11, and that `frozendict` is not an exact backport of the 3.15 builtin. Code behind these paths is tested on 3.11 as well as on the newest Python in the CI matrix.
- Free-threading is unavailable to users on 3.11 to 3.13, so nothing in the core may require it. Threaded execution stays an explicit choice.
- The CI matrix keeps five Python versions, 3.11 to 3.15, plus the free-threaded job.

## Alternatives considered

- **Raise the minimum to 3.12.** Rejected: it drops the 6.0% of downloads that come from 3.11, and no feature in the table needs 3.12.
- **Raise the minimum to 3.14**, the first version where free-threading is supported. Rejected: about 85% of downloads come from Pythons below 3.14 (73.0% from 3.11 to 3.13, which the current minimum supports, and 11.9% from 3.10). Free-threading is optional on 3.14 too, so the core would still have to work with the GIL enabled.
