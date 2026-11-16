"""Exact-name lookup within filesystem resource subtrees."""

from __future__ import annotations

from ..core.directory import Directory
from ..core.file import File
from .walker import walk


def find(resource: Directory | File, target: str) -> Directory | File | None:
    """Return the first top-down exact name match, or None."""
    if not isinstance(resource, (Directory, File)):
        raise TypeError("resource must be a Directory or File")
    if not isinstance(target, str):
        raise TypeError("target must be a string")

    for node in walk(resource):
        if node.name == target:
            return node
    return None
