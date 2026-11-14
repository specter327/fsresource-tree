"""Filesystem-specific file resource."""

from __future__ import annotations

from typing import Any

from resourcetree import Asset

from .directory import Directory


class File(Asset):
    """A filesystem file modeled as a generic terminal Asset."""

    def __init__(
        self,
        name: str,
        extension: str | None = None,
        parent: Directory | None = None,
        uid: str | None = None,
        metadata: dict[str, Any] | None = None,
        data: Any = None,
    ) -> None:
        super().__init__(
            name=name,
            parent=parent,
            uid=uid,
            data=data,
            metadata=metadata,
        )
        self.extension = extension

    def filename(self) -> str:
        return f"{self.name}.{self.extension}" if self.extension else self.name

    def __repr__(self) -> str:
        return f"File(uid={self.uid!r}, name={self.filename()!r})"
