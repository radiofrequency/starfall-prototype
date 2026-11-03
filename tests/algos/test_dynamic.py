import itertools
import random

import pytest

from algorithms.dynamic import (
    coin_change_min_coins, coin_change_ways, edit_distance, knapsack_01, knapsack_01_value,
    longest_increasing_subsequence,
)


def brute_knapsack(w, v, cap):
    best = 0
    for r in range(len(w) + 1):
        for combo in itertools.combinations(range(len(w)), r):
            if sum(w[i] for i in combo) <= cap:
                best = max(best, sum(v[i] for i in combo))
    return best


def test_knapsack_example():
    value, chosen = knapsack_01([1, 3, 4, 5], [1, 4, 5, 7], 7)
    assert value == 9 and chosen == [1, 2]


def test_knapsack_random_against_brute_force():
    rng = random.Random(0)
    for _ in range(200):
        n = rng.randint(0, 8)
        w = [rng.randint(0, 10) for _ in range(n)]
        v = [rng.randint(0, 20) for _ in range(n)]
        cap = rng.randint(0, 25)
        value, chosen = knapsack_01(w, v, cap)
        assert value == brute_knapsack(w, v, cap) == knapsack_01_value(w, v, cap)
        assert sum(w[i] for i in chosen) <= cap and sum(v[i] for i in chosen) == value


def test_knapsack_validates():
    with pytest.raises(ValueError):
        knapsack_01([1], [1, 2], 3)


def is_strictly_increasing_subseq(sub, seq):
    it = iter(seq)
    return all(x in it for x in sub) and all(a < b for a, b in zip(sub, sub[1:]))


def brute_lis_len(seq):
    for r in range(len(seq), 0, -1):
        for combo in itertools.combinations(seq, r):
            if all(a < b for a, b in zip(combo, combo[1:])):
                return r
    return 0


def test_lis():
    assert len(longest_increasing_subsequence([10, 9, 2, 5, 3, 7, 101, 18])) == 4
    assert longest_increasing_subsequence([]) == []
    assert longest_increasing_subsequence([5, 5, 5]) == [5]
    rng = random.Random(1)
    for _ in range(200):
        seq = [rng.randint(0, 9) for _ in range(rng.randint(0, 10))]
        lis = longest_increasing_subsequence(seq)
        assert len(lis) == brute_lis_len(seq)
        assert is_strictly_increasing_subseq(lis, seq)


def naive_edit(a, b):
    if not a:
        return len(b)
    if not b:
        return len(a)
    return min(naive_edit(a[1:], b) + 1, naive_edit(a, b[1:]) + 1, naive_edit(a[1:], b[1:]) + (a[0] != b[0]))


def test_edit_distance():
    assert edit_distance("kitten", "sitting") == 3
    assert edit_distance("horse", "ros") == 3
    assert edit_distance("", "abc") == 3 and edit_distance("same", "same") == 0
    rng = random.Random(2)
    for _ in range(200):
        a = "".join(rng.choice("abc") for _ in range(rng.randint(0, 6)))
        b = "".join(rng.choice("abc") for _ in range(rng.randint(0, 6)))
        assert edit_distance(a, b) == naive_edit(a, b) == edit_distance(b, a)


def test_coin_change_min():
    assert coin_change_min_coins([1, 2, 5], 11) == 3
    assert coin_change_min_coins([2], 3) == -1
    assert coin_change_min_coins([1], 0) == 0
    # Greedy fails here (6 = 4+1+1), DP finds 3+3.
    assert coin_change_min_coins([1, 3, 4], 6) == 2


def brute_ways(coins, amount):
    if amount == 0:
        return 1
    if not coins or amount < 0:
        return 0
    return brute_ways(coins, amount - coins[0]) + brute_ways(coins[1:], amount)


def test_coin_change_ways():
    assert coin_change_ways([1, 2, 5], 5) == 4
    assert coin_change_ways([2], 3) == 0
    rng = random.Random(3)
    for _ in range(100):
        coins = sorted(set(rng.randint(1, 7) for _ in range(rng.randint(1, 4))))
        amt = rng.randint(0, 20)
        assert coin_change_ways(coins, amt) == brute_ways(coins, amt)
