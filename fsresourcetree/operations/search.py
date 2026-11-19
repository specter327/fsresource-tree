"""In-memory lookup and format-based search within filesystem subtrees."""
from __future__ import annotations
from ..core.directory import Directory
from ..core.file import File
from ..core.symbolic_link import SymbolicLink
from ..format_types import FormatTypes, extensions_for, normalize_extensions, normalize_formats
from .walker import walk

 _UNSET = object()\n\ndef find(resource: Directory | File | SymbolicLink, target=_UNSET, *, format: FormatTypes | tuple[FormatTypes, ...] | None = None, extensions=None):
    """Search a modeled subtree.

    With target, preserve the exact-name API and return the first match or None.
    With format and/or extensions, return matching Files in depth-first order.
    """
    if not isinstance(resource, (Directory, File, SymbolicLink)):
        raise TypeError("resource must be a Directory, File or SymbolicLink")
    if target is not None:
        if format is not None or extensions is not None:
            raise ValueError("target cannot be combined with format or extensions")
        if not isinstance(target, str):
            raise TypeError("target must be a string")
        for node in walk(resource):
            name = node.name if isinstance(node, (Directory, SymbolicLink)) else node.filename()
            if name == target:
                return node
        return None
    if format is None and extensions is None:
        raise ValueError("provide target, format or extensions")
    accepted = set()
    if format is not None:
        accepted.update(extensions_for(normalize_formats(format)))
    if extensions is not None:
        accepted.update(normalize_extensions(extensions))
    return [
        node for node in walk(resource)
        if isinstance(node, File) and node.extension is not None
        and ("." + node.extension.lstrip(".").lower()) in accepted
    ]

__all__ = ["find"]
