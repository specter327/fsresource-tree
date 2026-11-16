"""Physical existence checks through an explicit filesystem provider."""

from ..core.directory import Directory
from ..core.file import File
from ..providers import FilesystemProviderProtocol, require_provider_operation


def exists(resource: Directory | File, *, provider: FilesystemProviderProtocol) -> bool:
    exists_physical = require_provider_operation(provider, "exists")
    return exists_physical(resource)
