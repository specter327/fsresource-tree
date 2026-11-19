"""Filesystem specialization built on top of the generic resourcetree core."""

from . import operations, renderers
from .operations import (
    FilesystemChangeEvent, FilesystemChangeType, PollingMonitor,
    ScanResult, copy, executable, move, readable, rename, scan, writable,
)
from resourcetree import Resource
from .core.directory import Directory
from .core.file import File
from .core.symbolic_link import SymbolicLink
from .core.tree import FSResourceTree
from .factory import FilesystemResourceType, resource_from_path, validate_path
from .providers import (
    FilesystemProvider, FilesystemProviderProtocol, ProviderCapabilities,
    LinuxProvider, TermuxProvider, WindowsProvider, ProviderLoader,
    detect_runtime_platform,
)
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
    "SymbolicLink",
    "Directory",
    "FSResourceTree",
    "FilesystemProvider",
    "LinuxProvider",
    "TermuxProvider",
    "WindowsProvider",
    "ProviderLoader",
    "detect_runtime_platform",
    "FilesystemProviderProtocol",
    "ProviderCapabilities",
    "PhysicalProfile",
    "FilesystemResourceType",
    "resource_from_path",
    "validate_path",
    "operations",
    "scan",
    "readable",
    "writable",
    "executable",
    "copy",
    "move",
    "rename",
    "ScanResult",
    "FilesystemChangeEvent",
    "FilesystemChangeType",
    "PollingMonitor",
    "renderers",
    "ResourceTreeError",
    "ResourceNotFoundError",
    "ResourceAlreadyRegisteredError",
    "InvalidParentError",
    "UnsupportedOperationError",
    "ProviderNotConfiguredError",
    "UnsupportedPlatformError",
]
