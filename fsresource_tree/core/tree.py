"""Filesystem specialization of the generic ResourceTree."""

from resourcetree import ResourceTree


class FSResourceTree(ResourceTree):
    """ResourceTree specialization for real filesystem resources.

    Filesystem discovery, physical paths and I/O operations are implemented
    by this package's filesystem-specific modules.
    """

    pass


# Backwards-compatible public name used by fsresource-tree <= 0.1.x.
ResourceTree = FSResourceTree

__all__ = ["FSResourceTree", "ResourceTree"]
