"""Interval problems. Intervals are closed ``(start, end)`` pairs with start <= end."""

from __future__ import annotations

import heapq
from typing import Sequence

Interval = tuple[float, float]


def merge_intervals(intervals: Sequence[Interval]) -> list[Interval]:
    """Merge overlapping (or touching) intervals.

    Sort by start, then sweep. Time O(n log n), space O(n).
    """
    out: list[list[float]] = []
    for s, e in sorted(intervals):
        if s > e:
            raise ValueError(f"invalid interval ({s}, {e})")
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return [(s, e) for s, e in out]


def insert_interval(sorted_disjoint: Sequence[Interval], new: Interval) -> list[Interval]:
    """Insert into a sorted, non-overlapping list and merge. Time O(n), space O(n)."""
    out: list[Interval] = []
    s, e = new
    i, n = 0, len(sorted_disjoint)
    while i < n and sorted_disjoint[i][1] < s:
        out.append(sorted_disjoint[i])
        i += 1
    while i < n and sorted_disjoint[i][0] <= e:
        s = min(s, sorted_disjoint[i][0])
        e = max(e, sorted_disjoint[i][1])
        i += 1
    out.append((s, e))
    out.extend(sorted_disjoint[i:])
    return out


def min_meeting_rooms(meetings: Sequence[Interval]) -> int:
    """Minimum rooms so no two overlapping meetings share one.

    Meetings are half-open here: one ending at 10 frees its room for one
    starting at 10. Min-heap of end times. Time O(n log n), space O(n).
    """
    ends: list[float] = []
    for s, e in sorted(meetings):
        if ends and ends[0] <= s:
            heapq.heapreplace(ends, e)
        else:
            heapq.heappush(ends, e)
    return len(ends)


def can_attend_all(meetings: Sequence[Interval]) -> bool:
    """True if no two half-open meetings overlap. Time O(n log n)."""
    ms = sorted(meetings)
    return all(ms[i][1] <= ms[i + 1][0] for i in range(len(ms) - 1))


def interval_intersections(a: Sequence[Interval], b: Sequence[Interval]) -> list[Interval]:
    """Intersections of two sorted disjoint lists (two pointers). Time O(m + n)."""
    i = j = 0
    out = []
    while i < len(a) and j < len(b):
        lo = max(a[i][0], b[j][0])
        hi = min(a[i][1], b[j][1])
        if lo <= hi:
            out.append((lo, hi))
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out
