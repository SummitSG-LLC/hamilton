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

"""
Telemetry has been removed from Hamilton.

The two functions of this module remain only so that a call to either says what to do. Since 2.0, both
raise a DeprecationError: remove the call.
"""

import typing

from hamilton.dev_utils.deprecation import DeprecationError, removed_in_2_0


def _removed_telemetry_function(name: str) -> DeprecationError:
    return removed_in_2_0(
        name,
        explanation="Telemetry has been removed from Hamilton, so there is nothing to switch off "
        "or check. Remove the call.",
        use_this=None,
        section="Telemetry functions",
    )


def disable_telemetry() -> typing.NoReturn:
    """Removed in 2.0: raises a DeprecationError. Telemetry has been removed; remove the call."""
    raise _removed_telemetry_function("telemetry.disable_telemetry()")


def is_telemetry_enabled() -> typing.NoReturn:
    """Removed in 2.0: raises a DeprecationError. Telemetry has been removed; remove the call."""
    raise _removed_telemetry_function("telemetry.is_telemetry_enabled()")
