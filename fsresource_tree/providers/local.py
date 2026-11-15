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

    def __init__(
        self,
        root: str | os.PathLike[str],
        *,
        resource_root: Directory,
    ) -> None:
        from ..core.directory import Directory

        if not isinstance(resource_root, Directory):
            raise TypeError("resource_root must be a Directory")
        self._resource_root = resource_root
        candidate = Path(root).expanduser()
        try:
            root_info = candidate.lstat()
        except FileNotFoundError:
            raise FileNotFoundError(candidate) from None
        if self._is_reparse_point(root_info) or not candidate.is_dir():
            raise NotADirectoryError(candidate)
        self._root = candidate.resolve(strict=True)
        self._root_fd: int | None = None
        if os.name == "posix" and hasattr(os, "O_NOFOLLOW") and os.open in os.supports_dir_fd:
            flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW
            self._root_fd = os.open(self._root, flags)

    @property
    def race_resistant(self) -> bool:
        """Whether physical operations are anchored to a POSIX directory descriptor."""
        return self._root_fd is not None

    def close(self) -> None:
        """Release the provider's pinned root directory descriptor."""
        if self._root_fd is not None:
            os.close(self._root_fd)
            self._root_fd = None

    def __enter__(self) -> FilesystemProvider:
        if self._root_fd is None and os.name == "posix":
            raise RuntimeError("provider descriptor is closed or secure descriptor operations are unavailable")
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()

    @staticmethod
    def _open_parent_at(root_fd: int, parts: tuple[str, ...]) -> tuple[int, str]:
        if not parts:
            raise ValueError("the provider root has no parent resource")
        flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW
        current = os.dup(root_fd)
        try:
            for part in parts[:-1]:
                next_fd = os.open(part, flags, dir_fd=current)
                os.close(current)
                current = next_fd
            return current, parts[-1]
        except BaseException:
            os.close(current)
            raise

    def _open_parent_fd(self, relative: Path) -> tuple[int, str]:
        if self._root_fd is None:
            raise RuntimeError("descriptor-relative operations are unavailable")
        return self._open_parent_at(self._root_fd, tuple(relative.parts))

    def _stat_relative(self, relative: Path) -> os.stat_result:
        if self._root_fd is None:
            raise RuntimeError("descriptor-relative operations are unavailable")
        if not relative.parts:
            return os.fstat(self._root_fd)
        parent_fd, name = self._open_parent_fd(relative)
        try:
            return os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        finally:
            os.close(parent_fd)

    def _exists_relative(self, relative: Path) -> bool:
        try:
            info = self._stat_relative(relative)
        except FileNotFoundError:
            return False
        if self._is_reparse_point(info):
            raise ValueError("symbolic links and reparse points are not traversable")
        return True

    def _listdir_relative(self, relative: Path) -> set[str]:
        if self._root_fd is None:
            raise RuntimeError("descriptor-relative operations are unavailable")
        if not relative.parts:
            directory_fd = os.dup(self._root_fd)
        else:
            parent_fd, name = self._open_parent_fd(relative)
            try:
                directory_fd = os.open(
                    name,
                    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW,
                    dir_fd=parent_fd,
                )
            finally:
                os.close(parent_fd)
        try:
            return set(os.listdir(directory_fd))
        finally:
            os.close(directory_fd)

    @staticmethod
    def _is_reparse_point(info: os.stat_result) -> bool:
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        attributes = getattr(info, "st_file_attributes", 0)
        return stat.S_ISLNK(info.st_mode) or bool(attributes & reparse_flag)

    @property
    def root(self) -> Path:
        return self._root

    @property
    def resource_root(self) -> Directory:
        return self._resource_root

    @staticmethod
    def _segment(value: str) -> str:
        if not isinstance(value, str) or not value or value in {".", ".."}:
            raise ValueError("resource names must be non-empty path components")
        if "/" in value or chr(92) in value or any(char in value for char in '<>:"|?*'):
            raise ValueError(f"resource name is not a portable path component: {value!r}")
        if chr(0) in value or value.endswith((" ", ".")):
            raise ValueError("resource names cannot contain NUL or end with a space or dot")
        device_name = value.split(".", 1)[0].upper()
        reserved = {"CON", "PRN", "AUX", "NUL"} | {
            f"{prefix}{index}" for prefix in ("COM", "LPT") for index in range(1, 10)
        }
        if device_name in reserved:
            raise ValueError(f"resource name is reserved on Windows: {value!r}")
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
        if current is not self._resource_root:
            raise ValueError("resource does not belong to this provider's logical root")
        for node in reversed(chain):
            name = node.filename() if isinstance(node, File) else node.name
            self._segment(name)
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
            if self._is_reparse_point(info):
                raise ValueError(f"symbolic links and reparse points are not traversable: {current}")
            if current != candidate and not stat.S_ISDIR(info.st_mode):
                raise NotADirectoryError(current)
        return candidate

    def exists(self, resource: Directory | File) -> bool:
        relative = self.relative_path(resource)
        if self.race_resistant:
            return self._exists_relative(relative)
        return self.resolve(resource).exists()

    def create(self, resource: Directory | File) -> Path:
        from ..core.directory import Directory
        from ..core.file import File

        relative = self.relative_path(resource)
        target = self._root / relative
        if isinstance(resource, Directory):
            if self.race_resistant:
                if not relative.parts:
                    if not stat.S_ISDIR(os.fstat(self._root_fd).st_mode):
                        raise NotADirectoryError(self._root)
                    return target
                parent_fd, name = self._open_parent_fd(relative)
                try:
                    try:
                        os.mkdir(name, dir_fd=parent_fd)
                    except FileExistsError:
                        pass
                    child_fd = os.open(
                        name,
                        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW,
                        dir_fd=parent_fd,
                    )
                    os.close(child_fd)
                finally:
                    os.close(parent_fd)
            else:
                target.mkdir(exist_ok=True)
                if target.is_symlink() or not target.is_dir():
                    raise NotADirectoryError(target)
        elif isinstance(resource, File):
            if self.race_resistant:
                parent_fd, name = self._open_parent_fd(relative)
                try:
                    try:
                        descriptor = os.open(
                            name,
                            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                            0o666,
                            dir_fd=parent_fd,
                        )
                    except FileExistsError:
                        info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                        if self._is_reparse_point(info) or not stat.S_ISREG(info.st_mode):
                            raise FileExistsError(target)
                    else:
                        os.close(descriptor)
                finally:
                    os.close(parent_fd)
            else:
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

        relative = self.relative_path(resource)
        target = self._root / relative
        if not relative.parts:
            raise PermissionError("the provider root cannot be deleted")
        if self.race_resistant:
            parent_fd, name = self._open_parent_fd(relative)
            try:
                try:
                    info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                except FileNotFoundError:
                    return False
                if self._is_reparse_point(info):
                    raise ValueError("refusing to delete a symbolic link or reparse point")
                if isinstance(resource, Directory):
                    if not stat.S_ISDIR(info.st_mode):
                        raise NotADirectoryError(target)
                    os.rmdir(name, dir_fd=parent_fd)
                elif isinstance(resource, File):
                    if not stat.S_ISREG(info.st_mode):
                        raise IsADirectoryError(target)
                    os.unlink(name, dir_fd=parent_fd)
                else:
                    raise TypeError("resource must be a Directory or File")
                return True
            finally:
                os.close(parent_fd)

        if not target.exists():
            return False
        if isinstance(resource, Directory):
            target.rmdir()
        elif isinstance(resource, File):
            target.unlink()
        else:
            raise TypeError("resource must be a Directory or File")
        return True

    def delete_tree(self, resource: Directory | File) -> bool:
        """Preflight a modeled subtree, then remove it bottom-up.

        Unknown physical entries cause a refusal before any modeled child is
        removed. This avoids partial deletion when the model is incomplete.
        """
        from ..core.directory import Directory
        from ..core.file import File
        from ..operations.walker import walk

        nodes = list(walk(resource, inverse=True))
        planned: dict[Path, Directory | File] = {}
        for node in nodes:
            target = self.resolve(node)
            if target == self._root:
                raise PermissionError("the provider root cannot be deleted")
            planned[target] = node

        for target, node in planned.items():
            if not target.exists():
                continue
            if isinstance(node, Directory):
                if not target.is_dir():
                    raise NotADirectoryError(target)
                expected = {
                    self.relative_path(child).name
                    for child in node.children
                }
                actual = {entry.name for entry in target.iterdir()}
                if actual != expected:
                    raise OSError(f"physical directory does not match modeled children: {target}")
            elif isinstance(node, File) and not target.is_file():
                raise IsADirectoryError(target)

        for node in nodes:
            self.delete(node)
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
                if self._is_reparse_point(item.lstat()):
                    raise ValueError(f"purge refuses symbolic links and reparse points: {item}")
        shutil.rmtree(target)
        return True
