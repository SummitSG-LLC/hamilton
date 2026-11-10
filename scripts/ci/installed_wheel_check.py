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

"""Builds and executes a small pure-Python graph with an installed ``apache-hamilton`` wheel.

The installed-wheel CI job copies this file out of the repository and runs it with the Python of
an environment that holds only the built wheel and its dependencies:

    python installed_wheel_check.py /path/to/source/checkout

It fails when ``hamilton`` is imported from the source checkout instead of the environment, which
would let a file that the wheel leaves out go unnoticed.
"""

import pathlib
import sys

import hamilton
from hamilton import ad_hoc_utils, driver


def doubled(number: int) -> int:
    return number * 2


def doubled_plus_one(doubled: int) -> int:
    return doubled + 1


def main(source_checkout: str) -> None:
    imported_from = pathlib.Path(hamilton.__file__).resolve()
    if imported_from.is_relative_to(pathlib.Path(source_checkout).resolve()):
        sys.exit(f"hamilton was imported from the source checkout: {imported_from}")

    module = ad_hoc_utils.create_temporary_module(doubled, doubled_plus_one)
    dr = driver.Builder().with_modules(module).build()
    result = dr.execute(["doubled", "doubled_plus_one"], inputs={"number": 20})
    if result != {"doubled": 40, "doubled_plus_one": 41}:
        sys.exit(f"unexpected result from the installed wheel: {result!r}")
    version = ".".join(str(part) for part in hamilton.__version__)
    print(f"apache-hamilton {version} from {imported_from.parent}: {result}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(f"usage: {sys.argv[0]} <source checkout>")
    main(sys.argv[1])
