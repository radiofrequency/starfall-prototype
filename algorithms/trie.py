"""Prefix tree (trie) for strings.

L = length of the word or prefix. Space is O(total characters stored).
"""

from __future__ import annotations

from typing import Iterator, Optional


class _Node:
    __slots__ = ("children", "terminal", "count")

    def __init__(self) -> None:
        self.children: dict[str, _Node] = {}
        self.terminal = False
        self.count = 0          # number of stored words passing through this node


class Trie:
    """Insert, exact search, prefix test, prefix count, autocomplete and delete."""

    def __init__(self, words: Optional[list[str]] = None) -> None:
        self._root = _Node()
        self._size = 0
        for w in words or ():
            self.insert(w)

    def __len__(self) -> int:
        return self._size

    def __contains__(self, word: str) -> bool:
        return self.search(word)

    def _walk(self, s: str) -> Optional[_Node]:
        node = self._root
        for ch in s:
            node = node.children.get(ch)
            if node is None:
                return None
        return node

    def insert(self, word: str) -> bool:
        """Add ``word``; return False if it was already present. O(L)."""
        if self.search(word):
            return False
        node = self._root
        node.count += 1
        for ch in word:
            node = node.children.setdefault(ch, _Node())
            node.count += 1
        node.terminal = True
        self._size += 1
        return True

    def search(self, word: str) -> bool:
        """Exact match. O(L)."""
        node = self._walk(word)
        return node is not None and node.terminal

    def starts_with(self, prefix: str) -> bool:
        """True if any stored word has this prefix. O(L)."""
        node = self._walk(prefix)
        return node is not None and node.count > 0

    def count_prefix(self, prefix: str) -> int:
        """How many stored words start with ``prefix``. O(L)."""
        node = self._walk(prefix)
        return node.count if node else 0

    def words_with_prefix(self, prefix: str, limit: Optional[int] = None) -> list[str]:
        """Stored words starting with ``prefix`` in lexicographic order.

        O(L + size of the output subtree).
        """
        node = self._walk(prefix)
        if node is None:
            return []
        out: list[str] = []
        for w in self._iter(node, prefix):
            out.append(w)
            if limit is not None and len(out) >= limit:
                break
        return out

    def _iter(self, node: _Node, prefix: str) -> Iterator[str]:
        stack = [(node, prefix)]
        while stack:
            n, p = stack.pop()
            if n.terminal:
                yield p
            for ch in sorted(n.children, reverse=True):
                stack.append((n.children[ch], p + ch))

    def delete(self, word: str) -> bool:
        """Remove ``word``; prunes empty branches. Return False if absent. O(L)."""
        if not self.search(word):
            return False
        node = self._root
        node.count -= 1
        for ch in word:
            child = node.children[ch]
            child.count -= 1
            if child.count == 0:
                del node.children[ch]
                self._size -= 1
                return True
            node = child
        node.terminal = False
        self._size -= 1
        return True

    def longest_common_prefix(self) -> str:
        """Longest prefix shared by every stored word. O(length of that prefix)."""
        if self._size == 0:
            return ""
        node, out = self._root, []
        while len(node.children) == 1 and not node.terminal:
            ch, node = next(iter(node.children.items()))
            out.append(ch)
        return "".join(out)
