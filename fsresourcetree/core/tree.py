""""Filesystem specialization of the generic ResourceTree."""

from __future__ import annotations

from collections.abc import Iterable

from resourcetree import ResourceTree

from .directory import Directory
from .file import File
from .symbolic_link import SymbolicLink


class FSResourceTree(ResourceTree):
    """ResourceTree whose roots and descendants are filesystem resources.

    A filesystem forest consists of one or more Directory roots. Its hierarchy
    may contain Directory, File and SymbolicLink instances.
    """

    def __init__(
        self,
        *,
        roots: Iterable[Directory] | None = None,
        name: str | None = None,
        uid: str | None = None,
    ) -> None:
        super().__init__(roots=roots, name=name, uid=uid)

    def _validate_node(self, resource) -> None:
        if not isinstance(resource, (Directory, File, SymbolicLink)):
            raise TypeError(
                "filesystem trees can contain only Directory, File or SymbolicLink resources"
            )

    def add_roots(self, resources: Iterable[Directory]) -> tuple[Directory, ...]:
        candidates = list(resources)
        for root in candidates:
            if not isinstance(root, Directory):
                raise TypeError("filesystem tree roots must be Directory instances")
        return super().add_roots(candidates)

    def register(self, resource, parent: Directory | None = None) -> str:
        if not isinstance(resource, (Directory, File)):
            raise TypeError("filesystem trees can register only Directory or File resources")
        if parent is not None and not isinstance(parent, Directory):
            raise TypeError("filesystem resource parent must be a Directory")
        return super().register(resource, parent)

    def mount(self, entrypoint: Directory, tree: ResourceTree) -> tuple[Directory, ...]:
        if not isinstance(entrypoint, Directory):
            raise TypeError("filesystem mount entrypoint must be a Directory")
        if not isinstance(tree, FSResourceTree):
            raise TypeError("only an FSResourceTree can be mounted into an FSResourceTree")
        return super().mount(entrypoint, tree)

    @classmethod
    def from_dict(cls, data: dict) -> FSResourceTree:
        from .model import _resource_from_validated_dict, validate_tree_payload

        validate_tree_payload(data, cls.TYPE)
        roots = [_resource_from_validated_dict(item) for item in data["roots"]]
        return cls(name=data["name"], uid=data["uid"], roots=roots)


__all__ = ["FSResourceTree"]
