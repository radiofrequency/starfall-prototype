import itertools
import random

from algorithms.two_pointers import (
    container_with_most_water, is_palindrome, remove_duplicates_sorted, three_sum, trap_rain_water,
    two_sum_sorted,
)


def test_two_sum_sorted():
    assert two_sum_sorted([2, 7, 11, 15], 9) == (0, 1)
    assert two_sum_sorted([1, 2, 3], 7) is None
    rng = random.Random(0)
    for _ in range(300):
        a = sorted(rng.randint(-10, 10) for _ in range(rng.randint(0, 10)))
        t = rng.randint(-15, 15)
        res = two_sum_sorted(a, t)
        exists = any(a[i] + a[j] == t for i, j in itertools.combinations(range(len(a)), 2))
        assert (res is not None) == exists
        if res:
            i, j = res
            assert i < j and a[i] + a[j] == t


def test_three_sum():
    assert three_sum([-1, 0, 1, 2, -1, -4]) == [(-1, -1, 2), (-1, 0, 1)]
    assert three_sum([0, 0, 0, 0]) == [(0, 0, 0)]
    rng = random.Random(1)
    for _ in range(200):
        nums = [rng.randint(-6, 6) for _ in range(rng.randint(0, 10))]
        brute = sorted({tuple(sorted(c)) for c in itertools.combinations(nums, 3) if sum(c) == 0})
        assert three_sum(nums) == brute


def test_container_with_most_water():
    assert container_with_most_water([1, 8, 6, 2, 5, 4, 8, 3, 7]) == 49
    rng = random.Random(2)
    for _ in range(200):
        h = [rng.randint(0, 10) for _ in range(rng.randint(2, 12))]
        brute = max((j - i) * min(h[i], h[j]) for i, j in itertools.combinations(range(len(h)), 2))
        assert container_with_most_water(h) == brute


def test_trap_rain_water():
    assert trap_rain_water([0, 1, 0, 2, 1, 0, 1, 3, 2, 1, 2, 1]) == 6
    assert trap_rain_water([4, 2, 0, 3, 2, 5]) == 9
    rng = random.Random(3)
    for _ in range(300):
        h = [rng.randint(0, 6) for _ in range(rng.randint(0, 12))]
        brute = sum(max(0, min(max(h[:i + 1]), max(h[i:])) - h[i]) for i in range(len(h)))
        assert trap_rain_water(h) == brute


def test_remove_duplicates_and_palindrome():
    a = [0, 0, 1, 1, 1, 2, 2, 3, 3, 4]
    k = remove_duplicates_sorted(a)
    assert a[:k] == [0, 1, 2, 3, 4]
    assert remove_duplicates_sorted([]) == 0
    assert is_palindrome("A man, a plan, a canal: Panama")
    assert not is_palindrome("race a car")
    assert is_palindrome("")
