"""Convenience facade for physical filesystem operations on resources.

Physical side effects are delegated to the operations layer and require an
explicit provider. This module contains no filesystem I/O.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..providers import FilesystemProviderProtocol
    from .directory import Directory


class FilesystemResourceOperations:
    """Expose provider-backed operations as resource instance methods."""

    def create(self, *, provider: FilesystemProviderProtocol, recursive_children: bool = False) -> bool:
        from ..operations.create import create
        return create(self, provider=provider, recursive_children=recursive_children)

    def delete(
        self, *, provider: FilesystemProviderProtocol,
        recursive_children: bool = False, purge: bool = False
    ) -> bool:
        from ..operations.delete import delete
        return delete(self, provider=provider, recursive_children=recursive_children, purge=purge)

    def exists(self, *, provider: FilesystemProviderProtocol) -> bool:
        from ..operations.exists import exists
        return exists(self, provider=provider)

    def readable(self, *, provider: FilesystemProviderProtocol) -> bool:
        from ..operations.access import readable
        return readable(self, provider=provider)

    def writable(self, *, provider: FilesystemProviderProtocol) -> bool:
        from ..operations.access import writable
        return writable(self, provider=provider)

    def executable(self, *, provider: FilesystemProviderProtocol) -> bool:
        from ..operations.access import executable
        return executable(self, provider=provider)

    def is_readable(self, *, provider: FilesystemProviderProtocol) -> bool:
        """Check read access for the provider's supported effective identity."""
        from ..operations.access import readable
        return readable(self, provider=provider)

    def is_writable(self, *, provider: FilesystemProviderProtocol) -> bool:
        """Check write access for the provider's supported effective identity."""
        from ..operations.access import writable
        return writable(self, provider=provider)

    def is_executable(self, *, provider: FilesystemProviderProtocol) -> bool:
        """Check execute/search access for the provider's supported effective identity."""
        from ..operations.access import executable
        return executable(self, provider=provider)

    def rename(self, new_name: str, *, provider: FilesystemProviderProtocol):
        from ..operations.relocate import rename
        return rename(self, new_name, provider=provider)

    def move(
        self, destination: Directory, *, provider: FilesystemProviderProtocol,
        new_name: str | None = None
    ):
        from ..operations.relocate import move
        return move(self, destination, provider=provider, new_name=new_name)

    def copy(
        self, destination: Directory, *, provider: FilesystemProviderProtocol,
        new_name: str | None = None
    ):
        from ..operations.relocate import copy
        return copy(self, destination, provider=provider, new_name=new_name)

__all__ = ["FilesystemResourceOperations"]
