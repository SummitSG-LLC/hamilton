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

import logging
from typing import Any

from packaging import version

from hamilton import registry
from hamilton.dev_utils import deprecation

logger = logging.getLogger(__name__)

try:
    from xlsxwriter.workbook import Workbook
except ImportError:
    Workbook = type

try:
    import polars as pl
except ImportError as e:
    raise NotImplementedError("Polars is not installed.") from e

pl_version = version.Version(pl.__version__)
if pl_version < version.Version("1.0.0"):
    _message = deprecation.removed_in_2_0_message(
        f"Support for polars older than 1.0.0 (you have {pl_version})",
        explanation="Hamilton's polars integration needs polars 1.0.0 or newer.",
        use_this="polars>=1.0.0",
        section="Polars older than 1.0",
    )
    # Extension autoloading skips an extension whose import fails and logs that only at debug level,
    # so the message is logged here too, where a user with an old polars sees it.
    logger.warning(_message)
    raise ImportError(_message, name=__name__)
elif pl_version < version.Version("2.0.0"):
    from hamilton.plugins.polars_post_1_0_0_extensions import register_data_loaders
else:
    from hamilton.plugins.polars_post_2_0_0_extensions import register_data_loaders

register_data_loaders()

DATAFRAME_TYPE = pl.DataFrame
COLUMN_TYPE = pl.Series


def register_types():
    """Function to register the types for this extension."""
    registry.register_types("polars", DATAFRAME_TYPE, COLUMN_TYPE)


@registry.get_column.register(pl.DataFrame)
def get_column_polars(df: pl.DataFrame, column_name: str) -> pl.Series:
    return df[column_name]


@registry.fill_with_scalar.register(pl.DataFrame)
def fill_with_scalar_polars(df: pl.DataFrame, column_name: str, scalar_value: Any) -> pl.DataFrame:
    if not isinstance(scalar_value, pl.Series):
        scalar_value = [scalar_value]
    return df.with_columns(pl.Series(name=column_name, values=scalar_value))


register_types()
