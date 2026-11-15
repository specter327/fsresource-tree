"""Filesystem-specific directory resource."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from resourcetree import Container


class Directory(Container):
    """A filesystem directory modeled as a generic Container."""

    TYPE = "directory"

    def __init__(
        self,
        name: str,
        parent: Directory | None = None,
        uid: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(name=name, parent=parent, uid=uid, metadata=metadata)

    def _validate_attachment(self, resource) -> None:
        from .file import File

        if not isinstance(resource, (Directory, File)):
            raise TypeError("a Directory can contain only Directory or File resources")
        super()._validate_attachment(resource)

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result["children"] = [child.to_dict() for child in self.children]
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Directory:
        if not isinstance(data, dict):
            raise TypeError("directory data must be a dictionary")
        if data.get("type") != cls.TYPE:
            raise ValueError(f"expected resource type {cls.TYPE!r}")

        directory = cls(
            name=data["name"],
            uid=data["uid"],
            metadata=data.get("metadata"),
        )
        created_at = datetime.fromisoformat(data["created_at"])
        updated_at = datetime.fromisoformat(data["updated_at"])

        from .model import resource_from_dict
        for child_data in data.get("children", []):
            directory.append_child(resource_from_dict(child_data))

        directory.created_at = created_at
        directory.updated_at = updated_at
        return directory

    def __repr__(self) -> str:
        return (
            f"Directory(uid={self.uid!r}, name={self.name!r}, "
            f"children={len(self.children)})"
        )
