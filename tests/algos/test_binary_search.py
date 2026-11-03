import bisect
import math
import random

from algorithms.binary_search import (
    binary_search, find_min_rotated, first_true, integer_sqrt, lower_bound, min_eating_speed,
    search_range, search_rotated, upper_bound,
)


def test_bounds_match_bisect():
    rng = random.Random(0)
    for _ in range(500):
        a = sorted(rng.randint(0, 10) for _ in range(rng.randint(0, 12)))
        x = rng.randint(-1, 11)
        assert lower_bound(a, x) == bisect.bisect_left(a, x)
        assert upper_bound(a, x) == bisect.bisect_right(a, x)
        i = binary_search(a, x)
        assert (i == -1 and x not in a) or (a[i] == x and a.index(x) == i)
        first, last = search_range(a, x)
        if x in a:
            assert (first, last) == (a.index(x), len(a) - 1 - a[::-1].index(x))
        else:
            assert (first, last) == (-1, -1)


def test_rotated_search_and_min():
    assert search_rotated([4, 5, 6, 7, 0, 1, 2], 0) == 4
    assert search_rotated([4, 5, 6, 7, 0, 1, 2], 3) == -1
    assert search_rotated([], 1) == -1
    rng = random.Random(1)
    for _ in range(300):
        base = sorted(rng.sample(range(50), rng.randint(1, 15)))
        k = rng.randrange(len(base))
        a = base[k:] + base[:k]
        assert find_min_rotated(a) == min(a)
        x = rng.randint(-1, 50)
        i = search_rotated(a, x)
        assert (i == -1 and x not in a) or a[i] == x


def test_first_true_and_isqrt():
    assert first_true(0, 100, lambda m: m >= 37) == 37
    assert first_true(0, 10, lambda m: False) == 11
    for n in list(range(200)) + [10**12, 10**12 - 1, 2**61]:
        assert integer_sqrt(n) == math.isqrt(n)


def test_min_eating_speed():
    assert min_eating_speed([3, 6, 7, 11], 8) == 4
    assert min_eating_speed([30, 11, 23, 4, 20], 5) == 30
    assert min_eating_speed([30, 11, 23, 4, 20], 6) == 23
