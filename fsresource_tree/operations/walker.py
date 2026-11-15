"""Iterative traversal of filesystem resource hierarchies."""

from __future__ import annotations

from collections.abc import Iterator

from ..core.directory import Directory
from ..core.file import File


def walk(resource: Directory | File, inverse: bool = False) -> Iterator[Directory | File]:
    """Traverse without Python recursion; inverse=True yields post-order."""
    if not isinstance(resource, (Directory, File)):
        raise TypeError("resource must be a Directory or File")
    stack: list[tuple[Directory | File, bool]] = [(resource, False)]
    visited: set[int] = set()
    while stack:
        node, expanded = stack.pop()
        identity = id(node)
        if expanded:
            yield node
            continue
        if identity in visited:
            raise ValueError("cycle or duplicate reference in filesystem hierarchy")
        visited.add(identity)
        if inverse:
            stack.append((node, True))
            if isinstance(node, Directory):
                stack.extend((child, False) for child in reversed(node.children))
        else:
            yield node
            if isinstance(node, Directory):
                stack.extend((child, False) for child in reversed(node.children))
