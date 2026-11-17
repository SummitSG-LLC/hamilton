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

"""The promises the 1.x line made for 2.0, and what 2.0 did with each.

The scan finds every promise in the source under ``hamilton/``: each use of ``@deprecated`` whose
``fail_starting`` the current version has reached, and each comment or string that promises a change in
2.0 or in the next major release. ``LEDGER`` records every promise found at the branch point with its
treatment. tests/test_2_0_promises.py fails when the scan finds a promise the ledger lacks, so a promise
that arrives when ``2.0`` takes ``main`` is caught, and when the ledger expects one the scan no longer finds.

Print the enumeration, for this checkout or for another hamilton package directory::

    uv run python -m tests.promises_for_2_0 [PATH_TO_A_HAMILTON_PACKAGE]
"""

import ast
import dataclasses
import io
import pathlib
import re
import sys
import tokenize

import hamilton
from hamilton.dev_utils import deprecation

# A promise in prose names Hamilton 2.0 or the next major release. Version numbers of other libraries
# ("polars 2.0.0", "pandas 2.0") do not match.
_PROSE_PROMISE = re.compile(
    r"hamilton(?: version:?)?\s+v?2\.0"
    r"|\bin (?:a |the )?2\.0(?:\.0)?\b"
    r"|\b2\.0(?:\.0)? release"
    r"|\bfrom 2\.0(?:\.0)?\b"
    r"|\bTODO\(2\.0\)"
    r"|\b(?:next|future) major\b",
    re.IGNORECASE,
)
# A line saying a removal happened ("Removed in 2.0", "was removed in Hamilton 2.0") is no promise.
_TOOK_EFFECT = re.compile(r"(?<!be )removed in (?:hamilton )?2\.0", re.IGNORECASE)
_DEPRECATED = "hamilton.dev_utils.deprecation.deprecated"
# A deprecation is a promise for 2.0 when it fails by 2.0.0, or by the current version once that is later.
_DUE_BY = max(deprecation.CURRENT_VERSION, deprecation.Version(2, 0, 0))
# Python 3.12 tokenizes the literal parts of an f-string apart from the f-string; 3.11 does not.
_TEXT_TOKENS = {tokenize.COMMENT, tokenize.STRING} | (
    {tokenize.FSTRING_MIDDLE} if hasattr(tokenize, "FSTRING_MIDDLE") else set()
)


@dataclasses.dataclass(frozen=True)
class Promise:
    """One promise found in the source: where it is, and what makes it."""

    path: str  # relative to the directory holding the hamilton package
    text: str  # the source line, stripped, or the name a deprecation decorates

    def __str__(self) -> str:
        return f"{self.path}: {self.text}"


def deprecated_calls(tree: ast.Module, module: str, is_package: bool = False) -> list[ast.Call]:
    """Every call of ``hamilton.dev_utils.deprecation.deprecated`` in a module, whatever name or
    import form (absolute, relative, aliased, or reached through a parent module) it is called by."""
    package = module if is_package else module.rpartition(".")[0]
    bound = {}  # name in this module -> the dotted name it refers to
    for statement in ast.walk(tree):
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                if alias.asname:
                    bound[alias.asname] = alias.name
                else:
                    root = alias.name.split(".")[0]
                    bound[root] = root
        elif isinstance(statement, ast.ImportFrom):
            source = statement.module or ""
            if statement.level:
                base = package
                for _ in range(statement.level - 1):
                    base = base.rpartition(".")[0]
                source = f"{base}.{source}" if source else base
            for alias in statement.names:
                bound[alias.asname or alias.name] = f"{source}.{alias.name}"

    def dotted_name(expr: ast.expr) -> str | None:
        if isinstance(expr, ast.Name):
            return bound.get(expr.id)
        if isinstance(expr, ast.Attribute):
            owner = dotted_name(expr.value)
            return f"{owner}.{expr.attr}" if owner else None
        return None

    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and dotted_name(node.func) == _DEPRECATED
    ]


def _fail_starting(call: ast.Call) -> tuple[int, ...] | None:
    """The ``fail_starting`` a deprecation passes, or None when it is not a literal."""
    argument = next(
        (keyword.value for keyword in call.keywords if keyword.arg == "fail_starting"),
        call.args[1] if len(call.args) > 1 else None,
    )
    try:
        return tuple(ast.literal_eval(argument)) if argument is not None else None
    except ValueError:
        return None


def _decorated_names(tree: ast.Module) -> dict[ast.expr, str]:
    """Each decorator expression in a module, mapped to the qualified name of what it decorates."""
    names = {}

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for decorator in child.decorator_list:
                    names[decorator] = f"{prefix}{child.name}"
                visit(child, f"{prefix}{child.name}.")
            else:
                visit(child, prefix)

    visit(tree, "")
    return names


def _due_deprecations(path: pathlib.Path, relative: str, source: str) -> list[Promise]:
    """Each ``@deprecated`` in a module that fails at the current version, or whose version is not
    a literal, named by what it decorates."""
    tree = ast.parse(source, filename=str(path))
    module_path = pathlib.PurePosixPath(relative).with_suffix("")
    is_package = module_path.name == "__init__"
    module = ".".join(module_path.parent.parts if is_package else module_path.parts)
    decorated = _decorated_names(tree)
    lines = source.splitlines()
    found = []
    for call in deprecated_calls(tree, module, is_package):
        fail_starting = _fail_starting(call)
        if fail_starting is None or deprecation.Version(*fail_starting[:3]) <= _DUE_BY:
            name = decorated.get(call)
            text = f"@deprecated {name}" if name else lines[call.lineno - 1].strip()
            found.append(Promise(relative, text))
    return found


def prose_promises(relative: str, source: str) -> list[Promise]:
    """Each comment or string in a module that promises a change in 2.0 or the next major release."""
    lines = source.splitlines()
    found = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type not in _TEXT_TOKENS:
            continue
        for offset, line in enumerate(token.string.splitlines()):
            if _PROSE_PROMISE.search(line) and not _TOOK_EFFECT.search(line):
                found.append(Promise(relative, lines[token.start[0] - 1 + offset].strip()))
    return found


def scan(package: pathlib.Path) -> list[Promise]:
    """Every promise for 2.0 in the source of a hamilton package, in file and line order."""
    found = []
    for path in sorted(package.rglob("*.py")):
        relative = path.relative_to(package.parent).as_posix()
        source = path.read_text()
        found += _due_deprecations(path, relative, source)
        found += prose_promises(relative, source)
    return list(dict.fromkeys(found))  # a line can hold more than one match


@dataclasses.dataclass(frozen=True)
class Entry:
    """A promise found at the branch point, and what 2.0 did with it."""

    promise: Promise
    treatment: str
    # Whether the promise is still in the source. A promise that took effect usually leaves none behind.
    in_source: bool


def _entry(path: str, text: str, treatment: str, in_source: bool = False) -> Entry:
    return Entry(Promise(path, text), treatment, in_source)


_RAISES = "Took effect: raises, naming the replacement and its migration section ({section})."
_NOT_A_PROMISE = "Not a promise of a 2.0 change: {reason} Kept as it is."

LEDGER: list[Entry] = [
    # Uses of @deprecated(fail_starting=(2, 0, 0)) at the branch point.
    _entry(
        "hamilton/driver.py",
        "@deprecated Driver.raw_execute",
        _RAISES.format(section="Driver.raw_execute")
        + " AsyncDriver.raw_execute, never deprecated, stays; hamilton_sdk's Driver no longer "
        "overrides it.",
    ),
    _entry(
        "hamilton/function_modifiers/expanders.py",
        "@deprecated parametrized",
        _RAISES.format(section="parametrized, parametrized_input and parameterized_inputs"),
    ),
    _entry(
        "hamilton/function_modifiers/expanders.py",
        "@deprecated parametrized_input",
        _RAISES.format(section="parametrized, parametrized_input and parameterized_inputs"),
    ),
    _entry(
        "hamilton/function_modifiers/expanders.py",
        "@deprecated parameterized_inputs",
        _RAISES.format(section="parametrized, parametrized_input and parameterized_inputs"),
    ),
    _entry(
        "hamilton/function_modifiers/macros.py",
        "@deprecated dynamic_transform",
        _RAISES.format(section="dynamic_transform and model"),
    ),
    _entry(
        "hamilton/function_modifiers/macros.py",
        "@deprecated model",
        _RAISES.format(section="dynamic_transform and model"),
    ),
    _entry(
        "hamilton/function_modifiers/macros.py",
        "@deprecated pipe",
        _RAISES.format(section="pipe"),
    ),
    _entry(
        "hamilton/telemetry.py",
        "@deprecated disable_telemetry",
        _RAISES.format(section="Telemetry functions"),
    ),
    _entry(
        "hamilton/telemetry.py",
        "@deprecated is_telemetry_enabled",
        _RAISES.format(section="Telemetry functions"),
    ),
    # Promises made in prose at the branch point.
    _entry(
        "hamilton/async_driver.py",
        "In Hamilton 2.0, we will be using an asynchronous constructor.",
        _NOT_A_PROMISE.format(
            reason="a plan, with no warning to users; AsyncDriver is a 1.x path that must keep "
            "working, so ainit() stays."
        ),
        in_source=True,
    ),
    _entry(
        "hamilton/caching/fingerprinting.py",
        "# TODO(2.0): revisit once/if a dependency-free `apache-hamilton-core` package",
        _NOT_A_PROMISE.format(
            reason="a note to maintainers; the core without pandas and numpy is Ticket 21's."
        ),
        in_source=True,
    ),
    _entry(
        "hamilton/driver.py",
        "backwards compatible. In Hamilton 2.0.0, this will be removed.",
        "Left for Ticket 21: _use_legacy_adapter decides whether a Driver without a result builder "
        "returns a pandas DataFrame, and the pandas default is Ticket 21's.",
        in_source=True,
    ),
    _entry(
        "hamilton/driver.py",
        '"display_graph=True is deprecated. It will be removed in the 2.0.0 release. "',
        _RAISES.format(section="display_graph")
        + " Driver.execute(display_graph=True) raises; the private execution path lost the "
        "parameter.",
    ),
    _entry(
        "hamilton/experimental/h_async.py",
        '"This module is deprecated and will be removed in Hamilton 2.0. "',
        "Took effect: importing the module raises an ImportError naming hamilton.async_driver "
        "and its migration section (hamilton.experimental.h_async).",
    ),
    _entry(
        "hamilton/experimental/h_cache.py",
        '"are deprecated and will be removed in Hamilton 2.0. "',
        "Took effect: importing the module raises an ImportError naming Builder.with_cache() "
        "and its migration section (hamilton.experimental.h_cache).",
    ),
    _entry(
        "hamilton/function_modifiers/configuration.py",
        "We will likely be deprecating this in 2.0, in favor of a (to be added) config.custom.",
        _NOT_A_PROMISE.format(
            reason="a hedged plan in a docstring, never warned about, whose replacement "
            "(config.custom) does not exist."
        ),
        in_source=True,
    ),
    _entry(
        "hamilton/function_modifiers_base.py",
        '"Import of this module is deprecated, and will be removed in a 2.0 release. In fact, "',
        "Took effect: importing the module raises an ImportError naming "
        "hamilton.function_modifiers.base and its migration section "
        "(hamilton.function_modifiers_base).",
    ),
    _entry(
        "hamilton/graph.py",
        '"in the 2.0.0 release.",',
        _RAISES.format(section="FunctionGraph.get_impacted_nodes"),
    ),
    _entry(
        "hamilton/lifecycle/__init__.py",
        "PrintLnHook = PrintLn  # for backwards compatibility -- this will be removed in 2.0",
        _RAISES.format(section="PrintLnHook") + " Reading the name raises a DeprecationError.",
    ),
    _entry(
        "hamilton/lifecycle/__init__.py",
        '"PrintLnHook",  # for backwards compatibility this will be removed in 2.0',
        "Took effect: PrintLnHook left __all__.",
    ),
    _entry(
        "hamilton/lifecycle/default.py",
        '"The `CacheAdapter` is deprecated and will be removed in Hamilton 2.0. "',
        _RAISES.format(section="CacheAdapter") + " Constructing it raises a DeprecationError.",
    ),
    _entry(
        "hamilton/models.py",
        "1.20.0 and fails from 2.0.0. Use @resolve instead.",
        "Took effect with @dynamic_transform and @model, which raise. The docstring now says so.",
    ),
    _entry(
        "hamilton/models.py",
        "# with the 2.0 release",
        'Not a promise of a 2.0 change: "will likely keep this in some way, but might change the '
        'name or the approach" promises no removal. BaseModel stays; the comment now says why, '
        "since @model, which used it, raises.",
    ),
    _entry(
        "hamilton/models.py",
        '@model is deprecated: it warns from 1.20.0 and fails from 2.0.0. Use @resolve instead."""',
        "Took effect with @model, which raises. The docstring now says so.",
    ),
    _entry(
        "hamilton/plugins/h_diskcache.py",
        '"The `DiskCacheAdapter` is deprecated and will be removed in Hamilton 2.0. "',
        _RAISES.format(section="DiskCacheAdapter")
        + " Constructing it raises a DeprecationError; so does evict_all_except_driver, which "
        "needed one on the Driver. evict_all_except stays.",
    ),
    _entry(
        "hamilton/plugins/h_openlineage.py",
        'default will change to ``"datasource"`` in a future major release.',
        _NOT_A_PROMISE.format(
            reason="it names no version, and its warning first shipped on 2026-09-29, too "
            "recently for users to have moved. The owner may decide to switch the default in 2.0."
        ),
        in_source=True,
    ),
    _entry(
        "hamilton/plugins/h_openlineage.py",
        '"bare table name). A future major release will default to "',
        "The warning of the entry above; kept with it.",
        in_source=True,
    ),
    _entry(
        "hamilton/plugins/polars_extensions.py",
        '"Using pre-1.0.0 Polars integration -- we will stop supporting this in Hamilton 2.0, '
        'so please upgrade your version of polars! "',
        "Took effect: with polars older than 1.0.0, importing the polars extension logs and "
        "raises an ImportError naming its migration section (Polars older than 1.0); the "
        "pre-1.0 integration is deleted.",
    ),
]


def main(argv: list[str]) -> None:
    package = pathlib.Path(argv[0]) if argv else pathlib.Path(hamilton.__file__).parent
    found = scan(package)
    ledger = {entry.promise: entry for entry in LEDGER}
    print(f"Promises for 2.0 under {package}: {len(found)} found, {len(LEDGER)} in the ledger.\n")
    for promise in found:
        entry = ledger.get(promise)
        print(
            f"- {promise}\n  {entry.treatment if entry else 'NOT IN THE LEDGER: decide and record it.'}"
        )
    missing = [entry for entry in LEDGER if entry.promise not in found]
    if missing:
        print(
            "\nIn the ledger, not in this source (a promise that took effect leaves none behind):\n"
        )
        for entry in missing:
            print(f"- {entry.promise}\n  {entry.treatment}")


if __name__ == "__main__":
    main(sys.argv[1:])
