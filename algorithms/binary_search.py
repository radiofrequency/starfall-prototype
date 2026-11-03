"""Binary search variants. All run in O(log n) time and O(1) space unless noted."""

from __future__ import annotations

from typing import Callable, Sequence


def lower_bound(a: Sequence[float], x: float) -> int:
    """First index i with a[i] >= x (len(a) if none). Same as ``bisect_left``."""
    lo, hi = 0, len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


def upper_bound(a: Sequence[float], x: float) -> int:
    """First index i with a[i] > x (len(a) if none). Same as ``bisect_right``."""
    lo, hi = 0, len(a)
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] <= x:
            lo = mid + 1
        else:
            hi = mid
    return lo


def binary_search(a: Sequence[float], x: float) -> int:
    """Index of ``x`` in sorted ``a`` (first occurrence) or -1."""
    i = lower_bound(a, x)
    return i if i < len(a) and a[i] == x else -1


def search_range(a: Sequence[float], x: float) -> tuple[int, int]:
    """(first, last) index of ``x`` in sorted ``a``, or (-1, -1)."""
    i = lower_bound(a, x)
    if i == len(a) or a[i] != x:
        return -1, -1
    return i, upper_bound(a, x) - 1


def search_rotated(a: Sequence[float], x: float) -> int:
    """Index of ``x`` in a sorted array of distinct values rotated at an unknown pivot, or -1.

    At each step one half is sorted; check whether x lies in it.
    """
    lo, hi = 0, len(a) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if a[mid] == x:
            return mid
        if a[lo] <= a[mid]:                 # left half sorted
            if a[lo] <= x < a[mid]:
                hi = mid - 1
            else:
                lo = mid + 1
        else:                               # right half sorted
            if a[mid] < x <= a[hi]:
                lo = mid + 1
            else:
                hi = mid - 1
    return -1


def find_min_rotated(a: Sequence[float]) -> float:
    """Minimum of a rotated sorted array of distinct values."""
    if not a:
        raise ValueError("empty array")
    lo, hi = 0, len(a) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] > a[hi]:
            lo = mid + 1
        else:
            hi = mid
    return a[lo]


def first_true(lo: int, hi: int, pred: Callable[[int], bool]) -> int:
    """Smallest integer in [lo, hi] where a monotone ``pred`` is True, or hi + 1.

    ``pred`` must be False...False True...True on the range.
    Time O(log(hi - lo)) calls to ``pred``.
    """
    end = hi + 1
    while lo < end:
        mid = (lo + end) // 2
        if pred(mid):
            end = mid
        else:
            lo = mid + 1
    return lo


def integer_sqrt(n: int) -> int:
    """floor(sqrt(n)) for n >= 0 using search on the answer. O(log n)."""
    if n < 0:
        raise ValueError("n must be non-negative")
    return first_true(0, n + 1, lambda m: m * m > n) - 1


def min_eating_speed(piles: Sequence[int], hours: int) -> int:
    """'Koko eating bananas': smallest integer speed to finish all piles in ``hours``.

    Search on the answer over [1, max(piles)]. Time O(n log max(piles)).
    """
    if hours < len(piles):
        raise ValueError("need at least one hour per pile")
    return first_true(1, max(piles), lambda k: sum((p + k - 1) // k for p in piles) <= hours)
