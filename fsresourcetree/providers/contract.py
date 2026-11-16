"""Structural contract and capability description for filesystem providers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ..exceptions import UnsupportedOperationError


@dataclass(frozen=True, slots=True)
class ProviderCapabilities:
    """Capabilities actually offered by one configured provider instance.

    platform identifies the Python runtime platform, not the filesystem
    format mounted at root. filesystem remains None unless a provider can
    identify that format reliably.
    """

    platform: str
    filesystem: str | None
    race_resistant: bool
    operations: frozenset[str]
    metadata_fields: frozenset[str]

    def __post_init__(self) -> None:
        if not isinstance(self.platform, str) or not self.platform:
            raise ValueError("platform must be a non-empty string")
        if self.filesystem is not None and not isinstance(self.filesystem, str):
            raise TypeError("filesystem must be a string or None")
        object.__setattr__(self, "operations", frozenset(self.operations))
        object.__setattr__(self, "metadata_fields", frozenset(self.metadata_fields))


@runtime_checkable
class FilesystemProviderProtocol(Protocol):
    """Structural interface consumed by filesystem operation services."""

    @property
    def capabilities(self) -> ProviderCapabilities: ...


def require_provider_operation(provider: FilesystemProviderProtocol, operation: str):
    """Validate and return one operation declared by a provider's capabilities."""
    if not isinstance(provider, FilesystemProviderProtocol):
        raise TypeError("provider must implement FilesystemProviderProtocol")
    capabilities = provider.capabilities
    if not isinstance(capabilities, ProviderCapabilities):
        raise TypeError("provider.capabilities must be ProviderCapabilities")
    if operation not in capabilities.operations:
        raise UnsupportedOperationError(
            f"filesystem provider does not support operation: {operation}"
        )
    method = getattr(provider, operation, None)
    if not callable(method):
        raise TypeError(
            f"provider declares {operation!r} but does not implement it"
        )
    return method


__all__ = [
    "FilesystemProviderProtocol",
    "ProviderCapabilities",
    "require_provider_operation",
]
