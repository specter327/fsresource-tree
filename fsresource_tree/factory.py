"""Filesystem path validation and resource materialization."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import TypeAlias

from .core.directory import Directory
from .core.file import File

FilesystemResourceType: TypeAlias = type[File] | type[Directory]


def validate_path(
    path: str | os.PathLike[str],
    *,
    expected_type: FilesystemResourceType | None = None,
) -> FilesystemResourceType:
    """Validate an existing entry and return its corresponding resource class.

    Symbolic links, Windows reparse points and special filesystem entries are
    rejected. Classification uses lstat, so links are never silently treated
    as their targets.
    """
    candidate = Path(path).expanduser()
    try:
        info = candidate.lstat()
    except FileNotFoundError:
        raise FileNotFoundError(candidate) from None

    # Windows symbolic links are also reparse points. Classify them first so
    # callers receive the specific symbolic-link error; other reparse points
    # (for example junctions) remain rejected by the broader check below.
    if stat.S_ISLNK(info.st_mode):
        raise ValueError(f"symbolic links are not filesystem resources: {candidate}")

    reparse_point_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    file_attributes = getattr(info, "st_file_attributes", 0)
    if file_attributes & reparse_point_flag:
        raise ValueError(f"filesystem reparse points are not resources: {candidate}")
    if stat.S_ISDIR(info.st_mode):
        resource_type: FilesystemResourceType = Directory
    elif stat.S_ISREG(info.st_mode):
        resource_type = File
    else:
        raise ValueError(f"unsupported filesystem entry type: {candidate}")

    if expected_type is not None:
        if expected_type not in (File, Directory):
            raise TypeError("expected_type must be File, Directory, or None")
        if resource_type is not expected_type:
            expected = "file" if expected_type is File else "directory"
            actual = "file" if resource_type is File else "directory"
            raise TypeError(f"expected a filesystem {expected}, found {actual}: {candidate}")

    return resource_type


def resource_from_path(
    path: str | os.PathLike[str],
    *,
    parent: Directory | None = None,
) -> File | Directory:
    """Materialize an existing path as its matching filesystem resource.

    The returned model contains no physical path. The path is used only to
    inspect the entry type and derive its logical name.
    """
    candidate = Path(path).expanduser()
    if candidate.name == "..":
        raise ValueError("paths ending in '..' cannot be materialized as filesystem resources")
    resource_type = validate_path(candidate)
    if not candidate.name:
        # Path('.') and Path() identify the current directory but have no
        # lexical basename. Resolve only this unnamed form, after lstat-based
        # classification, so ordinary named paths retain their supplied name.
        candidate = candidate.resolve(strict=True)
    if not candidate.name:
        raise ValueError("filesystem roots without a name cannot be materialized as resources")

    if parent is not None and not isinstance(parent, Directory):
        raise TypeError("parent must be a Directory or None")

    if resource_type is Directory:
        return Directory(name=candidate.name, parent=parent)

    suffix = candidate.suffix
    # pathlib treats a trailing dot as a suffix of ".". File.filename() cannot
    # represent that as an extension, so retain the complete basename instead.
    if suffix == ".":
        return File(name=candidate.name, parent=parent)
    name = candidate.name[:-len(suffix)] if suffix else candidate.name
    return File(name=name, extension=suffix[1:] or None, parent=parent)


__all__ = ["FilesystemResourceType", "resource_from_path", "validate_path"]
