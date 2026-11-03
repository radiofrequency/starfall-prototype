"""Graph algorithms on adjacency-list graphs.

Graphs are ``dict[node, list[node]]`` (unweighted) or
``dict[node, list[tuple[node, weight]]]`` (weighted). Nodes that only appear
as neighbours are handled. V = number of nodes, E = number of edges.
"""

from __future__ import annotations

import heapq
from collections import deque
from typing import Hashable, Iterable, Mapping, Optional, Sequence

Node = Hashable


def _all_nodes(graph: Mapping) -> list:
    seen: dict = {}
    for u, nbrs in graph.items():
        seen.setdefault(u, None)
        for v in nbrs:
            seen.setdefault(v[0] if isinstance(v, tuple) else v, None)
    return list(seen)


def bfs(graph: Mapping[Node, Sequence[Node]], start: Node) -> list[Node]:
    """Breadth-first visit order from ``start``.

    Time O(V + E), space O(V).
    """
    order, seen, q = [], {start}, deque([start])
    while q:
        u = q.popleft()
        order.append(u)
        for v in graph.get(u, ()):
            if v not in seen:
                seen.add(v)
                q.append(v)
    return order


def shortest_path_unweighted(graph: Mapping[Node, Sequence[Node]], src: Node, dst: Node) -> Optional[list[Node]]:
    """Fewest-edges path from ``src`` to ``dst`` via BFS, or ``None`` if unreachable.

    Time O(V + E), space O(V).
    """
    parent: dict = {src: None}
    q = deque([src])
    while q:
        u = q.popleft()
        if u == dst:
            path = []
            while u is not None:
                path.append(u)
                u = parent[u]
            return path[::-1]
        for v in graph.get(u, ()):
            if v not in parent:
                parent[v] = u
                q.append(v)
    return None


def dfs(graph: Mapping[Node, Sequence[Node]], start: Node) -> list[Node]:
    """Depth-first preorder from ``start`` (iterative, so no recursion limit).

    Neighbours are visited in the order listed, matching the recursive version.
    Time O(V + E), space O(V).
    """
    order, seen, stack = [], set(), [start]
    while stack:
        u = stack.pop()
        if u in seen:
            continue
        seen.add(u)
        order.append(u)
        for v in reversed(list(graph.get(u, ()))):
            if v not in seen:
                stack.append(v)
    return order


def dijkstra(graph: Mapping[Node, Sequence[tuple[Node, float]]], src: Node) -> tuple[dict, dict]:
    """Single-source shortest paths with non-negative weights.

    Returns ``(dist, parent)``; unreachable nodes are absent from ``dist``.
    Uses a binary heap with lazy deletion. Time O((V + E) log V), space O(V + E).
    Raises ``ValueError`` on a negative edge weight.
    """
    dist = {src: 0}
    parent: dict = {src: None}
    heap = [(0, 0, src)]
    counter = 1          # tie-breaker so nodes never need to be comparable
    done = set()
    while heap:
        d, _, u = heapq.heappop(heap)
        if u in done:
            continue
        done.add(u)
        for v, w in graph.get(u, ()):
            if w < 0:
                raise ValueError("Dijkstra requires non-negative edge weights")
            nd = d + w
            if v not in dist or nd < dist[v]:
                dist[v] = nd
                parent[v] = u
                heapq.heappush(heap, (nd, counter, v))
                counter += 1
    return dist, parent


def reconstruct_path(parent: Mapping[Node, Optional[Node]], dst: Node) -> Optional[list[Node]]:
    """Walk a parent map back from ``dst``. O(path length)."""
    if dst not in parent:
        return None
    path = []
    while dst is not None:
        path.append(dst)
        dst = parent[dst]
    return path[::-1]


def topological_sort(graph: Mapping[Node, Sequence[Node]]) -> list[Node]:
    """Kahn's algorithm. Raises ``ValueError`` if the graph has a cycle.

    Edge ``u -> v`` means u must come before v. Time O(V + E), space O(V).
    """
    nodes = _all_nodes(graph)
    indeg = {n: 0 for n in nodes}
    for u in graph:
        for v in graph[u]:
            indeg[v] += 1
    q = deque(n for n in nodes if indeg[n] == 0)
    order = []
    while q:
        u = q.popleft()
        order.append(u)
        for v in graph.get(u, ()):
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    if len(order) != len(nodes):
        raise ValueError("graph has a cycle; no topological order exists")
    return order


def has_cycle_directed(graph: Mapping[Node, Sequence[Node]]) -> bool:
    """Cycle detection in a directed graph via three-colour iterative DFS. O(V + E)."""
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in _all_nodes(graph)}
    for root in color:
        if color[root] != WHITE:
            continue
        stack = [(root, iter(graph.get(root, ())))]
        color[root] = GREY
        while stack:
            u, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                color[u] = BLACK
                stack.pop()
            elif color[nxt] == GREY:
                return True
            elif color[nxt] == WHITE:
                color[nxt] = GREY
                stack.append((nxt, iter(graph.get(nxt, ()))))
    return False


class UnionFind:
    """Disjoint-set union with path compression and union by size.

    ``find`` and ``union`` run in amortised O(alpha(n)) (inverse Ackermann,
    effectively constant). Elements are added lazily on first use.
    """

    def __init__(self, items: Iterable[Node] = ()) -> None:
        self.parent: dict = {}
        self.size: dict = {}
        self.components = 0
        for x in items:
            self.add(x)

    def add(self, x: Node) -> None:
        if x not in self.parent:
            self.parent[x] = x
            self.size[x] = 1
            self.components += 1

    def find(self, x: Node) -> Node:
        self.add(x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:          # path compression
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: Node, b: Node) -> bool:
        """Merge the sets of ``a`` and ``b``; return False if already joined."""
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
        self.components -= 1
        return True

    def connected(self, a: Node, b: Node) -> bool:
        return self.find(a) == self.find(b)


def connected_components(graph: Mapping[Node, Sequence[Node]]) -> list[list[Node]]:
    """Connected components of an undirected graph (edges may be listed one way).

    Each component is sorted when nodes are comparable; components are ordered
    by first appearance. Time O(V + E), space O(V + E).
    """
    adj: dict = {n: [] for n in _all_nodes(graph)}
    for u, nbrs in graph.items():
        for v in nbrs:
            adj[u].append(v)
            adj[v].append(u)
    seen, out = set(), []
    for n in adj:
        if n in seen:
            continue
        comp, stack = [], [n]
        seen.add(n)
        while stack:
            u = stack.pop()
            comp.append(u)
            for v in adj[u]:
                if v not in seen:
                    seen.add(v)
                    stack.append(v)
        try:
            comp.sort()
        except TypeError:
            pass
        out.append(comp)
    return out


def number_of_islands(grid: Sequence[Sequence[str]]) -> int:
    """Count 4-connected groups of ``"1"`` cells. Time O(R*C), space O(R*C) worst case."""
    if not grid:
        return 0
    rows, cols = len(grid), len(grid[0])
    seen = [[False] * cols for _ in range(rows)]
    count = 0
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == "1" and not seen[r][c]:
                count += 1
                seen[r][c] = True
                q = deque([(r, c)])
                while q:
                    y, x = q.popleft()
                    for ny, nx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                        if 0 <= ny < rows and 0 <= nx < cols and grid[ny][nx] == "1" and not seen[ny][nx]:
                            seen[ny][nx] = True
                            q.append((ny, nx))
    return count
