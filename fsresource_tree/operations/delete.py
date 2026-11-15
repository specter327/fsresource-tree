"""Delete physical resources through an explicit filesystem provider."""

from ..core.directory import Directory
from ..core.file import File
from ..providers import FilesystemProvider


def delete(
    resource: Directory | File,
    *,
    provider: FilesystemProvider,
    recursive_children: bool = False,
    purge: bool = False,
) -> bool:
    if not isinstance(provider, FilesystemProvider):
        raise TypeError("provider must be a FilesystemProvider")
    if purge:
        if not isinstance(resource, Directory):
            raise TypeError("purge requires a Directory")
        return provider.purge(resource)
    if recursive_children:
        return provider.delete_tree(resource)
    return provider.delete(resource)
