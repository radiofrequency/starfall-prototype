import random

import pytest

from algorithms.sliding_window import (
    longest_substring_without_repeats, max_sliding_window, max_sum_subarray_of_size_k,
    min_subarray_len, min_window_substring,
)
from collections import Counter


def test_longest_substring_without_repeats():
    assert longest_substring_without_repeats("abcabcbb") == 3
    assert longest_substring_without_repeats("bbbbb") == 1
    assert longest_substring_without_repeats("pwwkew") == 3
    assert longest_substring_without_repeats("") == 0
    rng = random.Random(0)
    for _ in range(300):
        s = "".join(rng.choice("abcd") for _ in range(rng.randint(0, 12)))
        brute = max((j - i for i in range(len(s)) for j in range(i + 1, len(s) + 1)
                     if len(set(s[i:j])) == j - i), default=0)
        assert longest_substring_without_repeats(s) == brute


def brute_min_window(s, t):
    need = Counter(t)
    best = ""
    for i in range(len(s)):
        for j in range(i + 1, len(s) + 1):
            if not need - Counter(s[i:j]) and (not best or j - i < len(best)):
                best = s[i:j]
    return best


def test_min_window_substring():
    assert min_window_substring("ADOBECODEBANC", "ABC") == "BANC"
    assert min_window_substring("a", "aa") == ""
    rng = random.Random(1)
    for _ in range(300):
        s = "".join(rng.choice("abc") for _ in range(rng.randint(0, 10)))
        t = "".join(rng.choice("abc") for _ in range(rng.randint(1, 3)))
        got = min_window_substring(s, t)
        want = brute_min_window(s, t)
        assert len(got) == len(want)
        assert not got or not Counter(t) - Counter(got)


def test_max_sliding_window():
    assert max_sliding_window([1, 3, -1, -3, 5, 3, 6, 7], 3) == [3, 3, 5, 5, 6, 7]
    rng = random.Random(2)
    for _ in range(300):
        nums = [rng.randint(-10, 10) for _ in range(rng.randint(1, 15))]
        k = rng.randint(1, len(nums))
        assert max_sliding_window(nums, k) == [max(nums[i:i + k]) for i in range(len(nums) - k + 1)]
    with pytest.raises(ValueError):
        max_sliding_window([1], 0)


def test_min_subarray_len():
    assert min_subarray_len(7, [2, 3, 1, 2, 4, 3]) == 2
    assert min_subarray_len(100, [1, 2, 3]) == 0
    rng = random.Random(3)
    for _ in range(300):
        nums = [rng.randint(1, 9) for _ in range(rng.randint(0, 10))]
        target = rng.randint(1, 30)
        brute = min((j - i for i in range(len(nums)) for j in range(i + 1, len(nums) + 1)
                     if sum(nums[i:j]) >= target), default=0)
        assert min_subarray_len(target, nums) == brute


def test_max_sum_subarray_of_size_k():
    assert max_sum_subarray_of_size_k([2, 1, 5, 1, 3, 2], 3) == 9
    assert max_sum_subarray_of_size_k([-3, -1, -2], 1) == -1
