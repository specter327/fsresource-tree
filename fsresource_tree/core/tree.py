"""Filesystem specialization of the generic ResourceTree."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

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

    def add_roots(self, resources: Iterable[Directory]) -> tuple[Directory, ...]:
        candidates = list(resources)
        seen: set[int] = set()
        for root in candidates:
            if not isinstance(root, Directory):
                raise TypeError("filesystem tree roots must be Directory instances")
            stack = [root]
            while stack:
                node = stack.pop()
                identity = id(node)
                if identity in seen:
                    raise ValueError("duplicate reference or cycle in filesystem hierarchy")
                seen.add(identity)
                if not isinstance(node, (Directory, File)):
                    raise TypeError("filesystem trees can contain only Directory or File resources")
                if isinstance(node, Directory):
                    stack.extend(node.children)
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

    def to_dict(self) -> dict[str, Any]:
        return super().to_dict()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FSResourceTree:
        if not isinstance(data, dict):
            raise TypeError("tree data must be a dictionary")
        if data.get("type") != cls.TYPE:
            raise ValueError(f"expected resource type {cls.TYPE!r}")

        from .model import resource_from_dict
        roots = [resource_from_dict(item) for item in data.get("roots", [])]
        return cls(name=data["name"], uid=data["uid"], roots=roots)


__all__ = ["FSResourceTree"]
