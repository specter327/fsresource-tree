"""Exceptions raised by fsresourcetree."""

from __future__ import annotations


class ResourceTreeError(Exception):
    """Base exception for filesystem resource errors."""


class ResourceNotFoundError(ResourceTreeError, KeyError):
    """No resource with the requested UID is registered."""


class ResourceAlreadyRegisteredError(ResourceTreeError, ValueError):
    """The resource is already registered in the tree."""


class InvalidParentError(ResourceTreeError, ValueError):
    """The supplied parent is not a valid or registered Directory."""


class UnsupportedOperationError(ResourceTreeError, NotImplementedError):
    """The selected provider does not support a requested filesystem operation."""


class ProviderNotConfiguredError(ResourceTreeError, RuntimeError):
    """The resource is not associated with a configured filesystem provider."""


class UnsupportedPlatformError(ResourceTreeError, OSError):
    """The current runtime platform has no supported filesystem provider."""


__all__ = [
    "ResourceTreeError",
    "ResourceNotFoundError",
    "ResourceAlreadyRegisteredError",
    "InvalidParentError",
    "UnsupportedOperationError",
    "ProviderNotConfiguredError",
    "UnsupportedPlatformError",
]
