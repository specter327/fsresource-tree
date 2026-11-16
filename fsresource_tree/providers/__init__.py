"""Filesystem provider contracts and implementations."""

from .contract import FilesystemProviderProtocol, ProviderCapabilities, require_provider_operation
from .local import FilesystemProvider

__all__ = [
    "FilesystemProvider",
    "FilesystemProviderProtocol",
    "ProviderCapabilities",
    "require_provider_operation",
]
