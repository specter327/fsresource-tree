"""Filesystem specialization built on top of the generic resourcetree core."""

from . import operations, renderers
from .operations import ScanResult, copy, move, rename, scan
from resourcetree import Resource
from .core.directory import Directory
from .core.file import File
from .core.tree import FSResourceTree
from .factory import FilesystemResourceType, resource_from_path, validate_path
from .providers import FilesystemProvider, FilesystemProviderProtocol, ProviderCapabilities
from .profile import PhysicalProfile
from .exceptions import (
    InvalidParentError,
    ResourceAlreadyRegisteredError,
    UnsupportedOperationError,
    ProviderNotConfiguredError,
    UnsupportedPlatformError,
    ResourceNotFoundError,
    ResourceTreeError,
)

__version__ = "0.4.0"

__all__ = [
    "Resource",
    "File",
    "Directory",
    "FSResourceTree",
    "FilesystemProvider",
    "FilesystemProviderProtocol",
    "ProviderCapabilities",
    "PhysicalProfile",
    "FilesystemResourceType",
    "resource_from_path",
    "validate_path",
    "operations",
    "scan",
    "copy",
    "move",
    "rename",
    "ScanResult",
    "renderers",
    "ResourceTreeError",
    "ResourceNotFoundError",
    "ResourceAlreadyRegisteredError",
    "InvalidParentError",
    "UnsupportedOperationError",
    "ProviderNotConfiguredError",
    "UnsupportedPlatformError",
]
