"""Provider-resolved convenience operations for filesystem resources.

A resource resolves its provider from itself or its nearest ancestor. The
provider is bound to a physical Directory root; callers do not pass it to
every operation. This module contains no filesystem I/O.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from ..exceptions import ProviderNotConfiguredError

if TYPE_CHECKING:
    from ..providers import FilesystemProviderProtocol
    from .directory import Directory


class FilesystemResourceOperations:
    """Expose provider-backed operations as resource instance methods."""

    def bind_provider(self, provider: FilesystemProviderProtocol):
        """Bind a provider to this Directory root and return the resource."""
        from ..providers import FilesystemProviderProtocol
        from .directory import Directory

        if not isinstance(self, Directory):
            raise TypeError("a filesystem provider can only be bound to a Directory")
        if not isinstance(provider, FilesystemProviderProtocol):
            raise TypeError("provider must implement FilesystemProviderProtocol")
        current = getattr(self, "_filesystem_provider", None)
        if current is not None and current is not provider:
            raise RuntimeError("this Directory already has a different filesystem provider")
        self._filesystem_provider = provider
        return self

    @property
    def filesystem_provider(self):
        """Return the provider bound to this resource or its nearest ancestor."""
        current = self
        while current is not None:
            provider = getattr(current, "_filesystem_provider", None)
            if provider is not None:
                return provider
            current = current.parent
        return None

    def close_provider(self) -> None:
        """Close and unbind the provider associated with this resource."""
        provider = self.filesystem_provider
        if provider is None:
            raise ProviderNotConfiguredError("resource has no configured filesystem provider")
        provider.close()

    def _require_provider(self):
        provider = self.filesystem_provider
        if provider is None:
            raise ProviderNotConfiguredError(
                f"{type(self).__name__} is not associated with a physical filesystem root; "
                "materialize a Directory with resource_from_path() or bind a provider "
                "to its Directory root"
            )
        return provider

    def create(self, *, recursive_children: bool = False) -> bool:
        from ..operations.create import create
        return create(self, provider=self._require_provider(), recursive_children=recursive_children)

    def delete(self, *, recursive_children: bool = False, purge: bool = False) -> bool:
        from ..operations.delete import delete
        return delete(self, provider=self._require_provider(), recursive_children=recursive_children, purge=purge)

    def exists(self) -> bool:
        from ..operations.exists import exists
        return exists(self, provider=self._require_provider())

    def rename(self, new_name: str):
        from ..operations.relocate import rename
        return rename(self, new_name, provider=self._require_provider())

    def move(self, destination: Directory, *, new_name: str | None = None):
        from ..operations.relocate import move
        if self.filesystem_provider is not destination.filesystem_provider:
            raise ValueError("source and destination must share the same filesystem provider")
        return move(self, destination, provider=self._require_provider(), new_name=new_name)

    def copy(self, destination: Directory, *, new_name: str | None = None):
        from ..operations.relocate import copy
        if self.filesystem_provider is not destination.filesystem_provider:
            raise ValueError("source and destination must share the same filesystem provider")
        return copy(self, destination, provider=self._require_provider(), new_name=new_name)


__all__ = ["FilesystemResourceOperations"]
