#!/usr/bin/env bash
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

# Measures the 1.x paths at the 2.0 branch point, as the reference results in benchmarks/results/
# were measured: a detached worktree of the branch-point commit, and for each Python a fresh
# environment that holds Hamilton's required dependencies and nothing else.
#
#   benchmarks/reference.sh OUT_DIR [PYTHON ...]     (default Pythons: 3.15 3.14t; needs uv)
#
# The environments get the newest releases of the dependencies; each result file lists the
# versions it measured.

set -euo pipefail

BRANCH_POINT=077b7a1d59cddac874f4d08c8f9fc2a6cbd610e1

if [[ $# -lt 1 ]]; then
  echo "usage: $0 OUT_DIR [PYTHON ...]" >&2
  exit 2
fi
out=$(mkdir -p "$1" && cd "$1" && pwd)
shift
pythons=("$@")
if [[ ${#pythons[@]} -eq 0 ]]; then
  pythons=(3.15 3.14t)
fi

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
repo=$(cd "$here/.." && pwd)
work=$(mktemp -d)
cleanup() {
  git -C "$repo" worktree remove --force "$work/checkout" 2>/dev/null || true
  rm -rf "$work"
}
trap cleanup EXIT

git -C "$repo" worktree add --quiet --detach "$work/checkout" "$BRANCH_POINT"

for python in "${pythons[@]}"; do
  env="$work/env-$python"
  uv venv --quiet --python "$python" "$env"
  # Installing the checkout brings exactly its required dependencies; the installed copy of
  # Hamilton is then removed so that the worker imports the checkout's hamilton/ package.
  uv pip install --quiet --python "$env/bin/python" "$work/checkout"
  uv pip uninstall --quiet --python "$env/bin/python" apache-hamilton
  "$env/bin/python" "$here/harness.py" run \
    --side "1x:checkout=$work/checkout,python=$env/bin/python" \
    --out "$out/reference-1x-${BRANCH_POINT:0:8}-python-$python.json" --force \
    --note "${BENCHMARK_NOTE:-}"
done
