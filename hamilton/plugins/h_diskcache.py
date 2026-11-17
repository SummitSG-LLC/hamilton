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
import typing
from typing import Any

import diskcache

from hamilton import driver, graph_types, node
from hamilton.dev_utils import deprecation

logger = logging.getLogger(__name__)

# The key under which the 1.x DiskCacheAdapter stored, for each node, the hashes of its versions it cached.
NODES_HISTORY_KEY = "_nodes_history"


def _removed_disk_cache_adapter(name: str) -> deprecation.DeprecationError:
    return deprecation.removed_in_2_0(
        name,
        explanation="The caching built into the Driver replaces DiskCacheAdapter, though not "
        "one-to-one. evict_all_except still prunes a cache directory DiskCacheAdapter wrote.",
        use_this="Builder.with_cache()",
        section="DiskCacheAdapter",
    )


def evict_all_except(nodes_to_keep: dict[str, node.Node], cache: diskcache.Cache) -> int:
    """Evicts from a cache that the 1.x DiskCacheAdapter wrote every node version except those passed.
    Remaining nodes may have multiple entries for different input values.
    """
    nodes_history: dict[str, list[str]] = cache.get(key=NODES_HISTORY_KEY)  # type: ignore

    new_nodes_history = dict()
    eviction_counter = 0
    for node_name, history in nodes_history.items():
        if len(history) < 1:
            continue

        if node_name in nodes_to_keep.keys():
            node_to_keep = nodes_to_keep[node_name]
            hash_to_keep = graph_types.hash_source_code(node_to_keep.callable, strip=True)
            history.remove(hash_to_keep)
            new_nodes_history[node_name] = [hash_to_keep]

        for hash_to_evict in history:
            cache.evict(tag=f"{node_name}.{hash_to_evict}")
            eviction_counter += 1

    cache.set(key=NODES_HISTORY_KEY, value=new_nodes_history)
    return eviction_counter


def evict_all_except_driver(dr: driver.Driver) -> typing.NoReturn:
    """Removed in 2.0 with DiskCacheAdapter, which it needed on the Driver: raises a DeprecationError.
    Call ``evict_all_except`` on the cache directory instead."""
    raise _removed_disk_cache_adapter("hamilton.plugins.h_diskcache.evict_all_except_driver")


class DiskCacheAdapter:
    """Removed in 2.0: constructing it raises a DeprecationError. Use ``Builder.with_cache()`` instead."""

    def __init__(self, *args: Any, **kwargs: Any):
        raise _removed_disk_cache_adapter("hamilton.plugins.h_diskcache.DiskCacheAdapter")
