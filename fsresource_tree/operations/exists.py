"""Physical existence checks through an explicit filesystem provider."""

from ..core.directory import Directory
from ..core.file import File
from ..providers import FilesystemProvider


def exists(resource: Directory | File, *, provider: FilesystemProvider) -> bool:
    if not isinstance(provider, FilesystemProvider):
        raise TypeError("provider must be a FilesystemProvider")
    return provider.exists(resource)
