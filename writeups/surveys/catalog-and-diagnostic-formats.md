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

# Survey: the catalog format and the diagnostic format for Hamilton 2.0

**Status:** survey report and proposal, written 2026-11-17 for Ticket 17 of the Hamilton 2.0 effort. Nothing here is decided. The owner (Dev-iL) decides the questions in [Decisions for the owner](#decisions-for-the-owner); decision record [2611-16](../adr/2611-16-catalog-artifact-and-diagnostic-formats.md) holds the decisions once made. Tickets 18 (structured diagnostics) and 19 (catalog and JSON artifact) wait on those decisions; Ticket 20 (CLI, language server and MCP) consumes the diagnostic format through Ticket 18.

## The answer in brief

- **Catalog artifact.** Hamilton should define its own small JSON format for the catalog of one compiled graph, and map to other systems from it, rather than adopt the dbt manifest, OpenLineage or Dagster's snapshot. None of the three describes what a Hamilton graph holds: function-level nodes whose types are Python objects, a config snapshot, and source locations, read without importing user code. The proposal borrows what worked for each: dbt's split between the producer's version and the schema's version, OpenLineage's rule that additive changes are compatible and removals are not, and Dagster's typed wrappers that mark a value Python cannot hand to JSON.
- **Version field.** A top-level `"schema_version": "1.0"`, a `MAJOR.MINOR` pair. A reader rejects a major version it does not know with a clear error. Whether it also rejects a newer minor version is the first owner decision, because Ticket 19 as written says it must.
- **Values with no JSON form.** Every position that can hold an arbitrary Python value (config values, tag values, `Annotated` metadata, parameter defaults) holds an envelope: `{"json": <value>}` when the value round-trips through JSON exactly, otherwise `{"python": {"class": "<module>.<qualname>", "repr": ...}}`. The reader never imports the class. Config values never carry a `repr`.
- **Diagnostics.** One plain record per finding: `code`, `name`, `severity`, `message`, `nodes`, `location`, `related`, `details`. Codes are opaque and stable, `HAM` plus three digits (`HAM001`), each paired with a readable kebab-case name (`duplicate-node`). A code is never reused or reassigned; a retired code keeps its documentation page. `HAM000` is the general code for a defect with no specific code. Two severities, `error` and `warning`. Lines count from one and columns are optional. The language server converts to LSP's zero-based positions at its edge; a SARIF export can come later without changing the record.

The rest of this report gives the evidence and the reasoning, ranks the proposal against alternatives, states the strongest arguments against it, and lists the decisions with a recommendation each.

## Terms

Each term below has one meaning throughout this report, for Hamilton and for every system compared.

- **Compiled graph:** the immutable result of compiling modules or functions with one config (the effort's own term). It holds node definitions, edges, tags, a config snapshot and source locations, and no adapter.
- **Catalog:** the read view of one compiled graph: its resolved nodes with names, types, `Annotated` metadata, tags, documentation and source locations, its edges, and the config it was compiled for. The catalog is an in-memory API (Ticket 19). dbt also ships a file called `catalog.json`; that file holds warehouse table and column information ([dbt docs, catalog-json.md L10][dbt-docs-catalog]) and is not what this report means by catalog.
- **Artifact:** a file or string that serializes something for another process to read. The **catalog artifact** is the JSON serialization of a catalog. dbt's manifest, an OpenLineage event and a Dagster repository snapshot are each an artifact in this sense.
- **Diagnostic:** one finding reported by a compiler or analyzer about its input: what is wrong, how serious it is, and where.
- **Code:** a short identifier of the kind of a diagnostic, the same for every occurrence of that kind (`E0308`, `F401`). A **name** is a readable identifier of the same kind (`unused-import`). SARIF calls the code a rule `id` and the name a rule `name`.
- **Severity:** how serious a diagnostic is (SARIF calls it `level`, rustc calls it `level`, LSP calls it `severity`).
- **Location:** where a diagnostic or a node sits in source: a file, a line, and optionally a column and an end. A **logical location** names a program construct (a function, a node) instead of a position in a file.
- **Marked value:** a value written into JSON in a form that tells the reader it is not the original value but a description of it.
- **Version field:** the field of an artifact that names the version of the artifact's schema, as opposed to the version of the program that produced it.

## What Hamilton has today

Facts from the code at `2.0` commit [`31b3a832`][ham-commit] unless stated otherwise.

- **Three unversioned descriptive outputs.** `HamiltonNode.as_dict()` returns a node's name, tags as they are, its output type as a string, its required and optional dependencies, the source text of its first originating function, its documentation and a version hash ([`graph_types.py` L130-L154][ham-asdict]). `Driver.export_execution` returns `{"nodes": [...]}` built from it with no schema version ([`driver.py` L1019-L1038][ham-export]). The UI SDK builds a third shape for the tracking server, with `output_schema_version=1` marked `TODO`, the type as `str(node_.type)`, and tags passed through with the comment `TODO -- ensure serializable` ([`ui/sdk/.../driver.py` L528-L560][ham-sdk]).
- **The type string loses information.** `get_type_as_string` ([`htypes.py` L119-L144][ham-htypes]) turns `dict[str, list[int]]` into `'dict[str, list]'`, drops `Annotated` metadata (`Annotated[int, "positive"]` becomes `'int'`), and does not qualify class names with their module. Measured on this branch with `uv run python`.
- **Tag values are not guaranteed to be strings.** `@tag` accepts a string or a non-empty list of unique strings ([`metadata.py` L139-L154][ham-tags]). Hamilton's own loaders and savers set reserved tags to booleans, such as `"hamilton.data_loader": True`, which JSON can hold. Nothing in the node type restricts tag values, the UI SDK passes tags on with `TODO -- ensure serializable`, and Ticket 17 lists tag values among the values that may have no JSON form. `export_execution` would raise `TypeError` from `json.dumps` on a node whose tag held any other object; no such tag was found in Hamilton's own code.
- **One existing mapping to OpenLineage.** The OpenLineage adapter models the whole Hamilton graph as one OpenLineage job. It puts the JSON of every node's `as_dict()` into the job's `sourceCode` facet as one string, and adds a custom run facet `HamiltonFacet` ([`h_openlineage.py` L43-L51, L560-L576][ham-ol]). In that mapping, nodes, edges and types have no place of their own in OpenLineage's model.
- **Errors.** Graph construction stops at the first defect and raises `ValueError` or a decorator's own exception, with a message and no code or line. The CLI, the MCP tool and the language server each report failures in their own shape (Ticket 17's "What's already known").

## What the two formats must do

These requirements come from the outline (apache/hamilton discussion #1645) and from Tickets 18, 19 and 20. They are the criteria the alternatives are ranked by later.

- **R1. Describe a graph before any run.** The catalog describes a compiled graph, not a record of a run.
- **R2. Read without importing user code.** "Loading Python definitions can execute module-level code; reading an already-built catalog need not import them" (outline). A reader that unpickles or imports by qualified name breaks this (Ticket 19).
- **R3. Fit Hamilton's node model.** Node names can be parameterized; a node generated by a decorator can come from more than one function; types are Python objects, including `Annotated` metadata and unresolved forward references with their namespace (Ticket 08's boundary).
- **R4. Carry and mark values with no JSON form.** Python types, `Annotated` metadata, tag values and config values may have none. Never drop one silently (Ticket 19).
- **R5. Versioned, with a clear failure.** The artifact carries a schema version; a reader given a version it does not know fails with a clear error and does not guess (Ticket 19).
- **R6. Stable diagnostic codes.** "Return stable diagnostic codes, source ranges, affected nodes, missing requirements, and useful correction information" (outline). Users filter and search on a code; a code is a promise once it ships (Ticket 18).
- **R7. One diagnostic shape for three tools.** "The same input/configuration should produce the same graph and diagnostics across tools" (outline). The CLI reads a file, the MCP tool a string and the language server an editor document (Ticket 20).
- **R8. No data values in diagnostics.** "Use bounded summaries of expected/actual types and contract differences" and "Avoid implicitly printing whole data values or query plans" (outline). Diagnostics carry keys and types, never values (Ticket 18).
- **R9. Cheap to keep.** Hamilton is a small project. Whatever it promises, it maintains: a schema, a code registry, documentation pages.

## Part 1: graph artifacts

### The job each format does

The three systems' artifacts answer different questions, so each comparison below starts from what the artifact is for.

| System (version) | Artifact | What it describes | When it is written | Who reads it |
| --- | --- | --- | --- | --- |
| dbt Core v1.12.7 | `manifest.json`, schema v12 | Every resource of a project after parsing: models, sources, tests, macros, with configs and edges | On every command that parses the project, before or without running anything | dbt itself (state comparison, docs site) and third-party tools |
| OpenLineage spec 2-0-2 (repository tag 1.55.0) | `RunEvent`, plus the runless `JobEvent` and `DatasetEvent` | Jobs that consume and produce datasets, and the runs of those jobs | Mostly during and after a run; a `JobEvent` can describe a job with no run | Lineage back ends such as Marquez, and catalogs |
| Dagster 1.13.30 | Repository snapshot (`RepositorySnap`, `AssetNodeSnap`) serialized by Dagster's `serdes` | The asset graph and jobs a code location defines | When the webserver or an agent loads a code location | Dagster's own webserver, daemon and Dagster+ agents |

Only the dbt manifest and the Dagster snapshot describe a graph before it runs (R1). OpenLineage's core is "an event describing an observed state of a job run" ([OpenLineage.md L15-L16][ol-md-core]); its runless `JobEvent` is the exception examined below.

### dbt manifest

- **Versioning.** Every dbt artifact has a `metadata` block with `dbt_schema_version`, a URL such as `https://schemas.getdbt.com/dbt/manifest/v12.json`, and separately `dbt_version`, the version of dbt that wrote it ([`base.py` L17-L31, L54-L66][dbt-base]; [dbt docs, dbt-artifacts.md L64-L66][dbt-docs-artifacts]). The schema version is one integer. "Artifact versions may change in any minor version of dbt (`v1.x.0`). Each artifact is versioned independently" ([dbt-artifacts.md L80][dbt-docs-artifacts]). Manifest v12 has been the version since dbt 1.8: the docs' table lists it for 1.8 to 1.11 and for the dbt 2.0 line ([dbt docs, _manifest-versions.md][dbt-docs-versions]), and the 1.12.7 source still writes v12 ([`manifest.py` L111][dbt-manifest]).
- **Additive changes keep the version number, and the published schema changes in place.** The `WritableManifest` of dbt 1.12.7 has a `functions` field with a default ([`manifest.py` L173-L176][dbt-manifest]). The v12 JSON schema in the dbt 1.8.0 source tree has no `functions` property ([v1.8.0 `schemas/dbt/manifest/v12.json`][dbt-v12-180]); the same file at v1.12.7 has it ([v1.12.7 `schemas/dbt/manifest/v12.json`][dbt-v12-1127]), and so does the document served at `https://schemas.getdbt.com/dbt/manifest/v12.json` today (fetched 2026-11-17). A consumer that pinned the v12 schema in 2024 validates against a different document than one that fetches it now.
- **Reading old and unknown artifacts.** The reader accepts manifest versions 4 to 11 and upgrades them in code ([`manifest.py` L178-L203][dbt-manifest]); any other version raises `IncompatibleSchemaError` ([`base.py` L112-L141][dbt-base]). It never validates against the schema, "as it allows for safer schema upgrades": unknown optional fields are accepted ([`manifest.py` L205-L213][dbt-manifest]). Nodes of an unknown resource type are dropped with a note ([`unknown_resource_types.py` L31-L45][dbt-unknown]).
- **Node identity.** `unique_id` is `<resource_type>.<package>.<resource_name>`, the same as the dictionary key ([manifest-json.md L45][dbt-docs-manifest]; [`resources/base.py` L10-L22][dbt-resource]). Resources are maps keyed by `unique_id`.
- **Edges.** Each node lists its parents in `depends_on.nodes` ([`components.py` L49-L55][dbt-components]); the manifest also carries `parent_map` and `child_map`, each derivable from the other ([`manifest.py` L142-L151][dbt-manifest]).
- **Types.** A column's type is a string from the warehouse, `data_type: Optional[str]` ([`components.py` L112-L118][dbt-components]). dbt has no host-language types to carry.
- **Provenance.** `original_file_path` relative to the project, and a `checksum` of the file contents ([`resources/base.py` L10-L28][dbt-resource]; [manifest-json.md L49][dbt-docs-manifest]).
- **Values with no JSON form.** dbt has none to carry: configuration comes from YAML and Jinja, and `meta` is `Dict[str, Any]` that came from YAML ([`components.py` L117][dbt-components]).
- **Non-determinism.** `metadata` holds `generated_at`, `invocation_id` and selected environment variables ([`base.py` L54-L66][dbt-base]), so two parses of the same project give different bytes.

### OpenLineage

- **Versioning.** The spec is a JSON Schema whose `$id` is a resolvable versioned URL (`https://openlineage.io/spec/2-0-2/OpenLineage.json`, [OpenLineage.json L3][ol-json]). Versions follow SchemaVer, `MODEL-REVISION-ADDITION`: MODEL for "a breaking schema change which will prevent interaction with any historical data", REVISION for one "which may prevent interaction with some historical data", ADDITION for one "compatible with all historical data" ([Versioning.md L19-L31][ol-versioning]). CI is to check that the spec stays backward compatible, "only add optional fields" ([Versioning.md L33-L41][ol-versioning]). Every event carries `schemaURL` and `producer` ([OpenLineage.json L5-L28, `BaseEvent`][ol-json]); every facet carries `_schemaURL` and `_producer` ([OpenLineage.json L282-L300, `BaseFacet`][ol-json-basefacet]). Each facet has its own version (for example `SchemaDatasetFacet` 1-2-0).
- **Node identity.** A job is "identified by a unique name within a namespace"; a dataset has a "unique name within the datasource namespace derived from its physical location (db.host.database.schema.table, for example)" ([OpenLineage.md L18-L24][ol-md-core]).
- **Edges.** In a run event, a job's `inputs` and `outputs` are datasets. Since August 2026 the spec also has an explicit lineage facet ([commit `2cfa2594b7`, PR #4804][ol-lineage-commit]): a `LineageJobFacet` that "on a JobEvent is the job's declared lineage", whose entries can name source jobs as well as datasets ([`facets/LineageFacet.json`][ol-lineage]).
- **Types.** A dataset's schema facet gives each field a `type` that is a string ("VARCHAR|INT|...") ([`facets/SchemaDatasetFacet.json`][ol-schema-facet]).
- **Provenance.** `SourceCodeLocationJobFacet` (repository URL, path, version) and `SourceCodeJobFacet` (language and source text) ([`facets/SourceCodeLocationJobFacet.json`][ol-scl-facet]).
- **Extension.** "Custom facets must use a distinct prefix named after the project defining them", and their `_schemaURL` "must be an immutable pointer to the version of the facet schema" ([OpenLineage.md L97-L123][ol-md-facets]).
- **Values with no JSON form.** Not addressed; every facet is JSON. Values without a JSON form would have to be described inside a custom facet whose schema the producer defines.
- **Runless events.** `JobEvent` requires a `job` and forbids a `run` (`"not": {"required": ["run"]}`, [OpenLineage.json L80-L106][ol-json]). It is the part of OpenLineage that can describe a graph before a run.

### Dagster asset graph

- **What the format is.** Dagster's webserver and agents do not import user code: "Code location servers serve metadata about the collection of its Dagster definitions" ([oss-deployment-architecture.md L22-L24][dag-arch]), and "Dagster loads snapshots from your code server over gRPC" ([snapshot-size-limits.md L8-L19][dag-snap-docs]). The snapshot is serialized by Dagster's own `serdes` module, which explains that it exists because JSON handles named tuples badly and so that only whitelisted types cross a serialization boundary, and that it is not pickle ([`serdes.py` L1-L14][dag-serdes-head]). This is the closest of the three to the job of Hamilton's catalog artifact: a description of user-defined graph nodes, written by a process that imported the code, read by processes that must not.
- **Versioning.** There is no version field. Each serialized object is a JSON object with a `"__class__"` key. Compatibility is kept field by field: a class keeps its old wire name through `storage_name`, a renamed field keeps its old key through `storage_field_names`, and a removed field is still written through `old_fields` so that older readers keep working ([`serdes.py` L260-L327][dag-serdes-wl]). `AssetNodeSnap` is still written as `"ExternalAssetNode"`, its `parent_edges` as `"dependencies"`, and it keeps writing an empty `depended_by` for "older deployed readers" ([`external_data.py` L944-L1006][dag-assetnode]). A reader meeting a class it does not know gets an `UnknownSerdesValue`; it is discarded when it sits in a field the reader ignores, and raises `DeserializationError` that names "version skew" when the reader needs it ([`serdes.py` L475-L506, L1219-L1234][dag-serdes-unknown]).
- **Published schema.** None found. The module lives in `dagster_shared.serdes`, re-exported as the private `dagster._serdes`; the Dagster docs at 1.13.30 never mention `serdes`, and their only "JSON schema" mention is unrelated (searches listed in [How the sources were checked](#how-the-sources-were-checked)). The snapshot is a wire format between Dagster's own processes, not a public contract.
- **Node identity.** `AssetKey` is a sequence of strings, shown to users joined by `/` ([`asset_key.py` L28-L95][dag-assetkey]).
- **Edges.** Each node holds its upstream edges (`AssetParentEdgeSnap`: parent key, input name, output name, partition mapping). The downstream list was removed as "redundant with `dependencies` - downstream is derived from upstream during read" ([`external_data.py` L676-L692, L944-L966][dag-assetnode]).
- **Types.** A type is a descriptor, not the Python object: `DagsterTypeSnap` has `kind`, `key`, `name`, `display_name`, `type_param_keys` and `metadata` ([`dagster_types.py` L67-L82][dag-typesnap]). Asset nodes do not carry types; jobs do.
- **Provenance.** Optional code references with a file path and line number, held in metadata ([`source_code.py` L36-L45][dag-source]).
- **Values with no JSON form.** Metadata values are typed wrappers: text, URL, path, JSON, int, float, bool, table schema and others ([`metadata_value.py`][dag-metadata]). A raw value of any other Python type is rejected with `DagsterInvalidMetadata` and the advice to wrap it ([`metadata/__init__.py` L139-L166][dag-normalize]). Two wrappers mark values that cannot travel: `PythonArtifactMetadataValue` keeps only a module and a name ([`metadata_value.py` L709-L728][dag-metadata]), and `ObjectMetadataValue` is "an instance of an unserializable object. Only the class name will be available across process" ([`metadata_value.py` L1047-L1053][dag-metadata]).
- **Identity of a snapshot.** `create_snapshot_id` is the SHA-1 of the serialized JSON ([`utils.py` L13-L21][dag-snapid]), which only works because the serialization of an unchanged definition is the same each time.

### Comparison

| Facet | dbt manifest v12 | OpenLineage 2-0-2 | Dagster 1.13.30 snapshot |
| --- | --- | --- | --- |
| Describes a graph before a run | Yes | Only through `JobEvent`, at job and dataset level | Yes |
| Read without the producer's code | Yes (JSON) | Yes (JSON) | Yes (by design of code locations) |
| Version field | `dbt_schema_version` URL, one integer | `$id`/`schemaURL`, `MODEL-REVISION-ADDITION`, per facet | None |
| Producer version | `dbt_version`, separate | `producer` URI, separate | None in the format |
| Additive change | Same version number; published schema edited in place | ADDITION bump | No bump; defaults and `old_fields` |
| Unknown content | Unknown fields accepted; unknown resource types dropped | Facets are open (`additionalProperties`) | Unknown fields dropped; unknown types fail when needed |
| Node identity | `type.package.name` string | `namespace` + `name` | List of strings |
| Edges | Parents per node, plus both maps | Datasets in and out; declared job lineage | Parents per node only |
| Types | Warehouse type string | Field type string | Descriptor (`key`, `display_name`, params) |
| Provenance | Relative path, file checksum | Source-code facets | Code references in metadata |
| Values with no JSON form | Not needed | Not addressed | Typed wrappers; marked placeholders |
| Public schema | Yes (JSON Schema) | Yes (JSON Schema) | No |

### What carries over to Hamilton

1. Hamilton's nodes are functions and values inside one process. dbt's identity names warehouse resources (`model.package.name`) and its required fields describe relations (`database`, `schema`, `alias`, `checksum`); OpenLineage's dataset identity is "derived from its physical location". A Hamilton intermediate node has no physical location. So neither identity scheme fits R3; Hamilton's node name, unique within a compiled graph, is its identity, as `AssetKey` is Dagster's.
2. dbt and OpenLineage both keep the schema's version apart from the producer's version. Hamilton should do the same: the format can stay at 1.0 across many Hamilton releases.
3. dbt shows the cost of one integer with additive changes kept under the same number: the document at the version URL changed, so the number no longer identifies a schema. OpenLineage's ADDITION component and a minor number avoid that. Dagster shows that without any version field, compatibility costs a permanent list of old names and fields in code.
4. Dagster's choice of one direction of edges, with the other derived on read, avoids a redundant field that has to agree with the first. dbt's `parent_map`/`child_map` carries both.
5. Dagster's typed metadata wrappers and its `ObjectMetadataValue` are the precedent for R4: carry what can travel, and mark what cannot with its class name, never the object. Its rejection of unknown raw metadata shows the other choice, an error at definition time, which Hamilton cannot make for config values that users legitimately pass as objects.
6. Dagster's snapshot identity by hash of the serialized form, and dbt's `generated_at`, show the two choices for determinism. A catalog without a timestamp can be compared byte for byte, which suits "the same sources must give the same output" in Tickets 18 and 20.

## Part 2: diagnostic formats

### The job each format does

| System (version) | Format | Job |
| --- | --- | --- |
| SARIF 2.1.0 Errata 01 (OASIS Standard, 2023-08-28) | JSON log of static-analysis results | Exchange results between analysis tools and result-management systems that track them across runs |
| LSP 3.18 (current; 3.19 in progress) | `Diagnostic` in `textDocument/publishDiagnostics` | Show findings in an open editor document, live |
| ruff 0.17.5 | Rule codes and names; JSON and other output formats | A Python linter's identifiers that users select, ignore and search; machine output for CI |
| rustc 1.100.0 | Error codes, lint names; `--error-format=json` | A compiler's identifiers with long explanations; machine output for cargo and editors |

SARIF 2.2 exists only as Committee Specification Draft 01 of 9 October 2026 ([OASIS SARIF directory][sarif-dir]); its rule `id` text is unchanged from 2.1.0 ([SARIF 2.2 CSD01 §5.49.3 "`id` Property"][sarif22]). This report cites 2.1.0 Errata 01, the current OASIS Standard.

### SARIF

- **Codes.** A rule's `id` "SHALL contain a stable identifier for the rule and SHOULD be opaque" ([SARIF §3.49.3][sarif]). The note gives two reasons for stability: build scripts that disable a rule by id must not break, and result-management systems must not mark results as new because an id changed. It gives the reason for opacity: an id such as `"DoNotDoXOrY"` keeps conveying outdated guidance after the rule changes, which an opaque id such as `"CA2101"` would not. A rule may also have a `name`, "an identifier that is understandable to an end user", which a tool author may alter while the id stays ([§3.49.7][sarif]). A renamed or split rule lists its former ids in `deprecatedIds` and former names in `deprecatedNames` ([§3.49.4, §3.49.8][sarif]). A result's `ruleId` may add hierarchical components after the rule id to identify a subset of violations ([§3.27.5][sarif]).
- **Severity.** `level` is one of `error` ("a serious problem was found"), `warning` ("a problem was found"), `note` ("a minor problem or an opportunity to improve") and `none` ([§3.27.10][sarif]).
- **Locations.** Physical locations give an artifact URI and a region; `startLine` is a positive integer and `startColumn` defaults to 1 ([§3.30.5, §3.30.6][sarif]). The unit of a column is declared per run in `columnKind`, `utf16CodeUnits` or `unicodeCodePoints` ([§3.14.27][sarif]). Logical locations name a construct, with `fullyQualifiedName` and a `kind` such as `function`, `module` or `type` ([§3.33][sarif]). `relatedLocations` points at other places that matter to a result ([§3.27.22][sarif]).
- **Fixes.** A `fix` lists artifact changes, each a set of regions to replace ([§3.55][sarif]).
- **Versioning.** The log's `version` "SHALL have the value `"2.1.0"`" and should come first, to let parsers handle future versions ([§3.13.2][sarif]); `$schema` may name the JSON Schema ([§3.13.3][sarif]).
- **Extension.** Every object may carry a `properties` bag of arbitrary JSON ([§3.8][sarif]).

### LSP

- **Codes.** `code?: integer | string`, "which might appear in the user interface", with an optional `codeDescription.href`, "a URI to open with more information" ([`types/diagnostic.md` L10-L71][lsp-diag]). The protocol says nothing about how codes are named or kept stable; that is the server's concern.
- **Severity.** `Error = 1`, `Warning = 2`, `Information = 3`, `Hint = 4`; servers should always send one ([`diagnostic.md` L18-L22, L77-L96][lsp-diag]).
- **Locations.** A `Range` of `Position`s; lines and characters are zero-based ([`types/position.md` L3][lsp-pos]); character offsets count UTF-16 code units unless client and server negotiate UTF-8 or UTF-32 ([`position.md` L43-L66][lsp-pos]). A diagnostic belongs to one document; other places go in `relatedInformation`, each a location and a message ([`diagnostic.md` L57-L61][lsp-diag]).
- **Fixes.** A `CodeAction` lists the `diagnostics` it resolves, may be `isPreferred`, and carries a `WorkspaceEdit` ([`language/codeAction.md` L496-L551][lsp-codeaction]). `data` on a diagnostic is preserved into the code-action request ([`diagnostic.md` L63-L70][lsp-diag]).
- **Versioning.** By capability negotiation at initialization, not by a version field ([`specification.md` L30][lsp-spec]).

### ruff

- **Codes.** "Flake8-style rule codes: an alphabetic prefix followed by digits (e.g., `F401`). The prefix indicates the source of the rule" ([`docs/linter.md` L29-L31][ruff-linter]). Every rule also has a kebab-case name, shown in output and documentation (`unused-import`). Names follow a convention: they read correctly as "ignore ${rule}", highlight the pattern linted against, and contain no fix instructions ([`docs/rule-proposals.md` L52-L71][ruff-proposals]). Diagnostics that do not come from a rule use a name as their code: a syntax error has `"code": "invalid-syntax"` ([JSON snapshot L8][ruff-json-snap]).
- **Moving from prefixes toward categories and names.** Ruff's source says categories (correctness, suspicious, style and others) "are intended to be our primary classification mechanism for rules going forward, with the linter groups eventually being deprecated and removed" ([`codes.rs` L86-L100][ruff-codes]). In preview, rule names can be used in suppression comments in place of codes ([`linter.md` L475-L477][ruff-linter-names]).
- **Stability.** A rule has a status: stable, preview, deprecated or removed, each with the version since when ([`codes.rs` L212-L224][ruff-codes]). Selecting a removed rule is an error. Renamed codes and names keep redirects; the code redirects still in the source include ones marked "Remove by 2023-02-01" ([`rule_redirects.rs` L17-L30][ruff-redirects]). Promoting a rule to stable, changing a stable rule's behavior and deprecating a rule each need a minor (breaking) release ([`docs/versioning.md` L3, L24-L39][ruff-versioning]).
- **Severity.** The JSON output has a `severity` field ([`json.rs` L204-L227][ruff-json]), from `Hint`, `Info`, `Warning`, `Error`, `Fatal` ([`ruff_db/.../mod.rs` L1312-L1318][ruff-severity]); the lint diagnostics in ruff's own JSON snapshot tests are all `error` ([JSON snapshot][ruff-json-snap-output]), and the source anticipates "a future where we have multiple diagnostic severities" ([`codes.rs` L86-L100][ruff-codes]).
- **Locations.** One-based `row` and `column`, with `end_location` ([`json.rs` L204-L245][ruff-json]); a column counts Unicode scalar values from the start of the line ([`ruff_source_file/src/lib.rs` L223-L232][ruff-linecolumn]).
- **Fixes.** A fix is a list of edits with an applicability: `safe`, `unsafe` or `display-only` ([`ruff_diagnostics/src/fix.rs` L14-L32][ruff-fix]).
- **Versioning of the JSON.** None in the output. Shape changes are announced as breaking changes: fixes became lists of edits in 0.0.260 ([`BREAKING_CHANGES.md` L649-L660][ruff-breaking-260]), and several location fields became nullable in 0.16.0 ([`BREAKING_CHANGES.md` L141-L145][ruff-breaking]).

### rustc

- **Codes.** Errors get codes like `E0123`, each with a long explanation shown by `--explain` ([rustc-dev-guide `diagnostics/error-codes.md` L1-L6][rust-guide-codes]). New codes are allocated in sequence, the next free number after the highest ([`error-codes.md` L32-L57][rust-guide-codes]); the number carries no meaning. A code is given "if the explanation would give more information than the error itself" ([`diagnostics.md` L74-L89][rust-guide-diag]); "Not all diagnostic have a code. For example, diagnostics created by lints don't have one" ([`diagnostics.md` L28-L33][rust-guide-diag]).
- **Stability.** "Do *not* remove entries from this list. Instead, just add a note to the corresponding markdown file saying that this error is not emitted by the compiler any more" ([`rustc_error_codes/src/lib.rs` L8-L23][rust-codes-lib]). At 1.100.0 there are 518 explanation files, of which 131 say "this error code is no longer emitted by the compiler", and 135 earlier codes are kept only as comments in the same file, so that none is reused (counted in the source tree; `E0001.md` is one of the retired ones).
- **Lint names.** Lints are identified by snake_case names that read as "allow *lint-name*" ([`diagnostics.md` L165-L175][rust-guide-diag]). A renamed or removed lint is registered with `register_renamed` or `register_removed`, so that the old name warns rather than fails ([`diagnostics.md` L751-L766][rust-guide-diag]).
- **Severity.** The JSON `level` is `error`, `warning`, `note`, `help`, `failure-note` or `error: internal compiler error` ([rustc book `json.md` L47-L56][rust-json]); `note` and `help` appear mostly as children of a main diagnostic.
- **Locations.** Spans with one-based `line_start` and `column_start`, byte offsets, and `is_primary` to mark the main span among several; "Character offsets are offsets of Unicode Scalar Values" ([`json.md` L57-L100][rust-json]).
- **Fixes.** A span may carry `suggested_replacement` with `suggestion_applicability`: `MachineApplicable`, `MaybeIncorrect`, `HasPlaceholders` or `Unspecified` ([`json.md` L120-L142][rust-json]).
- **Versioning of the JSON.** None. The documentation states the compatibility rule instead: "care should be taken to be forwards-compatible with future changes to the format. Optional values may be `null`. New fields may be added. Enumerated fields like "level" or "suggestion_applicability" may add new values" ([`json.md` L14-L18][rust-json]). The `code` field holds an error code or a lint name ([`json.md` L38-L46][rust-json]).

### Comparison

| Facet | SARIF 2.1.0 | LSP 3.18 | ruff 0.17.5 | rustc 1.100.0 |
| --- | --- | --- | --- | --- |
| Code form | Opaque stable `id`, readable `name` | Any integer or string | Prefix + digits, plus kebab-case name | `E` + four digits for errors; snake_case names for lints |
| Code assignment | Tool's choice | Server's choice | Prefix per origin linter, digits within | Next free number |
| Retired code | `deprecatedIds` on the successor | Not addressed | Status `removed`; redirects | Kept in the list, page says no longer emitted; never reused |
| Renamed name | `deprecatedNames` | Not addressed | Name redirects | `register_renamed` |
| Severities | error, warning, note, none | Error, Warning, Information, Hint | Hint, Info, Warning, Error, Fatal (lint rules report as error) | error, warning, note, help, failure-note, ICE |
| Line base | 1 | 0 | 1 | 1 |
| Column unit | Declared per run | UTF-16 by default, negotiable | Unicode scalar values | Unicode scalar values |
| Logical location | Yes (`logicalLocations`) | No | No | No |
| Several places | `relatedLocations` | `relatedInformation` | No | Several spans, one primary |
| Fix | Artifact changes | Code action with edit | Edits + applicability | Replacement + applicability |
| Version in the output | `version: "2.1.0"` | Capabilities | None | None; forward-compatibility rule stated |

### What carries over to Hamilton

1. All four systems that name codes (SARIF, ruff, rustc, and LSP by allowing them) pair an identifier for machines with text for people. SARIF and ruff carry both a code and a name; rustc's errors have a code and its lints have a name. The evidence for opaque codes is SARIF's stated reason (a readable id outlives its meaning); the evidence for names is ruff's move toward them and rustc's lint names. Carrying both, as SARIF and ruff do, gets both.
2. A code that shipped stays. rustc never reuses or removes a code, and documents retired ones; ruff marks removed rules and keeps redirects for years; SARIF has `deprecatedIds`. Hamilton can adopt the rustc rule at almost no cost, because its codes will number in tens, not hundreds.
3. Prefix grouping is a burden later. Ruff's own source plans to retire its linter prefixes as the primary grouping in favor of categories. rustc's sequential numbers never needed that. Hamilton has one producer, so a prefix per origin has nothing to encode; a constant prefix (`HAM`) only says "this is Hamilton's", which matters when diagnostics from several tools end up in one SARIF log or one editor.
4. The general code. ruff gives syntax errors, which are outside its rule registry, a name-like code; rustc gives internal compiler errors a level of their own. Hamilton needs a code for "a decorator raised something with no specific code" (Ticket 18). A reserved code is simpler for tools than a special level, because a filter on codes then catches everything.
5. Severities. Every system has at least error and warning; the extra levels serve needs Hamilton does not have yet (hints for editors, notes as children). rustc's rule that enumerated fields "may add new values" lets Hamilton start with two and add more without breaking consumers that follow the rule.
6. Locations. Three of four count lines from one; LSP counts from zero and negotiates the column unit. Columns are the most varied facet. Hamilton's compiler knows the line of a function (`co_firstlineno`), not a column, so a format that requires columns would invent them.
7. Several places. All but ruff can point at more than one place, and rustc marks one span as primary. Hamilton needs this: a node from several functions, two functions producing the same node.
8. Machine output without a version field works for ruff and rustc because their consumers are close to them (cargo, editors, CI scripts), and it still broke consumers (ruff's 0.0.260 and 0.16.0 entries). Hamilton's diagnostics are read by its own three tools and by agents through MCP, so a version field costs little and tells an agent what shape it is reading.

## Proposal

The proposal has two formats that share one location shape. Field names and shapes below are the proposal; Ticket 19 and Ticket 18 choose the Python API around them. The examples are illustrative, not fixtures.

### Shared: the location

```json
{"module": "my_features.spend", "qualname": "spend_per_signup", "file": "my_features/spend.py", "line": 41}
```

- `module`: the dotted module name; always present for a node from a function.
- `qualname`: the function's `__qualname__`, so a reader can name the definition without opening the file.
- `file`: the path relative to the import root the module was loaded from (the `sys.path` entry), with `/` separators, so that the same sources give the same path on every machine. `null` when the module has no file, such as a module built from a string by the MCP tool; `line` then counts lines of that string.
- `line`: one-based. For a function it is the first line of its definition including decorators, the line Python itself records as `co_firstlineno` and that `inspect.getsourcelines` returns (checked on CPython 3.11.15 and 3.14.4: for a function with two decorators both give the first decorator's line, not the `def` line). Decorator defects are on those lines, so a user acting on the diagnostic lands at the right place.
- `column`, `end_line`, `end_column`: optional, one-based, columns in Unicode code points (SARIF's `unicodeCodePoints`, rustc's scalar values). The compiler omits them when it does not know them; the language server converts to LSP's zero-based UTF-16 positions at its edge (Ticket 20).

### The catalog artifact, schema 1.0

```json
{
  "format": "hamilton.catalog",
  "schema_version": "1.0",
  "producer": {"name": "apache-hamilton", "version": "2.0.0.dev0"},
  "config": {
    "region": {"json": "eu"},
    "model": {"python": {"class": "sklearn.linear_model._base.LinearRegression"}}
  },
  "nodes": {
    "signups": {
      "external": true,
      "type": {"text": "int", "class": "builtins.int", "args": [], "metadata": []},
      "documentation": null,
      "tags": {},
      "inputs": {},
      "sources": []
    },
    "spend_per_signup": {
      "external": false,
      "type": {"text": "float", "class": "builtins.float", "args": [], "metadata": [{"python": {"class": "annotated_types.Gt", "repr": "Gt(gt=0)"}}]},
      "documentation": "Spend divided by signups.",
      "tags": {"owner": {"json": "growth"}},
      "inputs": {
        "signups": {"type": {"text": "int", "class": "builtins.int", "args": [], "metadata": []}, "optional": false},
        "spend": {"type": {"text": "float", "class": "builtins.float", "args": [], "metadata": []}, "optional": false}
      },
      "sources": [{"module": "my_features.spend", "qualname": "spend_per_signup", "file": "my_features/spend.py", "line": 41}]
    }
  }
}
```

**Top level.** `format` names the artifact kind, so a reader can tell a catalog from a diagnostics document or a future index of config variants. `schema_version` is the version field. `producer` is the Hamilton distribution and version that wrote it, kept apart from the schema version as dbt and OpenLineage do. `config` is the config snapshot the graph was compiled for. `nodes` maps each node name to its description. There is no timestamp, invocation id or environment: the same compiled graph gives the same bytes (keys sorted, fixed separators), which Ticket 19's agreement tests and any diff of two artifacts can rely on.

**Nodes.** Keyed by the node's name, which is unique in a compiled graph; parameterized and namespaced names appear as the compiler resolved them. `external` is true for a node no function produces (an input the caller supplies). `inputs` maps each dependency's node name to the type this node expects for it and whether it is optional; this is the only place edges live, as in Dagster, and downstream edges are derived on read. Keeping the expected type on the edge is what lets Ticket 19's requirements query report "the external inputs with the types their consumers expect" when two consumers expect different types. An optional input may also carry `"default"`, a value envelope. `sources` lists every originating function, first the one Hamilton treats as primary; a node from a decorator over several functions has several. `@check_output` nodes are listed as the compiled graph holds them (Ticket 19's scope).

**Types.** A type reference is `{"text", "class", "args", "metadata"}`. `text` is a canonical, module-qualified rendering for people (`dict[str, list[int]]`, `pandas.core.series.Series`), not today's lossy `get_type_as_string`. `class` is the origin's `<module>.<qualname>`; `args` are type references of the type arguments; `metadata` lists the `Annotated` metadata as value envelopes, in order. An annotation that did not resolve is `{"text": "'Foo'", "unresolved": true, "namespace": "my_features.spend"}`, the namespace kept as Ticket 08's boundary keeps it. Two type references are equal when their JSON is equal. A reader never imports `class`; it is a name.

**Value envelopes.** Every position that can hold an arbitrary Python value holds an envelope with exactly one key:

- `{"json": <value>}` when the value survives `json.loads(json.dumps(value)) == value` with the same types: `None`, `bool`, `int`, finite `float`, `str`, and lists and string-keyed dicts of those. A tuple, a set, `NaN` or a dict with non-string keys does not qualify.
- `{"python": {"class": "<module>.<qualname>"}}` otherwise, optionally with `"repr"`: the value's `repr()`, cut to at most 200 characters, with `"repr_truncated": true` when cut.

The envelope applies to config values, tag values, `Annotated` metadata and parameter defaults, the four positions R4 names. It applies even to tag values that are plain strings, so that one rule holds everywhere and no reserved key has to be escaped in user data. Dagster's metadata wrappers are the precedent.

**What carries a `repr`.** `Annotated` metadata and parameter defaults may carry one: they are constants in source code, and a `repr` such as `Gt(gt=0)` is what makes the metadata useful to a reader. Config values never carry one: config can hold credentials, and a `repr` of a client object can include them. A config value that is JSON is carried as JSON, so the docs must say that the artifact holds config values before a user shares one (Ticket 19). Tag values carry a `repr` only if the owner wants it (decision D4).

**Reader rules.** A reader rejects an artifact whose `format` is not `hamilton.catalog`, or whose major version it does not know, with an error that names both versions. What it does with a newer minor version is decision D2. A reader never imports a module named in the artifact.

**Schema document.** The schema is written as a JSON Schema (draft 2020-12, as dbt and OpenLineage do) generated from the Python types and kept in the repository with the docs. No `$schema` URL is promised until Hamilton has a stable place to serve one.

### Diagnostics

```json
{
  "format": "hamilton.diagnostics",
  "schema_version": "1.0",
  "producer": {"name": "apache-hamilton", "version": "2.0.0.dev0"},
  "mode": "import",
  "diagnostics": [
    {
      "code": "HAM003",
      "name": "edge-type-mismatch",
      "severity": "error",
      "message": "Node `spend_per_signup` expects `signups` as int, but `signups` produces str.",
      "nodes": ["signups", "spend_per_signup"],
      "location": {"module": "my_features.spend", "qualname": "spend_per_signup", "file": "my_features/spend.py", "line": 41},
      "related": [{"location": {"module": "my_features.load", "qualname": "signups", "file": "my_features/load.py", "line": 12}, "message": "`signups` is produced here."}],
      "details": {"input": "signups", "expected": "int", "actual": "str"}
    }
  ]
}
```

The code and name in the example are illustrative; Ticket 18 assigns them.

**The record.**

- `code`: `HAM` followed by three digits. Opaque: the digits carry no category, and codes are given in sequence as defects get them, as rustc does. More than 999 codes would continue with four digits without colliding.
- `name`: kebab-case, stating the defect, not the fix (`duplicate-node`, `missing-type-hint`), following ruff's and rustc's naming conventions. Names are for people and may be renamed; the code may not.
- `severity`: `error` (the graph cannot be built) or `warning` (it builds, and something may fail later, such as an unresolved annotation). Consumers must accept a value they do not know, as rustc's JSON documentation asks of its consumers, so that a third severity can be added as a minor change.
- `message`: one sentence that stands on its own. Not stable; tools must not parse it.
- `nodes`: the names of the nodes involved, possibly empty (a config defect may involve none).
- `location`: the primary location, or `null` when there is none. For a node from several functions, the function the defect is in.
- `related`: other locations with a short message each: the other function of a duplicate node, the producer of a mismatched edge. This maps to LSP `relatedInformation`, SARIF `relatedLocations` and rustc's non-primary spans.
- `details`: a small JSON object specific to the code, holding keys, names and type texts, never values (R8). It is where "missing requirements" go, such as the missing config keys of a decorator.
- `help`: optional text that tells the user how to correct the defect. No machine-applicable edits in 1.0; a `fixes` field with ruff's three applicability levels can be added in a minor version when the compiler has a fix to offer.

**The document.** The list is wrapped in the same `format`/`schema_version`/`producer` header as the catalog, with the same reader rules, and with `mode`, which states how the sources were compiled (`import`: the module's top-level code ran). That is the statement Ticket 20 requires each tool to make. Diagnostics are ordered by file, line, code and node names, so that the same sources give the same document.

**Code rules.** These go in the decision record and the generated reference table (Ticket 18).

1. A code, once in a release, keeps its meaning and is never reused, even after the compiler stops emitting it. Its reference entry stays and says it is no longer emitted (rustc).
2. A name may change; the old name stays listed as a former name of the code (SARIF `deprecatedNames`, rustc `register_renamed`).
3. When one code is split into several, each new code lists the old one as a former code (SARIF `deprecatedIds`).
4. Raising a code's severity, from warning to error, is a breaking change and gets migration instructions; lowering it is not.
5. `HAM000` (name `unclassified`) is the general code: a defect the compiler met but has no specific code for, including an exception of any type raised by a third-party decorator. Its `details` hold the exception's class; its message carries the exception's own message, which Hamilton does not control (see Gaps). It is always an error.
6. A code exists for each defect class Ticket 18 handles; whether a rare defect deserves its own code follows rustc's rule of thumb: when a user would search for it or filter on it.

### How Hamilton's records map to the others

| Hamilton | LSP 3.18 | SARIF 2.1.0 | OpenLineage 2-0-2 |
| --- | --- | --- | --- |
| `code` | `code` | `result.ruleId`, `reportingDescriptor.id` | - |
| `name` | (in message or `codeDescription` target) | `reportingDescriptor.name` | - |
| `severity` `error` / `warning` | `1` / `2` | `level` `error` / `warning` | - |
| `location.file`, `line`, `column` | URI + zero-based `Range` (UTF-16) | `physicalLocation`, region (1-based, `unicodeCodePoints`) | - |
| `nodes` | (in message) | `logicalLocations`, `kind` `function` | - |
| `related` | `relatedInformation` | `relatedLocations` | - |
| `details`, `help` | `data` | `properties`, `message.markdown` | - |
| Catalog node | - | - | A job per node in a `JobEvent`, upstream nodes as job inputs in `LineageJobFacet`, types and config in a `hamilton_` custom facet |
| Catalog `sources` | - | - | `SourceCodeLocationJobFacet` |

The mapping to LSP is Ticket 20's work. A SARIF export and an OpenLineage export of the catalog are not proposed now; this plan leaves out new renderers and exporters. The table shows that both are possible from the proposed records without changing them.

### How the formats grow

- **Additive (minor version):** declared config with types and defaults (a `config_declarations` member), contracts on the logical node and the way `@check_output` is exposed (new node members), a node's code-version hash, diagnostics kept with the catalog (a `diagnostics` member holding warnings), `fixes` on a diagnostic, a third severity.
- **Separate artifact (new `format` value):** an index of config variants or of available providers, which the outline keeps distinct from a compiled graph.
- **Breaking (major version):** a change to the envelope rule, to node identity, or to the location shape.

None of these is needed by the proposal, and none is in scope for this plan.

## Alternatives, ranked

### Catalog

Criteria, from the requirements above: C1 describes a graph before a run, at function level (R1, R3); C2 read without importing user code (R2); C3 carries Python types and marks non-JSON values (R3, R4); C4 versioned with a clear failure (R5); C5 cost to Hamilton to keep (R9); C6 read by existing third-party tools without a mapping.

| Option | C1 | C2 | C3 | C4 | C5 | C6 | Rank |
| --- | --- | --- | --- | --- | --- | --- | --- |
| A. Own format, as proposed, mapped to others later | Yes | Yes | Yes | Yes | One small schema | No; needs a mapping | 1 |
| B. OpenLineage `JobEvent` per node with `LineageJobFacet`, custom facets for types and config | Partly: lineage between jobs, not typed edges | Yes | Only inside a custom facet Hamilton defines | Yes, per facet | Spec conformance, plus the custom facets (which are option A inside an envelope) | Yes for lineage back ends that accept `JobEvent` | 2 |
| C. dbt manifest shape | No: resource types and required relational fields are dbt's | Yes | No | Yes, but one integer | A schema owned by another project | Only by dbt-aware tools, which would misread Hamilton nodes | 4 |
| D. Dagster-style serdes (class-tagged objects, no version) | Yes | Yes | Yes | No version field; compatibility kept in code | Old names kept forever | No | 3 |
| E. Pickle or import-by-name artifact | Yes | No | Yes | No | Low | No | Rejected by R2 |

Option B is the strongest alternative and is stated at full strength under counter-arguments below. It ranks second because the parts Hamilton needs most (typed edges, `Annotated` metadata, config) would live in custom facets that Hamilton defines and versions anyway, so it costs option A plus OpenLineage conformance, and because its node identity is a job name in a namespace that the user would have to choose.

### Diagnostic format and code scheme

Criteria: D1 stable codes users can filter on (R6); D2 one shape for three tools, convertible to LSP (R7); D3 no data values (R8); D4 cost to keep; D5 read by third-party tools.

| Option | D1 | D2 | D3 | D4 | D5 | Rank |
| --- | --- | --- | --- | --- | --- | --- |
| a. Own record, opaque `HAM` code + name, as proposed | Yes | Yes | By rule | Registry + generated table | Through a later SARIF export | 1 |
| b. SARIF as Hamilton's own diagnostic JSON | Yes | Heavy for an editor and an agent: `runs`, `tool.driver.rules`, results referring to rules by index | By rule | The SARIF object model in every tool | Yes (GitHub code scanning and other SARIF consumers) | 2 |
| c. Own record, names only (`duplicate-node`) as codes | Weaker: names convey meaning that can go stale (SARIF §3.49.3), and renames need redirects | Yes | By rule | Redirect table | Same as a | 3 |
| d. Own record, prefixed codes with a category in the digits (`HAM1xx` structure, `HAM2xx` types) | Yes, until a defect changes category | Yes | By rule | Category ranges to police | Same as a | 4 |
| e. LSP `Diagnostic` as the format | No naming rule | Zero-based UTF-16 positions do not suit the CLI or an agent | By rule | Low | Editors only | 5 |

## Strongest counter-arguments, engaged

**"Adopt OpenLineage for the catalog; Hamilton already speaks it."** Since August 2026 OpenLineage can describe declared lineage without a run: a `JobEvent` per Hamilton node, each with a `LineageJobFacet` naming its upstream nodes as source jobs, would put a Hamilton graph into Marquez and other back ends with no Hamilton-specific reader. That is a real benefit no own format has. It does not carry the parts of the catalog that Ticket 19 and the outline ask for: a field type in OpenLineage is one string, there is no place for `Annotated` metadata, a config snapshot or parameterized-name structure, and a job's identity is a name in a namespace that the user or the integration chooses. Each would go into a `hamilton_*` custom facet with a schema Hamilton defines, versions and publishes at an immutable URL, which is option A inside an envelope, plus OpenLineage conformance. The explicit lineage facet is three months old; how many consumers accept `JobEvent`s is not established here (one vendor page, the AWS SageMaker Unified Studio user guide, says "Currently, Amazon SageMaker Unified Studio only supports RunEvents" ([AWS docs, undated, read 2026-11-17][aws-ol]); that is a third-party claim about one consumer and is flagged as such). Hamilton's existing adapter shows the cost of the mismatch: it puts the whole node list into the `sourceCode` facet as one string. The proposal keeps the benefit reachable: an OpenLineage export from the catalog is a mapping (table above), and it can be added when someone needs it.

**"Adopt SARIF for diagnostics; GitHub code scanning reads it."** SARIF is a standard with stable identifiers, logical locations and fixes, and the proposed record copies its key rules. As the format the three tools exchange, it is heavy: a result refers to its rule through `tool.driver.rules` by index, a single finding needs `runs`/`tool`/`results` around it, and an agent reading MCP output, or an editor, gains nothing from that structure. The proposed record maps onto SARIF field by field, so an export is cheap when wanted.

**"Opaque codes are user-hostile; use names."** Ruff is moving toward names, and mypy-style names are familiar to Python users. The proposal gives every code a name and shows both. What it does not do is make the name the promise, because SARIF's stated reason holds for a compiler whose checks will change during 2.0: a name such as `missing-type-hint` may stop describing its defect if the check widens, while `HAM002` can keep its meaning by definition.

**"A version field on diagnostics is ceremony; ruff and rustc have none."** True, and both still broke consumers (ruff's entries in `BREAKING_CHANGES.md`); rustc compensates with a written forward-compatibility rule. Hamilton's diagnostics will be read by agents through MCP, which cannot read a changelog before parsing. The header costs three fields.

**"Envelopes everywhere are verbose; mark only the values that need it."** A reserved marker key inside otherwise raw JSON is shorter, but then a user config dict that happens to contain the marker key needs an escape rule, and a reader must check every object for it. With one envelope per value position, no user data is ever interpreted as a marker. Config and tags are small next to the node list; Ticket 19 measures the artifact's size at 1,000 nodes.

**"Hamilton should not promise a format before 2.0 is stable."** The outline asks for "a versioned JSON artifact usable by docs, agents, and editors" and "stable diagnostic codes". A version field is what lets the format change during 2.0 without breaking a reader silently. Codes can be promised early because the rule is cheap: never reuse.

## Three frames

- **Pipeline author.** Sees all defects in one build, each with a code to search and a file and line to open, in the CLI, the editor and the agent alike. Can share a catalog artifact with a teammate or an agent who does not have the pipeline's dependencies installed (the outline: "Catalog inspection should not require installing every provider"). Must know that the artifact holds config values; the proposal never adds a `repr` of a config value, but JSON config values are carried as they are.
- **Maintainer.** Keeps one schema per format, generated from the Python types, and one code registry that generates the reference table. Pays for the no-reuse rule with a list that only grows (rustc's has reached `E0806`; Hamilton's will hold tens). Pays for value envelopes once, in the writer. Decides each schema change against a written rule (additive is minor, anything else is major).
- **Operator** (CI, deployment, a platform team). Can fail a CI job on `severity == "error"`, allow-list a code, and diff two catalog artifacts byte for byte because there is no timestamp. Can pin a reader to a major version. Gets a clear error, not a partial read, when an artifact is newer than the reader (D2).

## Confidence, gaps and assumptions

- **Strong evidence:** every claim about the seven systems is read from their source or their own documentation at the stated version. The SARIF and rustc rules on stable codes are explicit text, not inference. dbt's in-place change of the v12 schema is shown by two files at two tags.
- **Moderate:** that Dagster publishes no schema for its snapshot rests on searches that found none, not on a statement by Dagster. That Hamilton's compiler has no columns rests on what Python's code objects give; a later compiler using `ast` could have them, which the optional fields allow.
- **Weak, flagged:** adoption of OpenLineage `JobEvent`s by back ends was not established; the one source found is a third-party vendor page.
- **Not surveyed:** mypy, pyright and pylint codes, which Python users also know (mypy uses names such as `arg-type`); the Hamilton UI's needs from a catalog; JSON Schema tooling choices. None of them would change the recommendations above, but they were not checked.
- **Assumptions:** the import root of a module is available when the compiler records a location (true for file-based modules; the string-built modules of the MCP tool and the language server have none, and their `file` is `null`). Hamilton node names are unique within one compiled graph (true of 1.x's `FunctionGraph`).
- **Gap in the "no values" rule:** the general code `HAM000` carries the message of an exception raised by third-party code, which may include values. The alternative, dropping the message, would leave the user with a code and no explanation. The owner may prefer to drop or truncate it (part of D6).

## Decisions for the owner

Each decision lists the options and a recommendation. Decisions D1 to D4 bind Ticket 19; D5 to D8 bind Ticket 18 (and through it Ticket 20).

- **D1. Catalog format: Hamilton's own JSON format, or an existing one?** Options: own format (A), OpenLineage `JobEvent`s with custom facets (B), dbt manifest shape (C), Dagster-style serdes (D). **Recommendation: A**, with the structure in [The catalog artifact, schema 1.0](#the-catalog-artifact-schema-10), and OpenLineage and SARIF left as later mappings.
- **D2. Version field and what a reader does with a version it does not know.** The field is `"schema_version": "MAJOR.MINOR"` with `format` and `producer` beside it. Options: (a) strict, as Ticket 19 is written: a reader rejects any version it does not know, including a newer minor; (b) a reader rejects an unknown major version and accepts a newer minor version, ignoring members it does not know, as dbt's reader and rustc's forward-compatibility rule do; (c) one integer, bumped on every change (dbt's scheme without its in-place edits), strict. **Recommendation: (b)**, with an amendment to Ticket 19's reader rule to say "major version". (a) makes every additive change break every older reader, which removes the reason to distinguish additive changes. If the owner prefers (a), the minor number still records what changed, and readers are simply upgraded with Hamilton.
- **D3. How a value with no JSON form is carried.** Options: (a) an envelope at every value position, `{"json": ...}` or `{"python": {"class": ...}}`; (b) raw JSON with a reserved marker object for non-JSON values; (c) stringify (today's behavior where it does not crash), which Ticket 19 forbids as a silent drop. **Recommendation: (a)**, with exact round-trip as the test for `json`.
- **D4. Which marked values may carry a `repr`.** Options for each of config values, tag values, `Annotated` metadata and parameter defaults: class name only, or class name plus a `repr` cut to 200 characters. **Recommendation:** `Annotated` metadata and defaults may carry a `repr`; config values never; tag values class name only (user tags are strings already, and a non-string tag value is Hamilton-internal).
- **D5. Locations.** One shape for both formats: `module`, `qualname`, `file` relative to the import root (or `null`), one-based `line` at the first line of the definition including decorators, optional one-based columns in Unicode code points. **Recommendation:** as stated. The alternative for `line` is the `def` line, which needs source parsing and points past the decorators where many defects are.
- **D6. Code scheme.** Options: (a) opaque `HAM` + three digits in sequence, plus a kebab-case name; (b) names only; (c) `HAM` codes with categories in the digit ranges. Also: the general code. **Recommendation: (a)**, with `HAM000` named `unclassified` as the general code, carrying the exception class in `details` and the exception's message as is.
- **D7. Code stability rules.** **Recommendation:** the six rules in [Diagnostics](#diagnostics): never reuse; retired codes stay documented; names may change with the former name listed; split codes list former codes; raising a severity is a breaking change; a code per defect class Ticket 18 handles.
- **D8. Severities, the record, and the diagnostics document.** **Recommendation:** two severities, `error` and `warning`, with consumers required to accept unknown values; the record fields `code`, `name`, `severity`, `message`, `nodes`, `location`, `related`, `details`, optional `help`, and no fix edits in 1.0; the JSON document wrapped in the same `format`/`schema_version`/`producer` header as the catalog, plus `mode`, with the reader rule of D2.

## How the sources were checked

- **Versions.** Each system was read at the newest release on 2026-11-17, found with `gh api repos/<owner>/<repo>/releases/latest`: dbt Core v1.12.7, OpenLineage 1.55.0 (spec 2-0-2), Dagster 1.13.30, ruff 0.17.5, Rust 1.100.0. Sources were sparse clones at those tags. The dbt documentation was read at commit `80c162b7` of `dbt-labs/docs.getdbt.com` and the LSP specification at commit `6714b477` of `microsoft/language-server-protocol` (2026-11-16), whose 3.18 page calls itself "the current 3.18.x version". SARIF was read from the OASIS HTML of 2.1.0 Errata 01, and the OASIS directory listing was fetched to confirm that 2.2 is a draft.
- **Primary sources only for key claims.** Every claim the proposal turns on (stable opaque ids, never-reused codes, separate schema and producer versions, in-place change of dbt's v12 schema, Dagster's compatibility by old names, OpenLineage's additive rule and runless `JobEvent`) cites the system's own source or specification. One web search was made (OpenLineage static lineage); its results were blogs and vendor pages, used only for the flagged SageMaker claim, and the claims about `JobEvent` were then checked in `OpenLineage.json` itself.
- **Several formulations per facet.** Versioning: `schema_version`, `dbt_schema_version`, `$id`, `schemaURL`, `version`, `storage_name`, `old_fields`, `BREAKING_CHANGES`. Identity: `unique_id`, `namespace`, `AssetKey`, `fqn`. Edges: `depends_on`, `parent_map`, `parent_edges`, `inputs`, `LineageJobFacet`. Types: `data_type`, `SchemaDatasetFacetFields`, `DagsterTypeSnap`. Non-JSON values: `Any`, `meta`, `MetadataValue`, `ObjectMetadataValue`, `normalize_metadata_value`, `UnknownSerdesValue`, `properties`, `LSPAny`. Codes: `id`, `deprecatedIds`, `name`, `RULE_NAME_REDIRECTS`, `RuleStatus`, `register_renamed`, `no longer emitted`, `error_codes!`. Severity: `level`, `DiagnosticSeverity`, `Severity`. Locations: `startLine`, `columnKind`, `Position`, `PositionEncodingKind`, `line_start`, `is_primary`, `JsonLocation`. Fixes: `fix`, `CodeAction`, `Applicability`, `suggestion_applicability`.
- **Dagster's missing public schema.** Searched the Dagster docs tree at 1.13.30 for `serdes` (no hits), `json schema`/`jsonschema` (one unrelated hit), `--json` and `list defs` (no machine-readable definition dump documented), and the Dagster+ snapshot page, which describes the snapshot without a schema.
- **dbt's v12 schema change.** Compared the property lists of `schemas/dbt/manifest/v12.json` at v1.8.0 and v1.12.7, and of the document served at `schemas.getdbt.com` on 2026-11-17.
- **Counts.** rustc's codes counted with `ls compiler/rustc_error_codes/src/error_codes | wc -l` (518), `grep -rl "no longer emitted"` (131) and the commented entries in `lib.rs` (135).
- **Hamilton facts.** Read at `2.0` commit `31b3a832`; the type-string losses were run with `uv run python` on this branch; the decorator-line behavior was run on CPython 3.11.15 and 3.14.4.
- **Not done.** No tool was run to produce its output; output shapes come from documentation, source and the tools' own snapshot tests.

<!-- Hamilton -->
[ham-commit]: https://github.com/SummitSG-LLC/hamilton/tree/31b3a832ab853d93b1b39333753c001ca55f7d6f
[ham-asdict]: https://github.com/SummitSG-LLC/hamilton/blob/31b3a832ab853d93b1b39333753c001ca55f7d6f/hamilton/graph_types.py#L130-L154
[ham-export]: https://github.com/SummitSG-LLC/hamilton/blob/31b3a832ab853d93b1b39333753c001ca55f7d6f/hamilton/driver.py#L1019-L1038
[ham-sdk]: https://github.com/SummitSG-LLC/hamilton/blob/31b3a832ab853d93b1b39333753c001ca55f7d6f/ui/sdk/src/hamilton_sdk/driver.py#L528-L560
[ham-htypes]: https://github.com/SummitSG-LLC/hamilton/blob/31b3a832ab853d93b1b39333753c001ca55f7d6f/hamilton/htypes.py#L119-L144
[ham-tags]: https://github.com/SummitSG-LLC/hamilton/blob/31b3a832ab853d93b1b39333753c001ca55f7d6f/hamilton/function_modifiers/metadata.py#L139-L154
[ham-ol]: https://github.com/SummitSG-LLC/hamilton/blob/31b3a832ab853d93b1b39333753c001ca55f7d6f/hamilton/plugins/h_openlineage.py#L560-L576

<!-- dbt -->
[dbt-base]: https://github.com/dbt-labs/dbt-core/blob/v1.12.7/core/dbt/artifacts/schemas/base.py#L17-L141
[dbt-manifest]: https://github.com/dbt-labs/dbt-core/blob/v1.12.7/core/dbt/artifacts/schemas/manifest/v12/manifest.py#L110-L213
[dbt-unknown]: https://github.com/dbt-labs/dbt-core/blob/v1.12.7/core/dbt/artifacts/schemas/upgrades/unknown_resource_types.py#L31-L45
[dbt-resource]: https://github.com/dbt-labs/dbt-core/blob/v1.12.7/core/dbt/artifacts/resources/base.py#L10-L28
[dbt-components]: https://github.com/dbt-labs/dbt-core/blob/v1.12.7/core/dbt/artifacts/resources/v1/components.py#L49-L118
[dbt-v12-180]: https://github.com/dbt-labs/dbt-core/blob/v1.8.0/schemas/dbt/manifest/v12.json
[dbt-v12-1127]: https://github.com/dbt-labs/dbt-core/blob/v1.12.7/schemas/dbt/manifest/v12.json
[dbt-docs-artifacts]: https://github.com/dbt-labs/docs.getdbt.com/blob/80c162b7878a1d5be738b4cbdec9de58838fb9c7/website/docs/reference/artifacts/dbt-artifacts.md?plain=1#L60-L80
[dbt-docs-manifest]: https://github.com/dbt-labs/docs.getdbt.com/blob/80c162b7878a1d5be738b4cbdec9de58838fb9c7/website/docs/reference/artifacts/manifest-json.md?plain=1#L40-L56
[dbt-docs-catalog]: https://github.com/dbt-labs/docs.getdbt.com/blob/80c162b7878a1d5be738b4cbdec9de58838fb9c7/website/docs/reference/artifacts/catalog-json.md?plain=1#L10
[dbt-docs-versions]: https://github.com/dbt-labs/docs.getdbt.com/blob/80c162b7878a1d5be738b4cbdec9de58838fb9c7/website/snippets/_manifest-versions.md?plain=1

<!-- OpenLineage -->
[ol-json]: https://github.com/OpenLineage/OpenLineage/blob/1.55.0/spec/OpenLineage.json#L1-L110
[ol-json-basefacet]: https://github.com/OpenLineage/OpenLineage/blob/1.55.0/spec/OpenLineage.json#L282-L300
[aws-ol]: https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/datazone-data-lineage-what-is-openlineage.html
[ol-versioning]: https://github.com/OpenLineage/OpenLineage/blob/1.55.0/spec/Versioning.md?plain=1#L19-L41
[ol-md-core]: https://github.com/OpenLineage/OpenLineage/blob/1.55.0/spec/OpenLineage.md?plain=1#L13-L34
[ol-md-facets]: https://github.com/OpenLineage/OpenLineage/blob/1.55.0/spec/OpenLineage.md?plain=1#L89-L123
[ol-lineage]: https://github.com/OpenLineage/OpenLineage/blob/1.55.0/spec/facets/LineageFacet.json
[ol-lineage-commit]: https://github.com/OpenLineage/OpenLineage/commit/2cfa2594b7
[ol-schema-facet]: https://github.com/OpenLineage/OpenLineage/blob/1.55.0/spec/facets/SchemaDatasetFacet.json
[ol-scl-facet]: https://github.com/OpenLineage/OpenLineage/blob/1.55.0/spec/facets/SourceCodeLocationJobFacet.json

<!-- Dagster -->
[dag-arch]: https://github.com/dagster-io/dagster/blob/1.13.30/docs/docs/deployment/oss/oss-deployment-architecture.md?plain=1#L22-L24
[dag-snap-docs]: https://github.com/dagster-io/dagster/blob/1.13.30/docs/docs/deployment/dagster-plus/management/snapshot-size-limits.md?plain=1#L8-L19
[dag-serdes-head]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/libraries/dagster-shared/dagster_shared/serdes/serdes.py#L1-L14
[dag-serdes-wl]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/libraries/dagster-shared/dagster_shared/serdes/serdes.py#L260-L327
[dag-serdes-unknown]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/libraries/dagster-shared/dagster_shared/serdes/serdes.py#L475-L506
[dag-assetnode]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/remote_representation/external_data.py#L676-L1006
[dag-assetkey]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/definitions/asset_key.py#L28-L95
[dag-typesnap]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/snap/dagster_types.py#L67-L82
[dag-source]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/definitions/metadata/source_code.py#L36-L45
[dag-metadata]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/definitions/metadata/metadata_value.py#L709-L1053
[dag-normalize]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/dagster/dagster/_core/definitions/metadata/__init__.py#L139-L166
[dag-snapid]: https://github.com/dagster-io/dagster/blob/1.13.30/python_modules/libraries/dagster-shared/dagster_shared/serdes/utils.py#L13-L21

<!-- SARIF -->
[sarif]: https://docs.oasis-open.org/sarif/sarif/v2.1.0/errata01/os/sarif-v2.1.0-errata01-os-complete.html
[sarif-dir]: https://docs.oasis-open.org/sarif/sarif/
[sarif22]: https://docs.oasis-open.org/sarif/sarif/v2.2/csd01/sarif-v2.2-csd01.md

<!-- LSP -->
[lsp-spec]: https://github.com/microsoft/language-server-protocol/blob/6714b477746a6d4b29fb5510152a3b82206a2e16/_specifications/lsp/3.18/specification.md?plain=1#L20-L30
[lsp-diag]: https://github.com/microsoft/language-server-protocol/blob/6714b477746a6d4b29fb5510152a3b82206a2e16/_specifications/lsp/3.18/types/diagnostic.md?plain=1#L10-L96
[lsp-pos]: https://github.com/microsoft/language-server-protocol/blob/6714b477746a6d4b29fb5510152a3b82206a2e16/_specifications/lsp/3.18/types/position.md?plain=1#L1-L66
[lsp-codeaction]: https://github.com/microsoft/language-server-protocol/blob/6714b477746a6d4b29fb5510152a3b82206a2e16/_specifications/lsp/3.18/language/codeAction.md?plain=1#L496-L551

<!-- ruff -->
[ruff-linter]: https://github.com/astral-sh/ruff/blob/0.17.5/docs/linter.md?plain=1#L29-L31
[ruff-linter-names]: https://github.com/astral-sh/ruff/blob/0.17.5/docs/linter.md?plain=1#L475-L477
[ruff-proposals]: https://github.com/astral-sh/ruff/blob/0.17.5/docs/rule-proposals.md?plain=1#L52-L71
[ruff-versioning]: https://github.com/astral-sh/ruff/blob/0.17.5/docs/versioning.md?plain=1#L1-L39
[ruff-codes]: https://github.com/astral-sh/ruff/blob/0.17.5/crates/ruff_linter/src/codes.rs#L86-L224
[ruff-redirects]: https://github.com/astral-sh/ruff/blob/0.17.5/crates/ruff_linter/src/rule_redirects.rs#L17-L30
[ruff-json]: https://github.com/astral-sh/ruff/blob/0.17.5/crates/ruff_db/src/diagnostic/render/json.rs#L204-L245
[ruff-json-snap]: https://github.com/astral-sh/ruff/blob/0.17.5/crates/ruff_db/src/diagnostic/render/snapshots/ruff_db__diagnostic__render__json__tests__syntax_errors.snap#L8
[ruff-json-snap-output]: https://github.com/astral-sh/ruff/blob/0.17.5/crates/ruff_db/src/diagnostic/render/snapshots/ruff_db__diagnostic__render__json__tests__output.snap
[ruff-severity]: https://github.com/astral-sh/ruff/blob/0.17.5/crates/ruff_db/src/diagnostic/mod.rs#L1312-L1318
[ruff-linecolumn]: https://github.com/astral-sh/ruff/blob/0.17.5/crates/ruff_source_file/src/lib.rs#L223-L232
[ruff-fix]: https://github.com/astral-sh/ruff/blob/0.17.5/crates/ruff_diagnostics/src/fix.rs#L14-L32
[ruff-breaking]: https://github.com/astral-sh/ruff/blob/0.17.5/BREAKING_CHANGES.md?plain=1#L141-L145
[ruff-breaking-260]: https://github.com/astral-sh/ruff/blob/0.17.5/BREAKING_CHANGES.md?plain=1#L649-L660

<!-- rustc -->
[rust-codes-lib]: https://github.com/rust-lang/rust/blob/1.100.0/compiler/rustc_error_codes/src/lib.rs#L8-L23
[rust-guide-codes]: https://github.com/rust-lang/rust/blob/1.100.0/src/doc/rustc-dev-guide/src/diagnostics/error-codes.md?plain=1#L1-L57
[rust-guide-diag]: https://github.com/rust-lang/rust/blob/1.100.0/src/doc/rustc-dev-guide/src/diagnostics.md?plain=1#L28-L89
[rust-json]: https://github.com/rust-lang/rust/blob/1.100.0/src/doc/rustc/src/json.md?plain=1#L14-L142
