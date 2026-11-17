"""Confined local filesystem access for filesystem resources.

The provider maps one logical Directory root to one existing physical directory.
It rejects path components, symbolic links and reparse-like entries instead of
following them. Operations are intentionally scoped below the configured root.
"""

from __future__ import annotations

import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from ..profile import PhysicalProfile
from ..exceptions import UnsupportedPlatformError
from .contract import ProviderCapabilities

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
        self._platform = "termux" if os.environ.get("TERMUX_VERSION") else sys.platform
        if self._platform not in {"linux", "termux", "win32"}:
            raise UnsupportedPlatformError(
                f"no filesystem provider is implemented for platform: {self._platform}"
            )
        self._resource_root = resource_root
        candidate = Path(root).expanduser()
        try:
            root_info = candidate.lstat()
        except FileNotFoundError:
            raise FileNotFoundError(candidate) from None
        if self._is_reparse_point(root_info) or not candidate.is_dir():
            raise NotADirectoryError(candidate)
        initial_identity = (root_info.st_dev, root_info.st_ino)
        self._root = candidate.resolve(strict=True)
        resolved_root_info = self._root.lstat()
        if self._is_reparse_point(resolved_root_info) or not stat.S_ISDIR(resolved_root_info.st_mode):
            raise NotADirectoryError(self._root)
        resolved_identity = (resolved_root_info.st_dev, resolved_root_info.st_ino)
        if resolved_identity != initial_identity:
            raise ValueError("configured filesystem root changed during provider initialization")
        # Retain the identity for path-based checks and verify it again after
        # opening the POSIX descriptor, closing the initialization race.
        self._root_identity = resolved_identity
        self._descriptor_mode = (
            os.name == "posix"
            and hasattr(os, "O_NOFOLLOW")
            and os.open in os.supports_dir_fd
            and os.stat in os.supports_dir_fd
        )
        self._root_fd: int | None = None
        if self._descriptor_mode:
            flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW
            descriptor = os.open(self._root, flags)
            try:
                opened_info = os.fstat(descriptor)
                opened_identity = (opened_info.st_dev, opened_info.st_ino)
                if opened_identity != self._root_identity:
                    raise ValueError("configured filesystem root changed before descriptor pinning")
            except BaseException:
                os.close(descriptor)
                raise
            self._root_fd = descriptor
        # Bind only after initialization succeeds; failed construction must not
        # leave a partially initialized provider attached to the resource tree.
        resource_root.bind_provider(self)

    @property
    def race_resistant(self) -> bool:
        """Whether physical operations are anchored to a POSIX directory descriptor."""
        return self._descriptor_mode

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Describe operations and metadata supported by this provider instance."""
        metadata_fields = {
            "exists", "entry_type", "size", "last_access_time",
            "last_modified_time", "permissions", "device_id", "inode",
            "link_count",
        }
        if hasattr(os.stat_result, "st_birthtime") or os.name == "nt":
            metadata_fields.add("creation_time")
        if hasattr(os.stat_result, "st_uid"):
            metadata_fields.add("owner_id")
        if hasattr(os.stat_result, "st_gid"):
            metadata_fields.add("group_id")
        if hasattr(os.stat_result, "st_flags"):
            metadata_fields.add("native_attributes")
        if hasattr(os.stat_result, "st_file_attributes"):
            metadata_fields.add("native_attributes")
        return ProviderCapabilities(
            platform=self._platform,
            filesystem=None,
            race_resistant=self.race_resistant,
            operations=frozenset({"create", "exists", "delete", "delete_tree", "purge", "profile", "access", "move", "copy_file", "create_exclusive"}),
            metadata_fields=frozenset(metadata_fields),
        )

    def close(self) -> None:
        """Release the provider's pinned root descriptor and unbind the root."""
        if self._root_fd is not None:
            os.close(self._root_fd)
            self._root_fd = None
        if getattr(self._resource_root, "_filesystem_provider", None) is self:
            del self._resource_root._filesystem_provider

    def __enter__(self) -> FilesystemProvider:
        if self._descriptor_mode and self._root_fd is None:
            raise RuntimeError("provider descriptor is closed")
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
            raise RuntimeError("provider descriptor is closed or unavailable")
        return self._open_parent_at(self._root_fd, tuple(relative.parts))

    def _open_directory_fd(self, relative: Path) -> int:
        """Open a directory beneath the pinned root and return its descriptor."""
        if self._root_fd is None:
            raise RuntimeError("provider descriptor is closed or unavailable")
        if not relative.parts:
            return os.dup(self._root_fd)
        parent_fd, name = self._open_parent_fd(relative)
        try:
            return os.open(
                name,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW,
                dir_fd=parent_fd,
            )
        finally:
            os.close(parent_fd)

    def _stat_relative(self, relative: Path) -> os.stat_result:
        if self._root_fd is None:
            raise RuntimeError("provider descriptor is closed or unavailable")
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
            raise RuntimeError("provider descriptor is closed or unavailable")
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
        if "/" in value or chr(0) in value:
            raise ValueError(f"resource name is not a valid path component: {value!r}")
        if os.name == "nt":
            if chr(92) in value or any(char in value for char in '<>:"|?*'):
                raise ValueError(f"resource name is not a valid Windows path component: {value!r}")
            if value.endswith((" ", ".")):
                raise ValueError("Windows resource names cannot end with a space or dot")
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

    def _validate_path_based_root(self) -> None:
        """Reject a replaced root or reparse point in its absolute path.

        This is a pre-operation path check, not a race-free Windows boundary:
        a hostile process can still mutate path components after validation.
        """
        components = [*reversed(self._root.parents), self._root]
        for component in components:
            try:
                info = component.lstat()
            except FileNotFoundError:
                raise FileNotFoundError(component) from None
            if self._is_reparse_point(info):
                raise ValueError(
                    f"configured filesystem root contains a symbolic link or reparse point: {component}"
                )
            if not stat.S_ISDIR(info.st_mode):
                raise NotADirectoryError(component)
            if component == self._root:
                # Windows may report st_ino == 0 when the filesystem cannot
                # provide a stable file index. In that case a replacement on
                # the same volume cannot be distinguished from the original
                # directory, so path-based operations must fail closed.
                if not info.st_ino or not self._root_identity[1]:
                    raise ValueError(
                        "configured filesystem root has no stable file identity; "
                        "refusing path-based operation"
                    )
                identity = (info.st_dev, info.st_ino)
                if identity != self._root_identity:
                    raise ValueError("configured filesystem root was replaced after provider construction")

    def resolve(self, resource: Directory | File, *, allow_missing: bool = True) -> Path:
        """Return a checked path for display and diagnostics, not for physical I/O.

        Path validation is inherently subject to TOCTOU races. Call create(),
        exists(), delete(), delete_tree() or purge() for physical operations.
        """
        if not self.race_resistant:
            self._validate_path_based_root()
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
        if not self.race_resistant:
            self.resolve(resource)
        target = self._root / relative
        if isinstance(resource, Directory):
            if self.race_resistant:
                if not relative.parts:
                    if self._root_fd is None:
                        raise RuntimeError("provider descriptor is closed")
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
        if not self.race_resistant:
            self.resolve(resource)
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
        for node in nodes:
            relative = self.relative_path(node)
            target = self._root / relative
            if not relative.parts:
                raise PermissionError("the provider root cannot be deleted")
            if self.race_resistant:
                try:
                    info = self._stat_relative(relative)
                except FileNotFoundError:
                    continue
                if self._is_reparse_point(info):
                    raise ValueError("recursive deletion refuses symbolic links and reparse points")
                if isinstance(node, Directory):
                    if not stat.S_ISDIR(info.st_mode):
                        raise NotADirectoryError(target)
                    expected = {
                        self.relative_path(child).name
                        for child in node.children
                    }
                    actual = self._listdir_relative(relative)
                    if actual != expected:
                        raise OSError(f"physical directory does not match modeled children: {target}")
                elif isinstance(node, File) and not stat.S_ISREG(info.st_mode):
                    raise IsADirectoryError(target)
            else:
                target = self.resolve(node)
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
        """Remove a modeled directory tree without following links.

        On POSIX, traversal and removal are anchored to open directory descriptors.
        The operation is confined against symlink substitution, but it is not an
        atomic transaction if another process concurrently renames entries.
        """
        relative = self.relative_path(directory)
        target = self._root / relative
        if not relative.parts:
            raise PermissionError("the provider root cannot be purged")

        if self.race_resistant:
            parent_fd, name = self._open_parent_fd(relative)
            target_fd = None
            opened: list[int] = []
            try:
                try:
                    info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                except FileNotFoundError:
                    return False
                if self._is_reparse_point(info) or not stat.S_ISDIR(info.st_mode):
                    raise NotADirectoryError(target)
                target_fd = os.open(
                    name,
                    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW,
                    dir_fd=parent_fd,
                )

                # Complete a no-follow preflight before removing anything.
                entries: list[tuple[tuple[str, ...], bool]] = []
                initial_fd = os.dup(target_fd)
                opened.append(initial_fd)
                stack: list[tuple[int, tuple[str, ...]]] = [(initial_fd, ())]
                while stack:
                    current_fd, prefix = stack.pop()
                    for child_name in os.listdir(current_fd):
                        child_info = os.stat(child_name, dir_fd=current_fd, follow_symlinks=False)
                        if self._is_reparse_point(child_info):
                            raise ValueError("purge refuses symbolic links and reparse points")
                        child_parts = prefix + (child_name,)
                        is_directory = stat.S_ISDIR(child_info.st_mode)
                        entries.append((child_parts, is_directory))
                        if is_directory:
                            child_fd = os.open(
                                child_name,
                                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW,
                                dir_fd=current_fd,
                            )
                            opened.append(child_fd)
                            stack.append((child_fd, child_parts))

                for child_parts, is_directory in sorted(entries, key=lambda item: len(item[0]), reverse=True):
                    child_parent_fd, child_name = self._open_parent_at(target_fd, child_parts)
                    try:
                        try:
                            child_info = os.stat(child_name, dir_fd=child_parent_fd, follow_symlinks=False)
                        except FileNotFoundError:
                            continue
                        if self._is_reparse_point(child_info):
                            raise ValueError("purge encountered a symbolic link or reparse point during removal")
                        if is_directory:
                            child_fd = os.open(
                                child_name,
                                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | os.O_NOFOLLOW,
                                dir_fd=child_parent_fd,
                            )
                            os.close(child_fd)
                            os.rmdir(child_name, dir_fd=child_parent_fd)
                        else:
                            os.unlink(child_name, dir_fd=child_parent_fd)
                    finally:
                        os.close(child_parent_fd)

                current_info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                pinned_info = os.fstat(target_fd)
                if (current_info.st_dev, current_info.st_ino) != (pinned_info.st_dev, pinned_info.st_ino):
                    raise OSError("purge target was replaced during removal")
                os.rmdir(name, dir_fd=parent_fd)
                return True
            finally:
                for descriptor in opened:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass
                if target_fd is not None:
                    os.close(target_fd)
                os.close(parent_fd)

        # Validate every existing ancestor before path-based filesystem I/O.
        self.resolve(directory)
        if not target.exists():
            return False
        if not target.is_dir() or target.is_symlink():
            raise NotADirectoryError(target)
        for current, dirs, files in os.walk(target, topdown=True, followlinks=False):
            for name in (*dirs, *files):
                item = Path(current) / name
                if self._is_reparse_point(item.lstat()):
                    raise ValueError(f"purge refuses symbolic links and reparse points: {item}")
        import shutil
        shutil.rmtree(target)
        return True


    def create_exclusive(self, resource: Directory) -> Path:
        """Create a new directory and fail if any physical entry already exists."""
        from ..core.directory import Directory

        if not isinstance(resource, Directory):
            raise TypeError("create_exclusive requires a Directory")
        relative = self.relative_path(resource)
        if not relative.parts:
            raise PermissionError("the provider root already exists")
        target = self._root / relative
        if self.race_resistant:
            parent_fd, name = self._open_parent_fd(relative)
            try:
                os.mkdir(name, dir_fd=parent_fd)
            finally:
                os.close(parent_fd)
        else:
            self.resolve(resource)
            target.mkdir(exist_ok=False)
        return target

    def move(self, resource: Directory | File, destination: Directory, new_name: str) -> Path:
        """Move/rename one modeled entry without replacing an existing target."""
        from ..core.directory import Directory
        from ..core.file import File

        if not isinstance(destination, Directory):
            raise TypeError("destination must be a Directory")
        if not isinstance(resource, (Directory, File)):
            raise TypeError("resource must be a Directory or File")
        if resource is self._resource_root:
            raise PermissionError("the provider root cannot be moved or renamed")
        old_relative = self.relative_path(resource)
        parent_relative = self.relative_path(destination)
        if isinstance(resource, File):
            target_component = self._segment(new_name + (("." + resource.extension) if resource.extension else ""))
        else:
            target_component = self._segment(new_name)
        new_relative = parent_relative / target_component
        if new_relative == old_relative:
            return self._root / new_relative
        if isinstance(resource, Directory) and old_relative in new_relative.parents:
            raise ValueError("a directory cannot be moved into itself or one of its descendants")
        if self.race_resistant:
            source_parent_fd, source_name = self._open_parent_fd(old_relative)
            destination_parent_fd = None
            try:
                destination_parent_fd = self._open_directory_fd(parent_relative)
                source_info = os.stat(source_name, dir_fd=source_parent_fd, follow_symlinks=False)
                if self._is_reparse_point(source_info):
                    raise ValueError("symbolic links and reparse points cannot be moved")
                if isinstance(resource, Directory) and not stat.S_ISDIR(source_info.st_mode):
                    raise NotADirectoryError(self._root / old_relative)
                if isinstance(resource, File) and not stat.S_ISREG(source_info.st_mode):
                    raise IsADirectoryError(self._root / old_relative)
                try:
                    os.stat(target_component, dir_fd=destination_parent_fd, follow_symlinks=False)
                except FileNotFoundError:
                    pass
                else:
                    raise FileExistsError(self._root / new_relative)
                os.rename(source_name, target_component, src_dir_fd=source_parent_fd, dst_dir_fd=destination_parent_fd)
            finally:
                if destination_parent_fd is not None:
                    os.close(destination_parent_fd)
                os.close(source_parent_fd)
        else:
            source = self.resolve(resource, allow_missing=False)
            destination_path = self.resolve(destination, allow_missing=False) / target_component
            if destination_path.exists() or destination_path.is_symlink():
                raise FileExistsError(destination_path)
            if isinstance(resource, Directory) and source in destination_path.parents:
                raise ValueError("a directory cannot be moved into itself or one of its descendants")
            os.rename(source, destination_path)
        return self._root / new_relative

    def copy_file(self, source: File, destination: Directory, new_name: str) -> Path:
        """Copy opaque file bytes into a new physical file; bytes are never returned."""
        from ..core.directory import Directory
        from ..core.file import File

        if not isinstance(source, File) or not isinstance(destination, Directory):
            raise TypeError("copy_file requires a File source and Directory destination")
        source_relative = self.relative_path(source)
        destination_relative = self.relative_path(destination)
        target_component = self._segment(new_name + (("." + source.extension) if source.extension else ""))
        target_relative = destination_relative / target_component
        if self.race_resistant:
            source_parent_fd, source_name = self._open_parent_fd(source_relative)
            destination_parent_fd = None
            source_fd = target_fd = None
            target_created = False
            try:
                destination_parent_fd = self._open_directory_fd(destination_relative)
                source_fd = os.open(source_name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=source_parent_fd)
                source_info = os.fstat(source_fd)
                if not stat.S_ISREG(source_info.st_mode):
                    raise ValueError("only regular files can be copied")
                target_fd = os.open(
                    target_component,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                    stat.S_IMODE(source_info.st_mode),
                    dir_fd=destination_parent_fd,
                )
                target_created = True
                while True:
                    chunk = os.read(source_fd, 1024 * 1024)
                    if not chunk:
                        break
                    view = memoryview(chunk)
                    while view:
                        written = os.write(target_fd, view)
                        view = view[written:]
            except BaseException:
                if target_fd is not None:
                    os.close(target_fd)
                    target_fd = None
                if target_created and destination_parent_fd is not None:
                    try:
                        os.unlink(target_component, dir_fd=destination_parent_fd)
                    except FileNotFoundError:
                        pass
                raise
            finally:
                if target_fd is not None:
                    os.close(target_fd)
                if source_fd is not None:
                    os.close(source_fd)
                if destination_parent_fd is not None:
                    os.close(destination_parent_fd)
                os.close(source_parent_fd)
        else:
            import shutil

            source_path = self.resolve(source, allow_missing=False)
            destination_path = self.resolve(destination, allow_missing=False) / target_component
            if destination_path.exists() or destination_path.is_symlink():
                raise FileExistsError(destination_path)
            info = source_path.lstat()
            if self._is_reparse_point(info) or not stat.S_ISREG(info.st_mode):
                raise ValueError("only regular files can be copied")
            try:
                with source_path.open("rb") as reader, destination_path.open("xb") as writer:
                    shutil.copyfileobj(reader, writer, length=1024 * 1024)
                os.chmod(destination_path, stat.S_IMODE(info.st_mode))
            except BaseException:
                try:
                    destination_path.unlink()
                except FileNotFoundError:
                    pass
                raise
        return self._root / target_relative

    def profile(self, resource: Directory | File) -> PhysicalProfile:
        """Observe physical metadata without opening or reading file contents.

        Missing entries produce an explicit exists=False snapshot. Other
        operating-system errors propagate unchanged. Symbolic links and
        reparse points are rejected rather than followed.
        """
        from ..core.directory import Directory
        from ..core.file import File

        if not isinstance(resource, (Directory, File)):
            raise TypeError("resource must be a Directory or File")
        relative = self.relative_path(resource)
        try:
            if self.race_resistant:
                info = self._stat_relative(relative)
            else:
                info = self.resolve(resource).lstat()
        except FileNotFoundError:
            return PhysicalProfile(exists=False, observed_at=datetime.now(timezone.utc))

        if self._is_reparse_point(info):
            raise ValueError("cannot profile a symbolic link or reparse point")
        if isinstance(resource, Directory) and not stat.S_ISDIR(info.st_mode):
            raise NotADirectoryError(self._root / relative)
        if isinstance(resource, File) and not stat.S_ISREG(info.st_mode):
            raise IsADirectoryError(self._root / relative)

        if stat.S_ISDIR(info.st_mode):
            entry_type = "directory"
        elif stat.S_ISREG(info.st_mode):
            entry_type = "file"
        else:
            raise ValueError("unsupported physical filesystem entry type")

        def timestamp(name: str):
            value = getattr(info, name, None)
            return datetime.fromtimestamp(value, timezone.utc) if value is not None else None

        native = tuple(
            (name, int(getattr(info, name)))
            for name in ("st_flags", "st_file_attributes")
            if getattr(info, name, None) is not None
        )
        return PhysicalProfile(
            exists=True,
            observed_at=datetime.now(timezone.utc),
            entry_type=entry_type,
            size=info.st_size,
            last_access_time=timestamp("st_atime"),
            last_modified_time=timestamp("st_mtime"),
            creation_time=timestamp("st_birthtime")
            or (timestamp("st_ctime") if os.name == "nt" else None),
            permissions=stat.S_IMODE(info.st_mode),
            owner_id=getattr(info, "st_uid", None),
            group_id=getattr(info, "st_gid", None),
            device_id=info.st_dev,
            inode=info.st_ino,
            link_count=info.st_nlink,
            native_attributes=native,
        )


    def access(self, resource: Directory | File, mode: int) -> bool:
        """Observe access for the current process identity using native OS checks.

        POSIX uses effective IDs when Python exposes that option. Other
        runtimes use native os.access semantics; on Windows this is not a
        complete NTFS ACL evaluator. This method cannot impersonate users or
        groups and does not guarantee that a later operation will succeed.
        """
        from ..core.directory import Directory
        from ..core.file import File

        if not isinstance(resource, (Directory, File)):
            raise TypeError("resource must be a Directory or File")
        if isinstance(mode, bool) or not isinstance(mode, int):
            raise TypeError("mode must be an integer access mask")
        allowed = os.R_OK | os.W_OK | os.X_OK | os.F_OK
        if mode < 0 or mode & ~allowed:
            raise ValueError("mode contains unsupported access flags")

        relative = self.relative_path(resource)
        try:
            info = self._stat_relative(relative) if self.race_resistant else self.resolve(
                resource, allow_missing=False
            ).lstat()
        except FileNotFoundError:
            return False
        if self._is_reparse_point(info):
            raise ValueError("access checks refuse symbolic links and reparse points")
        if isinstance(resource, Directory) and not stat.S_ISDIR(info.st_mode):
            raise NotADirectoryError(self._root / relative)
        if isinstance(resource, File) and not stat.S_ISREG(info.st_mode):
            raise IsADirectoryError(self._root / relative)

        kwargs = {}
        if os.name == "posix" and os.access in os.supports_effective_ids:
            kwargs["effective_ids"] = True

        if (
            self.race_resistant
            and os.access in os.supports_dir_fd
            and os.access in os.supports_follow_symlinks
        ):
            if relative.parts:
                parent_fd, name = self._open_parent_fd(relative)
                try:
                    return os.access(
                        name, mode, dir_fd=parent_fd,
                        follow_symlinks=False, **kwargs
                    )
                finally:
                    os.close(parent_fd)
            return os.access(
                ".", mode, dir_fd=self._root_fd,
                follow_symlinks=False, **kwargs
            )

        target = self._root / relative
        if not self.race_resistant:
            target = self.resolve(resource, allow_missing=False)
        return os.access(target, mode, **kwargs)
