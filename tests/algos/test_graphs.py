import itertools
import random

import pytest

from algorithms.graphs import (
    UnionFind, bfs, connected_components, dfs, dijkstra, has_cycle_directed, number_of_islands,
    reconstruct_path, shortest_path_unweighted, topological_sort,
)

G = {"a": ["b", "c"], "b": ["d"], "c": ["d", "e"], "d": ["f"], "e": ["f"], "f": []}


def test_bfs_order_by_levels():
    assert bfs(G, "a") == ["a", "b", "c", "d", "e", "f"]


def test_dfs_preorder_matches_recursive():
    def rec(u, seen, out):
        seen.add(u)
        out.append(u)
        for v in G[u]:
            if v not in seen:
                rec(v, seen, out)
        return out
    assert dfs(G, "a") == rec("a", set(), []) == ["a", "b", "d", "f", "c", "e"]


def test_shortest_path_unweighted():
    assert shortest_path_unweighted(G, "a", "f") == ["a", "b", "d", "f"]
    assert shortest_path_unweighted(G, "f", "a") is None
    assert shortest_path_unweighted(G, "a", "a") == ["a"]


def bellman_ford(graph, src):
    nodes = set(graph) | {v for nbrs in graph.values() for v, _ in nbrs}
    dist = {n: float("inf") for n in nodes}
    dist[src] = 0
    for _ in range(len(nodes) - 1):
        for u in graph:
            for v, w in graph[u]:
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
    return {n: d for n, d in dist.items() if d != float("inf")}


def test_dijkstra_matches_bellman_ford_on_random_graphs():
    rng = random.Random(0)
    for _ in range(100):
        n = rng.randint(1, 12)
        g = {u: [(rng.randrange(n), rng.randint(0, 20)) for _ in range(rng.randint(0, 4))] for u in range(n)}
        dist, parent = dijkstra(g, 0)
        assert dist == bellman_ford(g, 0)
        for v in dist:                       # every reconstructed path has the claimed length
            path = reconstruct_path(parent, v)
            length = sum(min(w for x, w in g[a] if x == b) for a, b in zip(path, path[1:]))
            assert path[0] == 0 and path[-1] == v and length == dist[v]


def test_dijkstra_rejects_negative_weights():
    with pytest.raises(ValueError):
        dijkstra({0: [(1, -1)]}, 0)


def test_topological_sort_respects_edges():
    order = topological_sort(G)
    pos = {n: i for i, n in enumerate(order)}
    assert all(pos[u] < pos[v] for u in G for v in G[u])
    assert sorted(order) == sorted(pos)


def test_topological_sort_detects_cycle():
    with pytest.raises(ValueError):
        topological_sort({1: [2], 2: [3], 3: [1]})


def test_cycle_detection_random_against_topo():
    rng = random.Random(1)
    for _ in range(200):
        n = rng.randint(1, 8)
        g = {u: rng.sample(range(n), rng.randint(0, min(3, n))) for u in range(n)}
        try:
            topological_sort(g)
            acyclic = True
        except ValueError:
            acyclic = False
        assert has_cycle_directed(g) == (not acyclic)


def test_union_find():
    uf = UnionFind(range(6))
    assert uf.components == 6
    assert uf.union(0, 1) and uf.union(1, 2) and uf.union(3, 4)
    assert not uf.union(0, 2)
    assert uf.connected(0, 2) and not uf.connected(0, 3)
    assert uf.components == 3
    uf.union("x", "y")                  # lazily added elements
    assert uf.components == 4


def test_union_find_agrees_with_components():
    rng = random.Random(2)
    for _ in range(50):
        n = rng.randint(1, 15)
        edges = [(rng.randrange(n), rng.randrange(n)) for _ in range(rng.randint(0, n))]
        g = {u: [] for u in range(n)}
        uf = UnionFind(range(n))
        for a, b in edges:
            g[a].append(b)
            uf.union(a, b)
        comps = connected_components(g)
        assert len(comps) == uf.components
        for comp in comps:
            assert all(uf.connected(comp[0], x) for x in comp)
        assert sorted(itertools.chain.from_iterable(comps)) == list(range(n))


def test_connected_components_example():
    assert connected_components({1: [2], 3: [4], 5: []}) == [[1, 2], [3, 4], [5]]


def test_number_of_islands():
    grid = ["11000", "11000", "00100", "00011"]
    assert number_of_islands(grid) == 3
    assert number_of_islands([]) == 0
    assert number_of_islands(["0"]) == 0
