"""Physical directory discovery and model materialization."""
from __future__ import annotations
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from ..core.directory import Directory
from ..core.file import File
from ..factory import resource_from_path
from ..providers import FilesystemProviderProtocol, require_provider_operation


@dataclass(frozen=True, slots=True)
class ScanResult:
    """Immutable summary of one physical directory scan."""
    directory: Directory
    discovered: tuple[Directory | File, ...]
    skipped: tuple[tuple[str, str], ...]
    @property
    def count(self) -> int:
        return len(self.discovered)


def scan(directory: Directory, *, provider: FilesystemProviderProtocol,
         recursive: bool = True,
         excluded_names: set[str] | frozenset[str] = frozenset(),
         exclude: Callable[[str, bool], bool] | None = None,
         on_error: str = "raise",
         symlink_policy: str = "skip") -> ScanResult:
    """Discover descendants. Links are never followed.

    symlink_policy="skip" (default) records and ignores links/reparse points;
    "raise" aborts when one is encountered. Following descendant links is
    deliberately unavailable because it conflicts with the provider's
    logical-path mapping and root-confinement guarantees. A selected root
    link can be resolved explicitly with resource_from_path(...,
    follow_symlinks=True).
    """
    if not isinstance(directory, Directory):
        raise TypeError("directory must be a Directory")
    if not isinstance(recursive, bool):
        raise TypeError("recursive must be a bool")
    if on_error not in {"raise", "skip"}:
        raise ValueError("on_error must be 'raise' or 'skip'")
    if symlink_policy not in {"skip", "raise"}:
        raise ValueError("symlink_policy must be 'skip' or 'raise'")
    if not isinstance(excluded_names, (set, frozenset)) or any(
        not isinstance(name, str) or not name for name in excluded_names
    ):
        raise TypeError("excluded_names must be a set of non-empty strings")
    if exclude is not None and not callable(exclude):
        raise TypeError("exclude must be callable or None")
    exists = require_provider_operation(provider, "exists")
    if not exists(directory):
        raise FileNotFoundError(f"physical directory does not exist: {directory.path()}")
    resolve = getattr(provider, "resolve", None)
    if not callable(resolve):
        raise TypeError("provider must expose resolve(resource) for directory discovery")
    root_path = resolve(directory, allow_missing=False)
    discovered: list[Directory | File] = []
    skipped: list[tuple[str, str]] = []
    stack: list[tuple[Directory, Path]] = [(directory, Path(root_path))]
    while stack:
        current_model, current_path = stack.pop()
        try:
            with os.scandir(current_path) as iterator:
                entries = sorted(iterator, key=lambda entry: entry.name.casefold())
        except OSError as error:
            if on_error == "raise":
                raise
            skipped.append((str(current_path), str(error)))
            continue
        for entry in entries:
            try:
                info = entry.stat(follow_symlinks=False)
                attributes = getattr(info, "st_file_attributes", 0)
                reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
                if stat.S_ISLNK(info.st_mode) or attributes & reparse_flag:
                    reason = "symbolic link or reparse point"
                    if symlink_policy == "raise":
                        raise ValueError(f"{reason}: {entry.path}")
                    skipped.append((entry.path, reason))
                    continue
                is_directory = stat.S_ISDIR(info.st_mode)
                is_file = stat.S_ISREG(info.st_mode)
                if not (is_directory or is_file):
                    skipped.append((entry.path, "unsupported filesystem entry type"))
                    continue
                if entry.name in excluded_names or (
                    exclude is not None and exclude(entry.name, is_directory)
                ):
                    skipped.append((entry.path, "excluded by scan policy"))
                    continue
                existing = next(
                    (child for child in current_model.children
                     if (child.name if isinstance(child, Directory) else child.filename()) == entry.name),
                    None,
                )
                expected_type = Directory if is_directory else File
                if existing is not None:
                    if not isinstance(existing, expected_type):
                        raise TypeError(f"model/physical type conflict at {entry.path!r}")
                    resource = existing
                else:
                    resource = resource_from_path(entry.path, parent=current_model)
                    if not isinstance(resource, expected_type):
                        raise OSError(f"filesystem entry changed during scan: {entry.path}")
                    discovered.append(resource)
                if is_directory and recursive:
                    stack.append((resource, Path(entry.path)))
            except (OSError, ValueError, TypeError) as error:
                if isinstance(error, ValueError) and symlink_policy == "raise":
                    raise
                if on_error == "raise":
                    raise
                skipped.append((entry.path, str(error)))
    return ScanResult(directory=directory, discovered=tuple(discovered), skipped=tuple(skipped))


__all__ = ["ScanResult", "scan"]
