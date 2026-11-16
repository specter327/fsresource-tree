"""Ancestor traversal for filesystem resource hierarchies."""

from __future__ import annotations

from collections.abc import Iterator

from ..core.directory import Directory
from ..core.file import File


Resource = Directory | File


def ancestors(
    resource: Resource,
    include_self: bool = True,
    inverse: bool = False,
) -> Iterator[Resource]:
    """Yield the parent chain in root-to-resource order by default.

    Set include_self=False to start at the parent. Set inverse=True to yield
    from the resource toward its root.
    """
    if not isinstance(resource, (Directory, File)):
        raise TypeError("resource must be a Directory or File")
    if not isinstance(include_self, bool):
        raise TypeError("include_self must be a bool")
    if not isinstance(inverse, bool):
        raise TypeError("inverse must be a bool")

    if not include_self and resource.parent is not None:
        if not isinstance(resource.parent, Directory):
            raise TypeError("filesystem resource parents must be Directory instances")
        if sum(child is resource for child in resource.parent.children) != 1:
            raise ValueError("inconsistent parent/child relationship")

    chain: list[Resource] = []
    current = resource if include_self else resource.parent
    visited: set[int] = set()

    while current is not None:
        if not isinstance(current, (Directory, File)):
            raise TypeError("filesystem ancestors must be Directory or File resources")
        identity = id(current)
        if identity in visited:
            raise ValueError("cycle detected in filesystem parent chain")
        visited.add(identity)
        chain.append(current)

        parent = current.parent
        if parent is not None:
            if not isinstance(parent, Directory):
                raise TypeError("filesystem resource parents must be Directory instances")
            if sum(child is current for child in parent.children) != 1:
                raise ValueError("inconsistent parent/child relationship")
        current = parent

    if inverse:
        yield from chain
    else:
        yield from reversed(chain)
