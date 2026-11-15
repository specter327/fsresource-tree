"""Iterative traversal of filesystem resource hierarchies."""

from __future__ import annotations

from collections.abc import Iterator

from ..core.directory import Directory
from ..core.file import File


Resource = Directory | File


def walk(resource: Resource, inverse: bool = False) -> Iterator[Resource]:
    """Traverse a subtree iteratively; inverse=True yields post-order."""
    if not isinstance(resource, (Directory, File)):
        raise TypeError("resource must be a Directory or File")
    if not isinstance(inverse, bool):
        raise TypeError("inverse must be a bool")

    stack: list[tuple[Resource, bool]] = [(resource, False)]
    visited: set[int] = set()

    while stack:
        node, expanded = stack.pop()
        if expanded:
            yield node
            continue

        identity = id(node)
        if identity in visited:
            raise ValueError("cycle or duplicate reference in filesystem hierarchy")
        visited.add(identity)

        if inverse:
            stack.append((node, True))
        else:
            yield node

        if isinstance(node, Directory):
            children = node.children
            child_ids: set[int] = set()
            for child in children:
                if not isinstance(child, (Directory, File)):
                    raise TypeError("filesystem hierarchies can contain only Directory or File")
                if id(child) in child_ids:
                    raise ValueError("duplicate child reference in filesystem hierarchy")
                child_ids.add(id(child))
                if child.parent is not node:
                    raise ValueError("inconsistent parent/child relationship")
            stack.extend((child, False) for child in reversed(children))
