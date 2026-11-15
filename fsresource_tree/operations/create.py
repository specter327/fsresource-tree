"""Create physical resources through an explicit filesystem provider."""

from ..core.directory import Directory
from ..core.file import File
from ..providers import FilesystemProvider
from .walker import walk


def create(
    resource: Directory | File,
    *,
    provider: FilesystemProvider,
    recursive_children: bool = False,
) -> bool:
    if not isinstance(provider, FilesystemProvider):
        raise TypeError("provider must be a FilesystemProvider")
    nodes = walk(resource) if recursive_children else iter((resource,))
    for node in nodes:
        provider.create(node)
    return True
