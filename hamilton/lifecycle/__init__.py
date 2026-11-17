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

from hamilton.dev_utils import deprecation

from .api import (  # noqa: F401
    EdgeConnectionHook,
    GraphAdapter,
    GraphConstructionHook,
    GraphExecutionHook,
    LegacyResultMixin,
    NodeExecutionHook,
    NodeExecutionMethod,
    ResultBuilder,
    StaticValidator,
    TaskExecutionHook,
    TaskGroupingHook,
    TaskReturnHook,
    TaskSubmissionHook,
)
from .base import LifecycleAdapter  # noqa: F401
from .default import (  # noqa: F401
    FunctionInputOutputTypeChecker,
    GracefulErrorAdapter,
    NoEdgeAndInputTypeChecking,
    PDBDebugger,
    PrintLn,
    SlowDownYouMoveTooFast,
    accept_error_sentinels,
)


def __getattr__(name: str):
    # The 1.x alias PrintLnHook is gone; reading it names its replacement instead of failing silently.
    # A DeprecationError rather than an AttributeError, because `from hamilton.lifecycle import PrintLnHook`
    # replaces an AttributeError with a generic ImportError and drops its message.
    if name == "PrintLnHook":
        raise deprecation.removed_in_2_0(
            "hamilton.lifecycle.PrintLnHook",
            explanation="It was another name for PrintLn.",
            use_this="hamilton.lifecycle.PrintLn",
            section="PrintLnHook",
        )
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# All the following types are public facing
__all__ = [
    "LifecycleAdapter",
    "LegacyResultMixin",
    "ResultBuilder",
    "GraphAdapter",
    "NodeExecutionHook",
    "EdgeConnectionHook",
    "PrintLn",
    "PDBDebugger",
    "GraphConstructionHook",
    "GraphExecutionHook",
    "NodeExecutionMethod",
    "StaticValidator",
    "TaskExecutionHook",
    "TaskGroupingHook",
    "FunctionInputOutputTypeChecker",
    "NoEdgeAndInputTypeChecking",
    "TaskReturnHook",
    "TaskSubmissionHook",
]
