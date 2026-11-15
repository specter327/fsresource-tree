"""Filesystem specialization of the generic ResourceTree."""

from __future__ import annotations

from collections.abc import Iterable

from resourcetree import ResourceTree

from .directory import Directory
from .file import File


class FSResourceTree(ResourceTree):
    """ResourceTree whose roots and descendants are filesystem resources.

    A filesystem forest consists of one or more Directory roots. Its hierarchy
    may contain only Directory and File instances.
    """

    def __init__(
        self,
        *,
        roots: Iterable[Directory] | None = None,
        name: str | None = None,
        uid: str | None = None,
    ) -> None:
        super().__init__(roots=roots, name=name, uid=uid)

    def _collect(self, resource):
        """Validate filesystem types before the generic tree indexes a subtree.

        ResourceTree uses _collect for root registration, child registration
        and cross-tree mounting. Keeping specialization validation here makes
        every one of those mutation paths enforce the same model contract.
        """
        if not isinstance(resource, (Directory, File)):
            raise TypeError("filesystem subtrees must start with a Directory or File")

        seen: set[int] = set()
        stack = [resource]
        while stack:
            node = stack.pop()
            identity = id(node)
            if identity in seen:
                raise ValueError("duplicate reference or cycle in filesystem hierarchy")
            seen.add(identity)

            if not isinstance(node, (Directory, File)):
                raise TypeError(
                    "filesystem trees can contain only Directory or File resources"
                )

            if isinstance(node, Directory):
                child_ids: set[int] = set()
                for child in node.children:
                    if not isinstance(child, (Directory, File)):
                        raise TypeError(
                            "filesystem trees can contain only Directory or File resources"
                        )
                    if id(child) in child_ids:
                        raise ValueError("duplicate child reference in filesystem hierarchy")
                    child_ids.add(id(child))
                    if child.parent is not node:
                        raise ValueError("inconsistent parent/child relationship")
                stack.extend(reversed(node.children))

        return super()._collect(resource)

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
        from .model import resource_from_dict, validate_tree_payload

        validate_tree_payload(data, cls.TYPE)
        roots = [resource_from_dict(item) for item in data["roots"]]
        return cls(name=data["name"], uid=data["uid"], roots=roots)


__all__ = ["FSResourceTree"]
