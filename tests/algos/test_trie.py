import random

from algorithms.trie import Trie


def test_basic_operations():
    t = Trie(["apple", "app", "apt", "banana"])
    assert len(t) == 4
    assert "app" in t and t.search("apple") and not t.search("ap")
    assert t.starts_with("ap") and not t.starts_with("c")
    assert t.count_prefix("ap") == 3 and t.count_prefix("") == 4
    assert t.words_with_prefix("ap") == ["app", "apple", "apt"]
    assert t.words_with_prefix("ap", limit=2) == ["app", "apple"]
    assert t.words_with_prefix("zz") == []
    assert not t.insert("app")


def test_delete_keeps_other_words():
    t = Trie(["app", "apple"])
    assert t.delete("app")
    assert not t.search("app") and t.search("apple") and t.starts_with("app")
    assert t.delete("apple")
    assert not t.starts_with("a") and len(t) == 0
    assert not t.delete("apple")


def test_longest_common_prefix():
    assert Trie(["flower", "flow", "flight"]).longest_common_prefix() == "fl"
    assert Trie(["dog", "car"]).longest_common_prefix() == ""
    assert Trie(["inter", "internet"]).longest_common_prefix() == "inter"
    assert Trie().longest_common_prefix() == ""


def test_random_against_set():
    rng = random.Random(0)
    t, ref = Trie(), set()
    for _ in range(2000):
        w = "".join(rng.choice("abc") for _ in range(rng.randint(0, 4)))
        if rng.random() < 0.6:
            assert t.insert(w) == (w not in ref)
            ref.add(w)
        else:
            assert t.delete(w) == (w in ref)
            ref.discard(w)
        p = "".join(rng.choice("abc") for _ in range(rng.randint(0, 2)))
        expected = sorted(x for x in ref if x.startswith(p))
        assert t.words_with_prefix(p) == expected
        assert t.count_prefix(p) == len(expected)
        assert len(t) == len(ref)
