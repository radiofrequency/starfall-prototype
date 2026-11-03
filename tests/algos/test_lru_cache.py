import random
from collections import OrderedDict

import pytest

from algorithms.lru_cache import LRUCache


def test_classic_sequence():
    c = LRUCache(2)
    c.put(1, 1)
    c.put(2, 2)
    assert c.get(1) == 1
    assert c.put(3, 3) == 2          # evicts 2
    assert c.get(2) is None
    assert c.put(4, 4) == 1          # evicts 1
    assert c.get(1) is None and c.get(3) == 3 and c.get(4) == 4
    assert c.keys() == [4, 3]
    assert c.hits == 3 and c.misses == 2 and c.evictions == 2


def test_update_refreshes_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("a", 10)
    assert c.put("c", 3) == "b"
    assert c.get("a") == 10


def test_capacity_validation():
    with pytest.raises(ValueError):
        LRUCache(0)


def test_random_against_ordereddict():
    rng = random.Random(0)
    for cap in (1, 2, 5):
        c, ref = LRUCache(cap), OrderedDict()
        for _ in range(2000):
            k = rng.randint(0, 8)
            if rng.random() < 0.5:
                v = rng.random()
                c.put(k, v)
                ref[k] = v
                ref.move_to_end(k)
                if len(ref) > cap:
                    ref.popitem(last=False)
            else:
                expected = ref.get(k)
                if k in ref:
                    ref.move_to_end(k)
                assert c.get(k) == expected
            assert c.keys() == list(reversed(ref))
            assert len(c) == len(ref)
