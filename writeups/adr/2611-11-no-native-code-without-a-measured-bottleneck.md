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

# 2611-11. No native code in Hamilton 2.0 until a benchmark shows a bottleneck

**Status:** Accepted (2026-11, a starting decision of the Hamilton 2.0 effort; the outline is apache/hamilton discussion #1645, "Hamilton 2.0: Architecture and Roadmap Reassessment")

## Context

The analysis that preceded the outline proposed native (Rust) work as one of its ideas. The outline moved it to the research backlog: "Keep on the research backlog until a measured bottleneck justifies it. Free-threaded Python already provides a useful CPU-parallel path."

Measurements at the `2.0` branch point (commit `ef88b1e9` of apache/hamilton `main`, one machine, CPython 3.15.0, a generated layered graph of integer nodes):

| What | Measured | Where the time goes |
|---|---|---|
| Build | 103 ms per 1,000 nodes | `typing.get_type_hints` and `inspect.signature` |
| Execute, default path | 13 to 22 µs per node | |
| Execute, task-based path with the synchronous executor | 206 ms for 1,000 nodes, against 12.5 ms on the default path | |
| `import hamilton.driver` | 431 ms | pandas 287 ms, numpy 78 ms |

None of these costs is in a compute kernel of Hamilton's own. Build time is spent in standard-library introspection, import time in two third-party packages, and the task-based path is about 16 times slower than another pure-Python path over the same graph. Each has a remedy in Python: resolve annotations once, stop importing pandas and numpy from the core, and replace the task-based coordinator.

The release tooling assumes one pure-Python wheel per distribution. The build backend is `flit_core`, and `scripts/verification-script.sh`, `scripts/apache_release_helper.py` and `scripts/README.md` name the artifact `<package>-<version>-py3-none-any.whl`.

## Decision

Hamilton 2.0 contains no compiled or native code. The question reopens only on a result from the `benchmarks/` harness whose profile names a bottleneck that a change in Python cannot remove.

## Consequences

- The distribution stays one `py3-none-any` wheel, and the release scripts, the ASF source release and installation on any platform keep working unchanged.
- Performance work on 2.0 is algorithmic and structural, and every claim about it is a measured verdict from the harness.
- CPU parallelism comes from free-threaded Python and from the libraries users call, which is why CI checks that the core suite runs with the GIL disabled.
- If native code is justified later, the release tooling has to learn platform wheels first. The outline notes that 3.15's `abi3t` "does not provide supported stable-ABI targeting for 3.14t", so free-threaded 3.14 would need its own wheels.

## Alternatives considered

- **Write the graph or scheduling kernel in native code now.** Rejected: no measurement shows a kernel that is the limit, and it would trade the single pure-Python wheel for per-platform builds before the runtime's design is settled.
- **Compile selected Python modules ahead of time**, leaving the source in Python. Rejected for the same reasons: it also needs per-platform wheels, and the measured costs are in calls and imports that compiling Hamilton's own modules would not remove.
