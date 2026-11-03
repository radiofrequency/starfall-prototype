import random

from algorithms.intervals import (
    can_attend_all, insert_interval, interval_intersections, merge_intervals, min_meeting_rooms,
)


def covered(intervals):
    return {x for s, e in intervals for x in range(s, e + 1)}


def test_merge_examples():
    assert merge_intervals([(1, 3), (2, 6), (8, 10), (15, 18)]) == [(1, 6), (8, 10), (15, 18)]
    assert merge_intervals([(1, 4), (4, 5)]) == [(1, 5)]
    assert merge_intervals([]) == []


def test_merge_random_preserves_coverage_and_disjoint():
    rng = random.Random(0)
    for _ in range(200):
        ivs = []
        for _ in range(rng.randint(0, 8)):
            s = rng.randint(0, 30)
            ivs.append((s, s + rng.randint(0, 6)))
        m = merge_intervals(ivs)
        assert covered(m) == covered(ivs)
        assert all(m[i][1] < m[i + 1][0] for i in range(len(m) - 1))


def test_insert_interval():
    assert insert_interval([(1, 3), (6, 9)], (2, 5)) == [(1, 5), (6, 9)]
    assert insert_interval([(1, 2), (3, 5), (6, 7), (8, 10), (12, 16)], (4, 8)) == [(1, 2), (3, 10), (12, 16)]
    assert insert_interval([], (5, 7)) == [(5, 7)]
    rng = random.Random(1)
    for _ in range(200):
        base = merge_intervals([(s, s + rng.randint(0, 3)) for s in rng.sample(range(40), rng.randint(0, 6))])
        s = rng.randint(0, 40)
        new = (s, s + rng.randint(0, 8))
        assert insert_interval(base, new) == merge_intervals(base + [new])


def brute_rooms(meetings):
    points = {t for s, e in meetings for t in (s, e)}
    return max((sum(1 for s, e in meetings if s <= t < e) for t in points), default=0)


def test_meeting_rooms():
    assert min_meeting_rooms([(0, 30), (5, 10), (15, 20)]) == 2
    assert min_meeting_rooms([(7, 10), (2, 4)]) == 1
    assert min_meeting_rooms([(1, 5), (5, 10)]) == 1
    rng = random.Random(2)
    for _ in range(200):
        ms = [(s, s + rng.randint(1, 8)) for s in (rng.randint(0, 20) for _ in range(rng.randint(0, 8)))]
        assert min_meeting_rooms(ms) == brute_rooms(ms)
        assert can_attend_all(ms) == (brute_rooms(ms) <= 1)


def test_intersections():
    a = [(0, 2), (5, 10), (13, 23), (24, 25)]
    b = [(1, 5), (8, 12), (15, 24), (25, 26)]
    assert interval_intersections(a, b) == [(1, 2), (5, 5), (8, 10), (15, 23), (24, 24), (25, 25)]
