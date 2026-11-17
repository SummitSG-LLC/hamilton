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

import inspect
import pathlib

import pytest

from hamilton import graph_types, node

diskcache = pytest.importorskip("diskcache")
h_diskcache = pytest.importorskip("hamilton.plugins.h_diskcache")


def _callable_to_node(callable) -> node.Node:
    return node.Node(
        name=callable.__name__,
        typ=inspect.signature(callable).return_annotation,
        callabl=callable,
    )


def _a_modulo_7(external_input: int) -> int:
    return external_input % 7


def _a_modulo_5(external_input: int) -> int:
    return external_input % 5


def test_evict_all_except_prunes_a_cache_the_1_x_adapter_wrote(tmp_path: pathlib.Path):
    """evict_all_except outlives DiskCacheAdapter, so it can prune a cache directory that 1.x wrote:
    each result tagged "<node>.<source hash>", and under "_nodes_history" the hashes of each node."""
    kept, evicted = _callable_to_node(_a_modulo_7), _callable_to_node(_a_modulo_5)
    kept_hash = graph_types.hash_source_code(kept.callable, strip=True)
    evicted_hash = graph_types.hash_source_code(evicted.callable, strip=True)
    with diskcache.Cache(directory=str(tmp_path)) as cache:
        cache.add(key=(kept_hash, 10), value=3, tag=f"A.{kept_hash}")
        cache.add(key=(evicted_hash, 10), value=0, tag=f"A.{evicted_hash}")
        cache.set(key="_nodes_history", value={"A": [kept_hash, evicted_hash]})

        eviction_counter = h_diskcache.evict_all_except(nodes_to_keep={"A": kept}, cache=cache)

        assert eviction_counter == 1
        assert cache.get((kept_hash, 10)) == 3
        assert cache.get((evicted_hash, 10)) is None
        assert cache.get("_nodes_history") == {"A": [kept_hash]}
