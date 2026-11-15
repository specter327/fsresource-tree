"""Logical resource paths relative to a filesystem provider root."""

from __future__ import annotations

from pathlib import PurePath

from ..core.directory import Directory
from ..core.file import File


def path(resource: Directory | File) -> PurePath:
    """Return the relative path below the hierarchy's top-level Directory.

    This function does not access the operating system. Use FilesystemProvider
    to resolve the returned logical path against a confined physical root.
    """
    if not isinstance(resource, (Directory, File)):
        raise TypeError("resource must be a Directory or File")
    segments: list[str] = []
    current = resource
    while current.parent is not None:
        segments.append(current.filename() if isinstance(current, File) else current.name)
        current = current.parent
        if not isinstance(current, Directory):
            raise TypeError("filesystem resources must descend from Directory roots")
    if not isinstance(current, Directory):
        raise TypeError("filesystem resource hierarchy must have a Directory root")
    return PurePath(*reversed(segments))
