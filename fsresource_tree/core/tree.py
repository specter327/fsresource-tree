"""Filesystem specialization of the generic ResourceTree."""

from resourcetree import ResourceTree

from .directory import Directory


class FSResourceTree(ResourceTree):
    """ResourceTree specialization for real filesystem resources.

    String roots are converted to filesystem Directory resources. Discovery,
    physical paths and I/O operations remain implemented by this package.
    """

    def __init__(self, root: Directory | str | None = None, **kwargs) -> None:
        if isinstance(root, str):
            root = Directory(root)
        if root is not None and not isinstance(root, Directory):
            raise TypeError("filesystem tree root must be a Directory or a name")
        super().__init__(root=root, **kwargs)


# Backwards-compatible public name used by fsresource-tree <= 0.1.x.
ResourceTree = FSResourceTree

__all__ = ["FSResourceTree", "ResourceTree"]
