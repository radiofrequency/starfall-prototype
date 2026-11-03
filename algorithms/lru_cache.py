"""LRU cache with O(1) get and put.

A dict maps keys to nodes of a doubly linked list ordered from most to least
recently used. Sentinel head/tail nodes remove edge cases. (``OrderedDict``
would do the same job; this spells out the mechanics.)
"""

from __future__ import annotations

from typing import Any, Hashable, Optional


class _Node:
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: Any = None, value: Any = None) -> None:
        self.key, self.value = key, value
        self.prev: Optional[_Node] = None
        self.next: Optional[_Node] = None


class LRUCache:
    """Fixed-capacity cache that evicts the least recently used key.

    ``get`` and ``put`` are O(1) time; space O(capacity).
    """

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._map: dict[Hashable, _Node] = {}
        self._head, self._tail = _Node(), _Node()      # head.next = MRU, tail.prev = LRU
        self._head.next, self._tail.prev = self._tail, self._head
        self.hits = self.misses = self.evictions = 0

    def __len__(self) -> int:
        return len(self._map)

    def __contains__(self, key: Hashable) -> bool:     # does not touch recency
        return key in self._map

    def _unlink(self, node: _Node) -> None:
        node.prev.next, node.next.prev = node.next, node.prev

    def _push_front(self, node: _Node) -> None:
        node.prev, node.next = self._head, self._head.next
        self._head.next.prev = node
        self._head.next = node

    def get(self, key: Hashable, default: Any = None) -> Any:
        """Value for ``key`` (marking it most recently used), else ``default``."""
        node = self._map.get(key)
        if node is None:
            self.misses += 1
            return default
        self.hits += 1
        self._unlink(node)
        self._push_front(node)
        return node.value

    def put(self, key: Hashable, value: Any) -> Optional[Hashable]:
        """Insert or update ``key``; return the evicted key, if any."""
        node = self._map.get(key)
        if node is not None:
            node.value = value
            self._unlink(node)
            self._push_front(node)
            return None
        node = _Node(key, value)
        self._map[key] = node
        self._push_front(node)
        if len(self._map) > self.capacity:
            lru = self._tail.prev
            self._unlink(lru)
            del self._map[lru.key]
            self.evictions += 1
            return lru.key
        return None

    def keys(self) -> list[Hashable]:
        """Keys from most to least recently used. O(n)."""
        out, node = [], self._head.next
        while node is not self._tail:
            out.append(node.key)
            node = node.next
        return out
