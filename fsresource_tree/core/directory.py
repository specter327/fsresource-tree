"""Filesystem-specific directory resource."""

from __future__ import annotations

from typing import Any

from resourcetree import Container


class Directory(Container):
    """A filesystem directory modeled as a generic Container."""

    def __init__(
        self,
        name: str,
        parent: Directory | None = None,
        uid: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, parent=parent, uid=uid, metadata=metadata)

    def __repr__(self) -> str:
        return (
            f"Directory(uid={self.uid!r}, name={self.name!r}, "
            f"children={len(self.children)})"
        )
