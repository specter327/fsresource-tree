"""Filesystem provider contracts, runtime implementations and loader."""

from .contract import FilesystemProviderProtocol, ProviderCapabilities, require_provider_operation
from .local import FilesystemProvider
from .platforms import LinuxProvider, TermuxProvider, WindowsProvider, detect_runtime_platform
from .loader import ProviderLoader

__all__ = [
    "FilesystemProvider",
    "LinuxProvider",
    "TermuxProvider",
    "WindowsProvider",
    "ProviderLoader",
    "detect_runtime_platform",
    "FilesystemProviderProtocol",
    "ProviderCapabilities",
    "require_provider_operation",
]
