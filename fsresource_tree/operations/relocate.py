"""Physical copy, move and rename operations for filesystem resources."""

from __future__ import annotations

from ..core.directory import Directory
from ..core.file import File
from ..providers import FilesystemProviderProtocol, require_provider_operation
from .walker import walk


Resource = Directory | File


def _physical_name(resource: Resource, name: str) -> str:
    if not isinstance(name, str) or not name or name in {".", ".."}:
        raise ValueError("name must be a non-empty path component")
    return name


def _validate_move(resource: Resource, destination: Directory) -> None:
    if resource.parent is None:
        raise PermissionError("a filesystem root cannot be moved or renamed")
    if resource.tree is not destination.tree:
        raise ValueError("source and destination must belong to the same ResourceTree")
    current = destination
    while current is not None:
        if current is resource:
            raise ValueError("a directory cannot be moved into itself or one of its descendants")
        current = current.parent
    if destination is resource.parent:
        return
    if resource in destination.children:
        raise ValueError("destination already contains this resource")


def move(
    resource: Resource,
    destination: Directory,
    *,
    provider: FilesystemProviderProtocol,
    new_name: str | None = None,
) -> Resource:
    """Move a resource to another directory; preserve its UID and descendants."""
    if not isinstance(resource, (Directory, File)):
        raise TypeError("resource must be a Directory or File")
    if not isinstance(destination, Directory):
        raise TypeError("destination must be a Directory")
    target_name = resource.name if new_name is None else _physical_name(resource, new_name)
    old_parent = resource.parent
    if old_parent is None:
        raise PermissionError("a filesystem root cannot be moved or renamed")
    _validate_move(resource, destination)
    if old_parent is destination and target_name == resource.name:
        return resource
    if any(child is not resource and child.name == target_name for child in destination.children):
        raise FileExistsError(target_name)
    physical_move = require_provider_operation(provider, "move")
    physical_move(resource, destination, target_name)
    if old_parent is destination:
        resource.name = target_name
        resource.touch()
    else:
        destination.append_child(resource)
        resource.name = target_name
        resource.touch()
    return resource


def rename(
    resource: Resource,
    new_name: str,
    *,
    provider: FilesystemProviderProtocol,
) -> Resource:
    """Rename one resource in place while preserving its UID."""
    if not isinstance(resource, (Directory, File)):
        raise TypeError("resource must be a Directory or File")
    if resource.parent is None:
        raise PermissionError("a filesystem root cannot be renamed")
    return move(resource, resource.parent, provider=provider, new_name=new_name)


def _clone(resource: Resource) -> Resource:
    if isinstance(resource, File):
        return File(resource.name, extension=resource.extension, metadata=resource.metadata)
    clone = Directory(resource.name, metadata=resource.metadata)
    source_stack = [(resource, clone)]
    while source_stack:
        original, duplicate = source_stack.pop()
        for child in original.children:
            if isinstance(child, File):
                duplicate.append_child(
                    File(child.name, extension=child.extension, metadata=child.metadata)
                )
            elif isinstance(child, Directory):
                child_clone = Directory(child.name, metadata=child.metadata)
                duplicate.append_child(child_clone)
                source_stack.append((child, child_clone))
            else:
                raise TypeError("filesystem hierarchies can contain only File or Directory")
    return clone


def copy(
    resource: Resource,
    destination: Directory,
    *,
    provider: FilesystemProviderProtocol,
    new_name: str | None = None,
) -> Resource:
    """Copy a modeled file/directory subtree with fresh resource identities.

    Directory copies reproduce the modeled hierarchy only. Physical entries
    absent from the model are not discovered or copied; call scan() first when
    a complete physical representation is required. File bytes are transferred
    internally by the provider and are never returned to the caller.
    """
    if not isinstance(resource, (Directory, File)):
        raise TypeError("resource must be a Directory or File")
    if not isinstance(destination, Directory):
        raise TypeError("destination must be a Directory")
    if resource.tree is not destination.tree:
        raise ValueError("source and destination must belong to the same ResourceTree")
    target_name = resource.name if new_name is None else _physical_name(resource, new_name)
    if any(child.name == target_name for child in destination.children):
        raise FileExistsError(target_name)
    physical_exists = require_provider_operation(provider, "exists")
    if not physical_exists(resource):
        raise FileNotFoundError(resource.path())
    physical_copy_file = require_provider_operation(provider, "copy_file")
    physical_create = require_provider_operation(provider, "create")
    clone = _clone(resource)
    clone.name = target_name
    destination.append_child(clone)
    try:
        nodes = list(walk(clone))
        originals = list(walk(resource))
        if len(nodes) != len(originals):
            raise RuntimeError("internal copy model mismatch")
        source_by_position = iter(originals)
        for node in nodes:
            original = next(source_by_position)
            if isinstance(node, Directory):
                if not physical_exists(original):
                    raise FileNotFoundError(original.path())
                physical_create(node)
            else:
                if not physical_exists(original):
                    raise FileNotFoundError(original.path())
                parent = node.parent
                if not isinstance(parent, Directory):
                    raise TypeError("copied File must have a Directory parent")
                physical_copy_file(original, parent, node.name)
        return clone
    except BaseException:
        try:
            if isinstance(clone, Directory):
                purge = getattr(provider, "purge", None)
                if callable(purge):
                    purge(clone)
                else:
                    for node in walk(clone, inverse=True):
                        if physical_exists(node):
                            require_provider_operation(provider, "delete")(node)
            elif physical_exists(clone):
                require_provider_operation(provider, "delete")(clone)
        finally:
            destination.remove_child(clone)
        raise


__all__ = ["copy", "move", "rename"]
