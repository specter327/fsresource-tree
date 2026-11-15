"""Delete physical resources through an explicit filesystem provider."""

from ..core.directory import Directory
from ..core.file import File
from ..providers import FilesystemProvider
from .walker import walk


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
    nodes = list(walk(resource, inverse=True)) if recursive_children else [resource]
    for node in nodes:
        provider.delete(node)
    return True
