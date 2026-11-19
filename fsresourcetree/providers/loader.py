"""Deterministic selection of filesystem providers for supported runtimes."""

from __future__ import annotations

from os import PathLike
from typing import TYPE_CHECKING

from ..exceptions import UnsupportedPlatformError
from .platforms import (
    LinuxProvider,
    TermuxProvider,
    WindowsProvider,
    detect_runtime_platform,
)

if TYPE_CHECKING:
    from ..core.directory import Directory


class ProviderLoader:
    """Select and instantiate the provider matching the current runtime.

    The loader selects by operating-system runtime, never by filesystem format.
    Provider capabilities remain the authority for operation support.
    """

    _PROVIDERS = {
        "linux": LinuxProvider,
        "termux": TermuxProvider,
        "win32": WindowsProvider,
    }

    @classmethod
    def supported_platforms(cls) -> tuple[str, ...]:
        """Return supported runtime identifiers in stable order."""
        return tuple(cls._PROVIDERS)

    @classmethod
    def provider_class(cls, platform: str | None = None):
        """Resolve a provider class; an explicit platform is useful for inspection."""
        selected = detect_runtime_platform() if platform is None else platform
        try:
            return cls._PROVIDERS[selected]
        except KeyError:
            raise UnsupportedPlatformError(
                f"no filesystem provider is implemented for platform: {selected}"
            ) from None

    @classmethod
    def load(
        cls,
        root: str | PathLike[str],
        *,
        resource_root: Directory,
    ):
        """Instantiate and bind the provider for the detected runtime."""
        provider_type = cls.provider_class()
        return provider_type(root, resource_root=resource_root)


__all__ = ["ProviderLoader"]
