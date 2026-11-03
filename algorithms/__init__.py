"""Classic algorithm and data-structure problems, with tested reference solutions.

Each function documents its time and space complexity. Standard library only.

Modules:
    graphs          BFS, DFS, Dijkstra, topological sort, union-find, connected components
    dynamic         0/1 knapsack, longest increasing subsequence, edit distance, coin change
    heaps           top-k, k-th largest, merge k sorted lists, running median
    trie            prefix tree with insert/search/prefix/autocomplete/delete
    intervals       merge, insert, minimum meeting rooms
    binary_search   lower/upper bound, rotated array search, search on the answer
    sliding_window  longest substring without repeats, minimum window substring, max sliding window
    two_pointers    two-sum (sorted), three-sum, container with most water, trapping rain water
    lru_cache       O(1) LRU cache built on a hash map + doubly linked list
"""

__all__ = [
    "graphs", "dynamic", "heaps", "trie", "intervals", "binary_search",
    "sliding_window", "two_pointers", "lru_cache",
]
