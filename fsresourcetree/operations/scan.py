"""Physical directory discovery and model materialization."""
from __future__ import annotations
import os
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from ..core.directory import Directory
from ..core.file import File
from ..core.symbolic_link import SymbolicLink
from ..providers import FilesystemProviderProtocol, require_provider_operation


def _normalize_symlink_target(target: str, *, windows: bool | None = None) -> str:
    """Remove Win32 extended-length prefixes from ordinary drive and UNC paths.

    os.readlink may expose the \\\\?\\ namespace prefix on Windows. It is an
    API detail rather than part of the user-facing link target. Keep other
    device namespaces untouched because stripping their prefix changes meaning.
    """
    if windows is None:
        windows = os.name == "nt"
    if not windows:
        return target
    if target.startswith("\\\\?\\UNC\\"):
        return "\\\\" + target[8:]
    if (
        len(target) >= 7
        and target.startswith("\\\\?\\")
        and target[4].isalpha()
        and target[5:7] == ":\\"
    ):
        return target[4:]
    return target

class _SymlinkPolicyError(ValueError):
    """Raised when the configured symlink policy rejects an entry."""


@dataclass(frozen=True, slots=True)
class ScanResult:
    """Immutable summary of one physical directory scan."""
    directory: Directory
    discovered: tuple[Directory | File | SymbolicLink, ...]
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
    """Discover descendants through the configured filesystem provider.

    Physical enumeration is provider-owned: POSIX providers enumerate relative
    to pinned directory descriptors; path-based platforms retain their
    explicitly documented weaker race guarantees. Descendant links are never
    followed.
    """
    if not isinstance(directory, Directory):
        raise TypeError("directory must be a Directory")
    if not isinstance(recursive, bool):
        raise TypeError("recursive must be a bool")
    if on_error not in {"raise", "skip"}:
        raise ValueError("on_error must be 'raise' or 'skip'")
    if symlink_policy not in {"skip", "accept", "raise"}:
        raise ValueError("symlink_policy must be 'skip', 'accept' or 'raise'")
    if not isinstance(excluded_names, (set, frozenset)) or any(
        not isinstance(name, str) or not name for name in excluded_names
    ):
        raise TypeError("excluded_names must be a set of non-empty strings")
    if exclude is not None and not callable(exclude):
        raise TypeError("exclude must be callable or None")

    exists = require_provider_operation(provider, "exists")
    enumerate_entries = require_provider_operation(provider, "scan_entries")
    if not exists(directory):
        raise FileNotFoundError(f"physical directory does not exist: {directory.path()}")
    resolve = getattr(provider, "resolve", None)
    if not callable(resolve):
        raise TypeError("provider must expose resolve(resource) for diagnostics")

    discovered: list[Directory | File | SymbolicLink] = []
    skipped: list[tuple[str, str]] = []
    stack: list[Directory] = [directory]

    while stack:
        current_model = stack.pop()
        try:
            entries = enumerate_entries(current_model)
        except OSError as error:
            if on_error == "raise":
                raise
            skipped.append((str(current_model.path()), str(error)))
            continue

        current_path = resolve(current_model, allow_missing=False)
        for name, info, target in entries:
            entry_path = str(current_path / name)
            try:
                attributes = getattr(info, "st_file_attributes", 0)
                reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
                is_symlink = stat.S_ISLNK(info.st_mode)
                is_reparse_point = bool(attributes & reparse_flag)
                if is_symlink or is_reparse_point:
                    reason = "symbolic link or reparse point"
                    if symlink_policy == "raise":
                        raise _SymlinkPolicyError(f"{reason}: {entry_path}")
                    if symlink_policy == "accept" and is_symlink:
                        if target is None:
                            raise OSError(f"symbolic-link target unavailable: {entry_path}")
                        existing = next(
                            (child for child in current_model.children
                             if child.name == name),
                            None,
                        )
                        normalized_target = _normalize_symlink_target(target)
                        if existing is not None:
                            if not isinstance(existing, SymbolicLink) or existing.target != normalized_target:
                                raise TypeError(f"model/physical type conflict at {entry_path!r}")
                        else:
                            resource = SymbolicLink(
                                name=name,
                                target=normalized_target,
                                parent=current_model,
                            )
                            discovered.append(resource)
                        continue
                    skipped.append((entry_path, reason))
                    continue

                is_directory = stat.S_ISDIR(info.st_mode)
                is_file = stat.S_ISREG(info.st_mode)
                if not (is_directory or is_file):
                    skipped.append((entry_path, "unsupported filesystem entry type"))
                    continue
                if name in excluded_names or (
                    exclude is not None and exclude(name, is_directory)
                ):
                    skipped.append((entry_path, "excluded by scan policy"))
                    continue

                existing = next(
                    (child for child in current_model.children
                     if (child.name if isinstance(child, Directory) else child.filename()) == name),
                    None,
                )
                expected_type = Directory if is_directory else File
                if existing is not None:
                    if not isinstance(existing, expected_type):
                        raise TypeError(f"model/physical type conflict at {entry_path!r}")
                    resource = existing
                elif is_directory:
                    resource = Directory(name=name, parent=current_model)
                    discovered.append(resource)
                else:
                    suffix = Path(name).suffix
                    if suffix == ".":
                        resource = File(name=name, parent=current_model)
                    else:
                        base_name = name[:-len(suffix)] if suffix else name
                        resource = File(
                            name=base_name,
                            extension=suffix[1:] or None,
                            parent=current_model,
                        )
                    discovered.append(resource)

                if is_directory and recursive:
                    stack.append(resource)
            except (OSError, ValueError, TypeError) as error:
                if isinstance(error, _SymlinkPolicyError):
                    raise
                if on_error == "raise":
                    raise
                skipped.append((entry_path, str(error)))

    return ScanResult(
        directory=directory,
        discovered=tuple(discovered),
        skipped=tuple(skipped),
    )

__all__ = ["ScanResult", "scan"]
