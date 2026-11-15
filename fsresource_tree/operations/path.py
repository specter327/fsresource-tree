"""Logical resource paths relative to a filesystem hierarchy root."""

from __future__ import annotations

from pathlib import PurePath

from ..core.directory import Directory
from ..core.file import File


def path(resource: Directory | File) -> PurePath:
    """Return the in-memory path below the top-level Directory.

    The top-level Directory represents PurePath('.'). No filesystem I/O is
    performed; use FilesystemProvider to resolve this path physically.
    """
    if not isinstance(resource, (Directory, File)):
        raise TypeError("resource must be a Directory or File")

    segments: list[str] = []
    current = resource
    visited: set[int] = set()

    while True:
        identity = id(current)
        if identity in visited:
            raise ValueError("cycle detected in filesystem parent chain")
        visited.add(identity)

        parent = current.parent
        if parent is None:
            if not isinstance(current, Directory):
                raise TypeError("filesystem resource hierarchy must have a Directory root")
            break

        if not isinstance(parent, Directory):
            raise TypeError("filesystem resources must descend from Directory roots")
        if sum(child is current for child in parent.children) != 1:
            raise ValueError("inconsistent parent/child relationship")

        segments.append(current.filename() if isinstance(current, File) else current.name)
        current = parent

    return PurePath(*reversed(segments))
