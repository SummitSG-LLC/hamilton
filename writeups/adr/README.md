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

# Architecture Decision Records

Each file here records one design decision: the context that forced it, what was decided, what
it costs, and the alternatives that were rejected. The records outlive the commits and review
threads that produced them, so a later change can tell a deliberate choice from an accident.

- File name: `YYMM-NN-short-title.md`, numbered in order. Numbers are never reused.
- Status: `Accepted`, `Superseded by YYMM-NN`, or `Deprecated`. An accepted record is not edited to
  change its decision; write a new record that supersedes it.
- Sections: Status, Context, Decision, Consequences, Alternatives considered.

| ADR | Title |
| ----- | ------- |
| [2609-01](2609-01-staged-sql-dataset-identity.md) | Staged, opt-in datasource identity for OpenLineage SQL datasets |
| [2609-02](2609-02-sql-metadata-keeps-1-0-0-filing.md) | SQL metadata keeps the 1.0.0 query/table_name filing; intent travels in `operation` |
| [2609-03](2609-03-resolving-sql-writes-and-statements.md) | How datasource-mode lineage resolves what a SQL write names |
| [2609-04](2609-04-sqlite-attached-databases.md) | SQLite attached databases are named by their own file |
| [2611-01](2611-01-polars-database-sql-metadata.md) | Polars database I/O records `sql_metadata` beside `file_metadata`; the pre-1.0 integration stays legacy-only |
| [2611-10](2611-10-python-3-11-stays-the-floor-for-2-0.md) | Python 3.11 stays the minimum for Hamilton 2.0 |
| [2611-11](2611-11-no-native-code-without-a-measured-bottleneck.md) | No native code in Hamilton 2.0 until a benchmark shows a bottleneck |
| [2611-12](2611-12-2-0-prototype-is-an-end-to-end-skeleton-behind-a-switch.md) | The 2.0 prototype is an end-to-end skeleton behind an opt-in switch; the 1.x paths stay as the reference |
| [2611-13](2611-13-fix-flow-between-main-and-2-0.md) | How fixes flow between `main` and `2.0` |
| [2611-14](2611-14-src-layout-deferred-to-just-before-the-2-0-release.md) | The move to a `src/` layout waits until just before the 2.0 release |
| [2611-16](2611-16-catalog-artifact-and-diagnostic-formats.md) | The catalog artifact format and the diagnostic format of Hamilton 2.0 (Proposed) |
