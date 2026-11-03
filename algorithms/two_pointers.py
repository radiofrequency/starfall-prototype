"""Two-pointer techniques on arrays."""

from __future__ import annotations

from typing import Optional, Sequence


def two_sum_sorted(a: Sequence[float], target: float) -> Optional[tuple[int, int]]:
    """Indices (i < j) in sorted ``a`` with a[i] + a[j] == target, or None.

    Time O(n), space O(1).
    """
    i, j = 0, len(a) - 1
    while i < j:
        s = a[i] + a[j]
        if s == target:
            return i, j
        if s < target:
            i += 1
        else:
            j -= 1
    return None


def three_sum(nums: Sequence[int], target: int = 0) -> list[tuple[int, int, int]]:
    """All unique value triples summing to ``target``, each sorted, list sorted.

    Sort, fix one element, two-pointer the rest, skip duplicates.
    Time O(n^2), space O(1) beyond sorting and output.
    """
    a = sorted(nums)
    out = []
    n = len(a)
    for i in range(n - 2):
        if i > 0 and a[i] == a[i - 1]:
            continue
        lo, hi = i + 1, n - 1
        while lo < hi:
            s = a[i] + a[lo] + a[hi]
            if s < target:
                lo += 1
            elif s > target:
                hi -= 1
            else:
                out.append((a[i], a[lo], a[hi]))
                lo += 1
                hi -= 1
                while lo < hi and a[lo] == a[lo - 1]:
                    lo += 1
                while lo < hi and a[hi] == a[hi + 1]:
                    hi -= 1
    return out


def container_with_most_water(heights: Sequence[float]) -> float:
    """Max area between two lines. Move the shorter side inwards. Time O(n), space O(1)."""
    i, j = 0, len(heights) - 1
    best = 0
    while i < j:
        best = max(best, (j - i) * min(heights[i], heights[j]))
        if heights[i] < heights[j]:
            i += 1
        else:
            j -= 1
    return best


def trap_rain_water(heights: Sequence[float]) -> float:
    """Water trapped between bars. Two pointers with running maxima. Time O(n), space O(1)."""
    i, j = 0, len(heights) - 1
    left_max = right_max = 0
    water = 0
    while i < j:
        if heights[i] < heights[j]:
            left_max = max(left_max, heights[i])
            water += left_max - heights[i]
            i += 1
        else:
            right_max = max(right_max, heights[j])
            water += right_max - heights[j]
            j -= 1
    return water


def remove_duplicates_sorted(a: list) -> int:
    """Deduplicate a sorted list in place; return the new length k (a[:k] is unique).

    Slow/fast pointers. Time O(n), space O(1).
    """
    if not a:
        return 0
    k = 1
    for x in a[1:]:
        if x != a[k - 1]:
            a[k] = x
            k += 1
    return k


def is_palindrome(s: str) -> bool:
    """Palindrome check ignoring case and non-alphanumerics. Time O(n), space O(1)."""
    i, j = 0, len(s) - 1
    while i < j:
        if not s[i].isalnum():
            i += 1
        elif not s[j].isalnum():
            j -= 1
        elif s[i].lower() != s[j].lower():
            return False
        else:
            i += 1
            j -= 1
    return True
