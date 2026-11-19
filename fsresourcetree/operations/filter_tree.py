"""Create a non-destructive, hierarchy-preserving filtered model view."""
from __future__ import annotations
from ..core.directory import Directory
from ..core.file import File
from ..format_types import FormatTypes, extensions_for, normalize_extensions, normalize_formats
from .walker import walk

def filter_tree(directory: Directory, *, format: FormatTypes | tuple[FormatTypes, ...] | None = None, extensions=None) -> Directory:
    """Return a detached hierarchy containing matching files.

    Directories are retained only when they contain a match; the requested
    root is always retained. The source model is never modified. Symbolic
    links are omitted because they are not regular files.
    """
    if not isinstance(directory, Directory):
        raise TypeError("directory must be a Directory")
    if format is None and extensions is None:
        raise ValueError("provide format or extensions")
    accepted = set()
    if format is not None:
        accepted.update(extensions_for(normalize_formats(format)))
    if extensions is not None:
        accepted.update(normalize_extensions(extensions))
    result = Directory(directory.name, metadata=dict(directory.metadata))
    clones = {id(directory): result}
    for node in walk(directory):
        if node is directory:
            continue
        if isinstance(node, Directory):
            parent_clone = clones.get(id(node.parent))
            if parent_clone is not None:
                clones[id(node)] = Directory(node.name, parent=parent_clone, metadata=dict(node.metadata))
        elif isinstance(node, File) and node.extension is not None:
            suffix = "." + node.extension.lstrip(".").lower()
            if suffix in accepted:
                parent_clone = clones.get(id(node.parent))
                if parent_clone is not None:
                    File(node.name, extension=node.extension, parent=parent_clone, metadata=dict(node.metadata))
    for node in list(walk(result, inverse=True)):
        if isinstance(node, Directory) and node is not result and not node.children:
            node.parent.remove_child(node)
    return result

__all__ = ["filter_tree"]
