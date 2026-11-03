"""Dynamic programming classics."""

from __future__ import annotations

from bisect import bisect_left
from typing import Sequence


def knapsack_01(weights: Sequence[int], values: Sequence[float], capacity: int) -> tuple[float, list[int]]:
    """0/1 knapsack: best total value within ``capacity`` and the chosen item indices.

    Full table so the choice can be reconstructed. Time O(n*W), space O(n*W),
    where W = capacity (pseudo-polynomial). Weights must be non-negative ints.
    """
    if len(weights) != len(values):
        raise ValueError("weights and values must have the same length")
    if capacity < 0 or any(w < 0 for w in weights):
        raise ValueError("capacity and weights must be non-negative")
    n = len(weights)
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        w, v = weights[i - 1], values[i - 1]
        prev, row = dp[i - 1], dp[i]
        for c in range(capacity + 1):
            row[c] = prev[c]
            if w <= c and prev[c - w] + v > row[c]:
                row[c] = prev[c - w] + v
    chosen, c = [], capacity
    for i in range(n, 0, -1):
        if dp[i][c] != dp[i - 1][c]:
            chosen.append(i - 1)
            c -= weights[i - 1]
    return dp[n][capacity], chosen[::-1]


def knapsack_01_value(weights: Sequence[int], values: Sequence[float], capacity: int) -> float:
    """Value-only 0/1 knapsack with a 1-D table (iterate capacity downwards).

    Time O(n*W), space O(W).
    """
    dp = [0] * (capacity + 1)
    for w, v in zip(weights, values):
        for c in range(capacity, w - 1, -1):
            dp[c] = max(dp[c], dp[c - w] + v)
    return dp[capacity]


def longest_increasing_subsequence(nums: Sequence[float]) -> list[float]:
    """One longest strictly increasing subsequence (patience sorting).

    ``tails[k]`` holds the index of the smallest tail of an increasing
    subsequence of length k+1; predecessor links rebuild the answer.
    Time O(n log n), space O(n).
    """
    tails: list[int] = []
    tail_vals: list[float] = []
    prev = [-1] * len(nums)
    for i, x in enumerate(nums):
        k = bisect_left(tail_vals, x)
        if k == len(tails):
            tails.append(i)
            tail_vals.append(x)
        else:
            tails[k] = i
            tail_vals[k] = x
        prev[i] = tails[k - 1] if k > 0 else -1
    out = []
    i = tails[-1] if tails else -1
    while i != -1:
        out.append(nums[i])
        i = prev[i]
    return out[::-1]


def edit_distance(a: str, b: str) -> int:
    """Levenshtein distance (insert, delete, substitute; each cost 1).

    Two rolling rows. Time O(len(a)*len(b)), space O(min(len(a), len(b))).
    """
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cur[j] = min(prev[j] + 1,                  # delete
                         cur[j - 1] + 1,               # insert
                         prev[j - 1] + (ca != cb))     # substitute / match
        prev = cur
    return prev[-1]


def coin_change_min_coins(coins: Sequence[int], amount: int) -> int:
    """Fewest coins summing to ``amount`` (unlimited supply), or -1 if impossible.

    Time O(len(coins) * amount), space O(amount).
    """
    if amount < 0:
        raise ValueError("amount must be non-negative")
    INF = amount + 1
    dp = [0] + [INF] * amount
    for x in range(1, amount + 1):
        for c in coins:
            if 0 < c <= x and dp[x - c] + 1 < dp[x]:
                dp[x] = dp[x - c] + 1
    return dp[amount] if dp[amount] != INF else -1


def coin_change_ways(coins: Sequence[int], amount: int) -> int:
    """Number of combinations (order-insensitive) making ``amount``.

    Coins in the outer loop so each multiset is counted once.
    Time O(len(coins) * amount), space O(amount).
    """
    dp = [1] + [0] * amount
    for c in coins:
        if c <= 0:
            continue
        for x in range(c, amount + 1):
            dp[x] += dp[x - c]
    return dp[amount]
