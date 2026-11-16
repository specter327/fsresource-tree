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

    def scan(
        self, *, provider: FilesystemProviderProtocol, recursive: bool = True,
        excluded_names: set[str] | frozenset[str] = frozenset(),
        exclude=None, on_error: str = "raise"
    ):
        from ..core.directory import Directory
        from ..operations.scan import scan
        if not isinstance(self, Directory):
            raise TypeError("scan is available only on Directory resources")
        return scan(
            self, provider=provider, recursive=recursive,
            excluded_names=excluded_names, exclude=exclude, on_error=on_error
        )

    def purge(self, *, provider: FilesystemProviderProtocol) -> bool:
        from ..core.directory import Directory
        from ..operations.delete import delete
        if not isinstance(self, Directory):
            raise TypeError("purge is available only on Directory resources")
        return delete(self, provider=provider, purge=True)


__all__ = ["FilesystemResourceOperations"]
