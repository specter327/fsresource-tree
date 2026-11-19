"""Filesystem path validation and resource materialization."""

from __future__ import annotations
import os
import stat
from pathlib import Path
from typing import TypeAlias
from .core.directory import Directory
from .core.file import File

FilesystemResourceType: TypeAlias = type[File] | type[Directory]


def validate_path(path: str | os.PathLike[str], *,
                  expected_type: FilesystemResourceType | None = None,
                  follow_symlinks: bool = False) -> FilesystemResourceType:
    """Validate an entry; links are rejected unless explicitly followed."""
    if not isinstance(follow_symlinks, bool):
        raise TypeError("follow_symlinks must be a bool")
    candidate = Path(path).expanduser()
    try:
        info = candidate.stat() if follow_symlinks else candidate.lstat()
    except FileNotFoundError:
        raise FileNotFoundError(candidate) from None
    if not follow_symlinks and stat.S_ISLNK(info.st_mode):
        raise ValueError(f"symbolic links are not filesystem resources: {candidate}")
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    if getattr(info, "st_file_attributes", 0) & reparse_flag:
        raise ValueError(f"filesystem reparse points are not resources: {candidate}")
    if stat.S_ISDIR(info.st_mode):
        resource_type = Directory
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


def resource_from_path(path: str | os.PathLike[str], *,
                       parent: Directory | None = None,
                       follow_symlinks: bool = False) -> File | Directory:
    """Materialize a path; following a supplied root link is explicit opt-in.

    When enabled, the target's canonical path becomes the resource/provider
    root. Descendant links remain governed independently by Directory.scan().
    """
    if not isinstance(follow_symlinks, bool):
        raise TypeError("follow_symlinks must be a bool")
    if follow_symlinks and parent is not None:
        raise ValueError("follow_symlinks is only supported for an explicitly selected root resource")
    candidate = Path(path).expanduser()
    if candidate.name == "..":
        raise ValueError("paths ending in '..' cannot be materialized as filesystem resources")
    if follow_symlinks:
        candidate = candidate.resolve(strict=True)
    resource_type = validate_path(candidate)
    if not candidate.name:
        candidate = candidate.resolve(strict=True)
    if not candidate.name:
        raise ValueError("filesystem roots without a name cannot be materialized as resources")
    if parent is not None and not isinstance(parent, Directory):
        raise TypeError("parent must be a Directory or None")
    if resource_type is Directory:
        resource = Directory(name=candidate.name, parent=parent)
        if parent is None:
            from .providers import ProviderLoader
            ProviderLoader.load(candidate, resource_root=resource)
        return resource
    suffix = candidate.suffix
    if suffix == ".":
        return File(name=candidate.name, parent=parent)
    name = candidate.name[:-len(suffix)] if suffix else candidate.name
    return File(name=name, extension=suffix[1:] or None, parent=parent)


__all__ = ["FilesystemResourceType", "resource_from_path", "validate_path"]
