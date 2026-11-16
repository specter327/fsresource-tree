"""Create physical resources through an explicit filesystem provider."""

from ..core.directory import Directory
from ..core.file import File
from ..providers import FilesystemProviderProtocol, require_provider_operation
from .walker import walk


def create(
    resource: Directory | File,
    *,
    provider: FilesystemProviderProtocol,
    recursive_children: bool = False,
) -> bool:
    create_physical = require_provider_operation(provider, "create")
    nodes = walk(resource) if recursive_children else iter((resource,))
    for node in nodes:
        create_physical(node)
    return True
