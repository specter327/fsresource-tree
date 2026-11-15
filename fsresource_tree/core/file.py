"""Filesystem-specific file resource."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from resourcetree import Asset

from .directory import Directory


class File(Asset):
    """A filesystem file modeled as a generic terminal Asset."""

    TYPE = "file"

    def __init__(
        self,
        name: str,
        extension: str | None = None,
        parent: Directory | None = None,
        uid: str | None = None,
        metadata: dict[str, Any] | None = None,
        data: Any = None,
    ) -> None:
        if extension is not None and not isinstance(extension, str):
            raise TypeError("extension must be a string or None")
        if parent is not None and not isinstance(parent, Directory):
            raise TypeError("a File parent must be a Directory")
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

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["extension"] = self.extension
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> File:
        from .model import validate_resource_payload

        validate_resource_payload(data, allowed_root_types=("file",))
        file = cls(
            name=data["name"],
            extension=data.get("extension"),
            uid=data["uid"],
            metadata=data.get("metadata"),
            data=data.get("data"),
        )
        file.created_at = datetime.fromisoformat(data["created_at"])
        file.updated_at = datetime.fromisoformat(data["updated_at"])
        return file

    def __repr__(self) -> str:
        return f"File(uid={self.uid!r}, name={self.filename()!r})"
