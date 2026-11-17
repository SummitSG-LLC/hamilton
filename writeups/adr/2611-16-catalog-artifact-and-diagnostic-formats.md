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

# 2611-16. The catalog artifact format and the diagnostic format of Hamilton 2.0

**Status:** Proposed (2026-11). This record awaits the owner's decisions. Nothing in it is decided until the owner (Dev-iL) has decided each question below; the record then states the decisions and its status becomes Accepted.

## Context

The 2.0 outline (apache/hamilton discussion #1645) asks the compiler to "Return stable diagnostic codes, source ranges, affected nodes, missing requirements, and useful correction information", and asks for "a versioned JSON artifact usable by docs, agents, and editors" describing a compiled graph, which "need not import" the user's Python definitions to be read. Hamilton has neither today: build errors carry no code or line, the CLI, the language server and the MCP server each report them in their own shape, and the three descriptive JSON outputs that exist (`HamiltonNode.as_dict`, `Driver.export_execution`, the UI SDK's node templates) carry no schema version and lose type information.

Both formats become promises once they ship: users filter and search on a code, and other tools read the artifact. The survey [Catalog and diagnostic formats](../surveys/catalog-and-diagnostic-formats.md) compares how the dbt manifest, OpenLineage and Dagster's asset-graph snapshot carry a graph, and how SARIF, LSP, ruff and rustc carry diagnostics and keep codes stable, each at a stated version. It proposes a format for each and lists the questions below. Ticket 18 (structured diagnostics) and Ticket 19 (catalog and JSON artifact) follow this record.

## Decision

Awaiting the owner. The survey's proposal, for the owner to accept, amend or reject point by point:

- **D1. Catalog format.** Hamilton defines its own JSON format for the catalog of one compiled graph (`"format": "hamilton.catalog"`), and maps to OpenLineage or others later if wanted. Not adopted: OpenLineage `JobEvent`s with custom facets, the dbt manifest shape, Dagster-style class-tagged serialization.
- **D2. Version field and unknown versions.** `"schema_version": "MAJOR.MINOR"` beside `format` and a `producer` (Hamilton's name and version). Additive changes raise the minor version; any other change raises the major version. Proposed: a reader rejects an unknown major version with a clear error and accepts a newer minor version, ignoring members it does not know. This needs Ticket 19's reader rule amended to say "major version"; the alternative is a strict reader that rejects any version it does not know.
- **D3. Values with no JSON form.** Each position that can hold an arbitrary Python value (config values, tag values, `Annotated` metadata, parameter defaults) holds an envelope: `{"json": <value>}` when the value round-trips through JSON exactly, otherwise `{"python": {"class": "<module>.<qualname>"}}`. A reader never imports the class.
- **D4. `repr` of marked values.** `Annotated` metadata and parameter defaults may carry a `repr` cut to 200 characters; config values and tag values carry the class name only.
- **D5. Locations.** One shape for both formats: `module`, `qualname`, `file` relative to the import root (or `null` for a module built from a string), one-based `line` at the first line of the definition including decorators, optional one-based `column`, `end_line` and `end_column` in Unicode code points. Tools convert at their edge (LSP: zero-based, UTF-16).
- **D6. Code scheme.** Each diagnostic kind has an opaque code, `HAM` followed by three digits given in sequence, and a kebab-case name that states the defect. `HAM000` (`unclassified`) is the general code for a defect with no specific code.
- **D7. Code stability.** A code that shipped is never reused or given another meaning; a retired code stays documented as no longer emitted; a renamed kind lists its former names; a split code is listed as a former code of its successors; raising a code's severity is a breaking change with migration instructions.
- **D8. Diagnostic record and document.** Two severities, `error` and `warning`, which consumers must accept new values beside. Record fields: `code`, `name`, `severity`, `message`, `nodes`, `location`, `related`, `details` (keys, names and type texts only, never values), optional `help`; no fix edits in 1.0. The JSON document has the same `format`/`schema_version`/`producer` header as the catalog (`"format": "hamilton.diagnostics"`) and a `mode` stating how the sources were compiled.

The owner's decisions: not yet recorded.

## Consequences

If the proposal is accepted as written:

- Ticket 19 writes and reads `hamilton.catalog` 1.0 as specified, and its reader fails clearly on an unknown major version.
- Ticket 18 assigns `HAM` codes and names to the defect classes it handles, with `HAM000` for the rest, and generates the reference table from a registry in the code. Ticket 20's tools take code, severity, location and node names from the record and never parse a message.
- The catalog artifact holds config values that are JSON as they are; the docs must say so before a user shares one.
- Hamilton maintains two small JSON Schemas and a code registry that only grows.
- An export to SARIF or to OpenLineage remains possible from the records without changing them; neither is built in this plan.

## Alternatives considered

The survey ranks these against explicit criteria; in brief:

- **OpenLineage as the catalog format** (a `JobEvent` per node, upstream nodes in `LineageJobFacet`). Readable by lineage back ends, but types, `Annotated` metadata and config would sit in custom facets Hamilton defines anyway, and node identity would be a job name in a user-chosen namespace.
- **The dbt manifest shape.** Its resource types and required fields describe warehouse relations, not Python functions.
- **Dagster-style serialization without a version field.** Works inside one product, at the cost of keeping every old class and field name in code; it has no public schema.
- **SARIF as Hamilton's diagnostic format.** A standard that third-party tools read, but heavy for an editor or an agent; the proposed record maps onto it field by field.
- **Names only as codes**, or **codes with categories in their digits.** Names and categories can stop describing a check as it changes; an opaque code cannot.
