"""Heap / priority-queue problems (``heapq`` is a binary min-heap)."""

from __future__ import annotations

import heapq
from collections import Counter
from typing import Hashable, Iterable, Optional, Sequence


def top_k_largest(nums: Iterable[float], k: int) -> list[float]:
    """The k largest values, largest first.

    Keeps a min-heap of size k. Time O(n log k), space O(k).
    """
    if k <= 0:
        return []
    heap: list[float] = []
    for x in nums:
        if len(heap) < k:
            heapq.heappush(heap, x)
        elif x > heap[0]:
            heapq.heapreplace(heap, x)
    return sorted(heap, reverse=True)


def kth_largest(nums: Sequence[float], k: int) -> float:
    """k-th largest element (1-based). Time O(n log k), space O(k)."""
    if not 1 <= k <= len(nums):
        raise ValueError("k out of range")
    return top_k_largest(nums, k)[-1]


def top_k_frequent(items: Iterable[Hashable], k: int) -> list[Hashable]:
    """The k most frequent items, most frequent first (ties: first seen first).

    Time O(n + m log k) for m distinct items, space O(m).
    """
    counts = Counter(items)                        # preserves first-seen order
    order = {x: i for i, x in enumerate(counts)}
    heap: list[tuple[int, int, Hashable]] = []     # (count, -first_seen, item)
    for x, c in counts.items():
        entry = (c, -order[x], x)
        if len(heap) < k:
            heapq.heappush(heap, entry)
        elif entry > heap[0]:
            heapq.heapreplace(heap, entry)
    return [x for _, _, x in sorted(heap, reverse=True)]


def merge_k_sorted(lists: Sequence[Sequence[float]]) -> list[float]:
    """Merge k sorted lists. Heap of (value, list index, element index).

    Time O(N log k) for N total elements, space O(k) beyond the output.
    Stable: equal values come out in list order.
    """
    heap = [(lst[0], i, 0) for i, lst in enumerate(lists) if lst]
    heapq.heapify(heap)
    out = []
    while heap:
        v, i, j = heapq.heappop(heap)
        out.append(v)
        if j + 1 < len(lists[i]):
            heapq.heappush(heap, (lists[i][j + 1], i, j + 1))
    return out


class ListNode:
    """Singly linked list node, for the linked-list version of merge-k."""

    __slots__ = ("val", "next")

    def __init__(self, val: float, next: Optional["ListNode"] = None) -> None:
        self.val, self.next = val, next

    @staticmethod
    def from_list(values: Iterable[float]) -> Optional["ListNode"]:
        head = cur = ListNode(0)
        for v in values:
            cur.next = ListNode(v)
            cur = cur.next
        return head.next

    def to_list(self) -> list[float]:
        out, node = [], self
        while node:
            out.append(node.val)
            node = node.next
        return out


def merge_k_sorted_linked(heads: Sequence[Optional[ListNode]]) -> Optional[ListNode]:
    """Merge k sorted linked lists by relinking nodes. Time O(N log k), space O(k)."""
    heap = [(h.val, i, h) for i, h in enumerate(heads) if h]
    heapq.heapify(heap)
    dummy = tail = ListNode(0)
    while heap:
        _, i, node = heapq.heappop(heap)
        tail.next = node
        tail = node
        if node.next:
            heapq.heappush(heap, (node.next.val, i, node.next))
    tail.next = None
    return dummy.next


class RunningMedian:
    """Median of a stream with two heaps (max-heap low half, min-heap high half).

    ``add`` O(log n), ``median`` O(1).
    """

    def __init__(self) -> None:
        self._lo: list[float] = []   # negated values: max-heap
        self._hi: list[float] = []

    def add(self, x: float) -> None:
        if self._lo and x > -self._lo[0]:
            heapq.heappush(self._hi, x)
        else:
            heapq.heappush(self._lo, -x)
        if len(self._lo) > len(self._hi) + 1:
            heapq.heappush(self._hi, -heapq.heappop(self._lo))
        elif len(self._hi) > len(self._lo):
            heapq.heappush(self._lo, -heapq.heappop(self._hi))

    def median(self) -> float:
        if not self._lo:
            raise ValueError("no data")
        if len(self._lo) > len(self._hi):
            return -self._lo[0]
        return (-self._lo[0] + self._hi[0]) / 2
