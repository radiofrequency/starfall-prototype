"""Sliding-window problems. Each pointer moves forward only, so they are linear."""

from __future__ import annotations

from collections import Counter, deque
from typing import Sequence


def longest_substring_without_repeats(s: str) -> int:
    """Length of the longest substring with all-distinct characters.

    Track the last index of each char; jump the left edge past a repeat.
    Time O(n), space O(alphabet).
    """
    last: dict[str, int] = {}
    left = best = 0
    for right, ch in enumerate(s):
        if ch in last and last[ch] >= left:
            left = last[ch] + 1
        last[ch] = right
        best = max(best, right - left + 1)
    return best


def min_window_substring(s: str, t: str) -> str:
    """Shortest substring of ``s`` containing every char of ``t`` (with multiplicity).

    Returns "" if none. Time O(len(s) + len(t)), space O(alphabet).
    """
    if not t or not s:
        return ""
    need = Counter(t)
    missing = len(t)
    left = 0
    best = (0, float("inf"))
    for right, ch in enumerate(s):
        if need[ch] > 0:
            missing -= 1
        need[ch] -= 1
        if missing == 0:
            while need[s[left]] < 0:            # drop surplus chars from the left
                need[s[left]] += 1
                left += 1
            if right - left < best[1] - best[0]:
                best = (left, right)
            need[s[left]] += 1                  # give up one required char and continue
            missing += 1
            left += 1
    return "" if best[1] == float("inf") else s[best[0]: best[1] + 1]


def max_sliding_window(nums: Sequence[float], k: int) -> list[float]:
    """Maximum of each length-k window.

    Monotonic deque of indices with decreasing values. Time O(n), space O(k).
    """
    if k <= 0:
        raise ValueError("k must be positive")
    dq: deque[int] = deque()
    out = []
    for i, x in enumerate(nums):
        while dq and nums[dq[-1]] <= x:
            dq.pop()
        dq.append(i)
        if dq[0] <= i - k:
            dq.popleft()
        if i >= k - 1:
            out.append(nums[dq[0]])
    return out


def min_subarray_len(target: float, nums: Sequence[float]) -> int:
    """Shortest contiguous subarray with sum >= target (positive numbers), or 0.

    Time O(n), space O(1).
    """
    if any(x <= 0 for x in nums):
        raise ValueError("numbers must be positive for the sliding-window method")
    left = total = 0
    best = len(nums) + 1
    for right, x in enumerate(nums):
        total += x
        while total >= target:
            best = min(best, right - left + 1)
            total -= nums[left]
            left += 1
    return 0 if best == len(nums) + 1 else best


def max_sum_subarray_of_size_k(nums: Sequence[float], k: int) -> float:
    """Largest sum over all length-k windows. Time O(n), space O(1)."""
    if not 1 <= k <= len(nums):
        raise ValueError("k out of range")
    window = sum(nums[:k])
    best = window
    for i in range(k, len(nums)):
        window += nums[i] - nums[i - k]
        best = max(best, window)
    return best
