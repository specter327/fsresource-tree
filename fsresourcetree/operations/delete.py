"""Delete physical resources through an explicit filesystem provider."""

from ..core.directory import Directory
from ..core.file import File
from ..providers import FilesystemProviderProtocol, require_provider_operation


def delete(
    resource: Directory | File,
    *,
    provider: FilesystemProviderProtocol,
    recursive_children: bool = False,
    purge: bool = False,
) -> bool:
    if purge:
        if not isinstance(resource, Directory):
            raise TypeError("purge requires a Directory")
        purge_physical = require_provider_operation(provider, "purge")
        return purge_physical(resource)
    if recursive_children:
        delete_tree_physical = require_provider_operation(provider, "delete_tree")
        return delete_tree_physical(resource)
    delete_physical = require_provider_operation(provider, "delete")
    return delete_physical(resource)
