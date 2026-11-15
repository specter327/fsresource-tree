"""Confined local filesystem access for filesystem resources.

The provider maps one logical Directory root to one existing physical directory.
It rejects path components, symbolic links and reparse-like entries instead of
following them. Operations are intentionally scoped below the configured root.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..core.directory import Directory
    from ..core.file import File


class FilesystemProvider:
    """Access resources beneath a single, pre-existing directory boundary."""

    def __init__(self, root: str | os.PathLike[str]) -> None:
        candidate = Path(root).expanduser()
        if not candidate.exists():
            raise FileNotFoundError(candidate)
        if candidate.is_symlink() or not candidate.is_dir():
            raise NotADirectoryError(candidate)
        self._root = candidate.resolve(strict=True)

    @property
    def root(self) -> Path:
        return self._root

    @staticmethod
    def _segment(value: str) -> str:
        if not isinstance(value, str) or not value or value in {".", ".."}:
            raise ValueError("resource names must be non-empty path components")
        if value in {os.sep, "/", "\\\\"} or os.sep in value or (os.altsep and os.altsep in value):
            raise ValueError(f"resource name is not a single path component: {value!r}")
        if "\\x00" in value:
            raise ValueError("resource names cannot contain NUL")
        return value

    def relative_path(self, resource: Directory | File) -> Path:
        from ..core.directory import Directory
        from ..core.file import File

        if not isinstance(resource, (Directory, File)):
            raise TypeError("resource must be a Directory or File")
        chain = []
        current = resource
        while current.parent is not None:
            chain.append(current)
            current = current.parent
            if not isinstance(current, Directory):
                raise TypeError("filesystem resources must descend from Directory roots")
        if not isinstance(current, Directory):
            raise TypeError("filesystem resource hierarchy must have a Directory root")
        for node in reversed(chain):
            name = node.filename() if isinstance(node, File) else node.name
            chain_name = self._segment(name)
            if isinstance(node, File) and node is not resource:
                raise ValueError("a File cannot contain child resources")
        # The top-level Directory represents the provider root itself.
        return Path(*(self._segment(n.filename() if isinstance(n, File) else n.name) for n in reversed(chain)))

    def resolve(self, resource: Directory | File, *, allow_missing: bool = True) -> Path:
        relative = self.relative_path(resource)
        candidate = self._root.joinpath(relative)
        try:
            candidate.relative_to(self._root)
        except ValueError as exc:
            raise ValueError("resource path escapes the configured filesystem root") from exc

        current = self._root
        for part in relative.parts:
            current = current / part
            try:
                info = current.lstat()
            except FileNotFoundError:
                if allow_missing:
                    continue
                raise
            if stat.S_ISLNK(info.st_mode):
                raise ValueError(f"symbolic links are not traversable: {current}")
            if current != candidate and not stat.S_ISDIR(info.st_mode):
                raise NotADirectoryError(current)
        return candidate

    def exists(self, resource: Directory | File) -> bool:
        target = self.resolve(resource)
        return target.exists()

    def create(self, resource: Directory | File) -> Path:
        from ..core.directory import Directory
        from ..core.file import File

        target = self.resolve(resource)
        if isinstance(resource, Directory):
            target.mkdir(exist_ok=True)
            if target.is_symlink() or not target.is_dir():
                raise NotADirectoryError(target)
        elif isinstance(resource, File):
            if target.exists():
                if target.is_symlink() or not target.is_file():
                    raise FileExistsError(target)
            else:
                with target.open("xb"):
                    pass
        else:
            raise TypeError("resource must be a Directory or File")
        return target

    def delete(self, resource: Directory | File) -> bool:
        from ..core.directory import Directory
        from ..core.file import File

        target = self.resolve(resource)
        if target == self._root:
            raise PermissionError("the provider root cannot be deleted")
        if not target.exists():
            return False
        if isinstance(resource, Directory):
            target.rmdir()
        elif isinstance(resource, File):
            target.unlink()
        else:
            raise TypeError("resource must be a Directory or File")
        return True

    def purge(self, directory: Directory) -> bool:
        """Remove a modeled directory and all physical descendants, without following links."""
        import shutil

        target = self.resolve(directory)
        if target == self._root:
            raise PermissionError("the provider root cannot be purged")
        if not target.exists():
            return False
        if not target.is_dir() or target.is_symlink():
            raise NotADirectoryError(target)
        # shutil.rmtree unlinks symlinks rather than traversing them. Reject them
        # explicitly so destructive operations never silently cross link boundaries.
        for current, dirs, files in os.walk(target, topdown=True, followlinks=False):
            for name in (*dirs, *files):
                item = Path(current) / name
                if item.is_symlink():
                    raise ValueError(f"purge refuses symbolic links: {item}")
        shutil.rmtree(target)
        return True
