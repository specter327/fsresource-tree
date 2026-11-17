"""Effective access observations for filesystem resources."""

from __future__ import annotations

import os

from ..core.directory import Directory
from ..core.file import File
from ..providers import FilesystemProviderProtocol, require_provider_operation


def _access(resource: Directory | File, mode: int, *, provider: FilesystemProviderProtocol) -> bool:
    if not isinstance(resource, (Directory, File)):
        raise TypeError("resource must be a Directory or File")
    check = require_provider_operation(provider, "access")
    return bool(check(resource, mode))


def readable(resource: Directory | File, *, provider: FilesystemProviderProtocol) -> bool:
    """Observe whether the current process can read the filesystem entry."""
    return _access(resource, os.R_OK, provider=provider)


def writable(resource: Directory | File, *, provider: FilesystemProviderProtocol) -> bool:
    """Observe whether the current process can modify the filesystem entry."""
    return _access(resource, os.W_OK, provider=provider)


def executable(resource: Directory | File, *, provider: FilesystemProviderProtocol) -> bool:
    """Observe execute (file) or search/traversal (directory) access."""
    return _access(resource, os.X_OK, provider=provider)


__all__ = ["executable", "readable", "writable"]
