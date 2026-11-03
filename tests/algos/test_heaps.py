import random
import statistics

import pytest

from algorithms.heaps import (
    ListNode, RunningMedian, kth_largest, merge_k_sorted, merge_k_sorted_linked, top_k_frequent,
    top_k_largest,
)


def test_top_k_largest_random():
    rng = random.Random(0)
    for _ in range(100):
        nums = [rng.randint(-50, 50) for _ in range(rng.randint(0, 30))]
        k = rng.randint(0, 35)
        assert top_k_largest(nums, k) == sorted(nums, reverse=True)[:k]


def test_kth_largest():
    assert kth_largest([3, 2, 1, 5, 6, 4], 2) == 5
    with pytest.raises(ValueError):
        kth_largest([1], 2)


def test_top_k_frequent():
    assert top_k_frequent([1, 1, 1, 2, 2, 3], 2) == [1, 2]
    assert top_k_frequent(list("abcabcab"), 3) == ["a", "b", "c"]
    assert top_k_frequent(list("xyz"), 2) == ["x", "y"]     # ties: first seen first


def test_merge_k_sorted_random():
    rng = random.Random(1)
    for _ in range(100):
        lists = [sorted(rng.randint(0, 30) for _ in range(rng.randint(0, 6))) for _ in range(rng.randint(0, 6))]
        flat = sorted(x for l in lists for x in l)
        assert merge_k_sorted(lists) == flat
        merged = merge_k_sorted_linked([ListNode.from_list(l) for l in lists])
        assert (merged.to_list() if merged else []) == flat


def test_running_median():
    rng = random.Random(2)
    rm, seen = RunningMedian(), []
    with pytest.raises(ValueError):
        rm.median()
    for _ in range(200):
        x = rng.randint(-100, 100)
        rm.add(x)
        seen.append(x)
        assert rm.median() == statistics.median(seen)
