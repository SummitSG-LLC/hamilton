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

"""How Hamilton's own deprecations reach users: on the release clock, as warnings users can filter."""

import ast
import dataclasses
import inspect
import pathlib
import warnings

import pytest

import hamilton
from hamilton.dev_utils.deprecation import DeprecationError, deprecated

from tests.promises_for_2_0 import deprecated_calls

_CURRENT_VERSION_POSITION = [field.name for field in dataclasses.fields(deprecated)].index(
    "current_version"
)


@pytest.mark.parametrize(
    "source",
    [
        "from hamilton.dev_utils.deprecation import deprecated\ndeprecated()",
        "from hamilton.dev_utils.deprecation import deprecated as old\nold()",
        "from hamilton.dev_utils import deprecation\ndeprecation.deprecated()",
        "import hamilton.dev_utils.deprecation as d\nd.deprecated()",
        "import hamilton.dev_utils.deprecation\nhamilton.dev_utils.deprecation.deprecated()",
        "from hamilton import dev_utils\ndev_utils.deprecation.deprecated()",
        "from ..dev_utils.deprecation import deprecated\ndeprecated()",
        "from ..dev_utils import deprecation\ndeprecation.deprecated()",
        "from .. import dev_utils\ndev_utils.deprecation.deprecated()",
    ],
)
def test_the_lock_finds_deprecated_under_every_import_form(source):
    tree = ast.parse(source)
    assert len(deprecated_calls(tree, "hamilton.function_modifiers.example")) == 1


def test_no_deprecation_in_hamilton_pins_its_current_version():
    """A pinned current_version freezes a deprecation's clock: it never starts warning, or warns forever
    and never fails. Every deprecation must read the running release instead."""
    package = pathlib.Path(hamilton.__file__).parent
    pinned = []
    for path in sorted(package.rglob("*.py")):
        relative = path.relative_to(package.parent).with_suffix("")
        is_package = relative.name == "__init__"
        module = ".".join(relative.parent.parts if is_package else relative.parts)
        tree = ast.parse(path.read_text(), filename=str(path))
        for call in deprecated_calls(tree, module, is_package):
            if len(call.args) > _CURRENT_VERSION_POSITION or any(
                keyword.arg == "current_version" for keyword in call.keywords
            ):
                pinned.append(f"{path.relative_to(package.parent)}:{call.lineno}")
    assert pinned == []


def _decorated_function(**overrides):
    arguments = dict(
        warn_starting=(1, 0, 0),
        fail_starting=(2, 0, 0),
        use_this=None,
        explanation="Use the new one.",
        migration_guide="https://example.com/guide",
        current_version=(1, 5, 0),
    )

    @deprecated(**{**arguments, **overrides})
    def old_api() -> str:
        return "result"

    return old_api


def _decorated_class(**overrides):
    arguments = dict(
        warn_starting=(1, 0, 0),
        fail_starting=(2, 0, 0),
        use_this=None,
        explanation="Use the new one.",
        migration_guide="https://example.com/guide",
        current_version=(1, 5, 0),
    )

    @deprecated(**{**arguments, **overrides})
    class OldDecorator:
        def __call__(self) -> str:
            return "result"

    return OldDecorator()


@pytest.mark.parametrize(
    "decorate", [_decorated_function, _decorated_class], ids=["function", "class"]
)
def test_deprecation_warns_with_a_future_warning_at_the_calling_line(decorate):
    old_api = decorate()
    with pytest.warns(FutureWarning, match="2.0.0") as record:
        calling_line = inspect.currentframe().f_lineno + 1
        assert old_api() == "result"
    assert len(record) == 1
    assert (record[0].filename, record[0].lineno) == (__file__, calling_line)


@pytest.mark.parametrize(
    "decorate", [_decorated_function, _decorated_class], ids=["function", "class"]
)
def test_deprecation_warning_follows_the_warning_filters(decorate):
    old_api = decorate()
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        with pytest.raises(FutureWarning):
            old_api()
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("ignore", FutureWarning)
        assert old_api() == "result"
    assert record == []


@pytest.mark.parametrize(
    "decorate", [_decorated_function, _decorated_class], ids=["function", "class"]
)
def test_custom_warn_action_replaces_the_warning(decorate):
    messages = []
    old_api = decorate(warn_action=messages.append)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert old_api() == "result"
    assert len(messages) == 1


def _deprecate_class(messages: list[str]):
    return deprecated(
        warn_starting=(1, 0, 0),
        fail_starting=(2, 0, 0),
        use_this=None,
        explanation="Use the new one.",
        migration_guide="https://example.com/guide",
        current_version=(1, 5, 0),
        warn_action=messages.append,
    )


def test_plain_subclass_of_a_deprecated_class_warns_once_under_its_parents_name():
    messages = []

    @_deprecate_class(messages)
    class Parent:
        def __call__(self) -> str:
            return "result"

    class Child(Parent):
        pass

    class ChildCallingSuper(Parent):
        def __call__(self) -> str:
            return super().__call__()

    assert Child()() == "result"
    assert ChildCallingSuper()() == "result"
    assert [message.split(" ")[0] for message in messages] == [Parent.__qualname__] * 2


@pytest.mark.parametrize("calls_super", [False, True], ids=["inherits-call", "overrides-call"])
def test_deprecated_subclass_of_a_deprecated_class_warns_once_under_its_own_name(calls_super):
    messages = []

    @_deprecate_class(messages)
    class Parent:
        def __call__(self) -> str:
            return "result"

    if calls_super:

        @_deprecate_class(messages)
        class Child(Parent):
            def __call__(self) -> str:
                return super().__call__()

    else:

        @_deprecate_class(messages)
        class Child(Parent):
            pass

    assert Child()() == "result"
    assert [message.split(" ")[0] for message in messages] == [Child.__qualname__]


@pytest.mark.parametrize("version", [(2, 0, 0), (2, 1, 0)], ids=["2.0.0", "2.1.0"])
def test_deprecated_subclass_of_a_deprecated_class_fails_under_its_own_name(version):
    def deprecate(cls):
        return deprecated(
            warn_starting=(1, 0, 0),
            fail_starting=(2, 0, 0),
            use_this=None,
            explanation="Use the new one.",
            migration_guide="https://example.com/guide",
            current_version=version,
        )(cls)

    @deprecate
    class Parent:
        def __call__(self) -> str:
            return "result"

    @deprecate
    class Child(Parent):
        pass

    with pytest.raises(DeprecationError, match=f"^{Child.__qualname__} has been deprecated"):
        Child()()
