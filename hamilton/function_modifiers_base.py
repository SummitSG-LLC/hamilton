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

"""Removed in 2.0: importing this module raises an ImportError that says what to use instead."""

from hamilton.dev_utils import deprecation

raise ImportError(
    deprecation.removed_in_2_0_message(
        "hamilton.function_modifiers_base",
        explanation="It only re-exported hamilton.function_modifiers.base, which was never a public API.",
        use_this="hamilton.function_modifiers.base",
        section="hamilton.function_modifiers_base",
    ),
    name=__name__,
)
