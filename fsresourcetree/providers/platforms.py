"""Runtime-specific provider classes built on the shared local implementation."""

from __future__ import annotations

import os
import sys

from ..exceptions import UnsupportedPlatformError
from .local import FilesystemProvider


def detect_runtime_platform() -> str:
    """Return the supported runtime identifier without guessing filesystem type."""
    if os.environ.get("TERMUX_VERSION"):
        return "termux"
    if sys.platform == "linux":
        return "linux"
    if sys.platform == "win32":
        return "win32"
    return sys.platform


class _PlatformProvider(FilesystemProvider):
    """Shared implementation with an explicit runtime compatibility guard."""

    EXPECTED_PLATFORM: str

    def __init__(self, root, *, resource_root):
        actual = detect_runtime_platform()
        if actual != self.EXPECTED_PLATFORM:
            raise UnsupportedPlatformError(
                f"{type(self).__name__} requires runtime platform "
                f"{self.EXPECTED_PLATFORM!r}; detected {actual!r}"
            )
        super().__init__(root, resource_root=resource_root)


class LinuxProvider(_PlatformProvider):
    """GNU/Linux provider using the shared POSIX descriptor-relative backend."""

    EXPECTED_PLATFORM = "linux"


class TermuxProvider(_PlatformProvider):
    """Termux provider; reuses POSIX primitives while reporting Android runtime."""

    EXPECTED_PLATFORM = "termux"


class WindowsProvider(_PlatformProvider):
    """Windows provider using the shared path-based implementation."""

    EXPECTED_PLATFORM = "win32"


__all__ = [
    "LinuxProvider",
    "TermuxProvider",
    "WindowsProvider",
    "detect_runtime_platform",
]
