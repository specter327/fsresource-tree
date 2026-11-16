"""Filesystem-specific file resource."""

from __future__ import annotations

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

    def _to_dict_shallow(self) -> dict[str, Any]:
        result = super()._to_dict_shallow()
        result["extension"] = self.extension
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> File:
        from .model import _resource_from_validated_dict, validate_resource_payload

        validate_resource_payload(data, allowed_root_types=("file",))
        return _resource_from_validated_dict(data)

    @property
    def physical_profile(self):
        """Latest explicitly cached physical metadata observation, if any."""
        return getattr(self, "_physical_profile", None)

    def profile(self, *, provider, update_cache: bool = False):
        """Query physical metadata through an explicit FilesystemProvider."""
        from ..operations.profile import profile

        return profile(self, provider=provider, update_cache=update_cache)

    def __repr__(self) -> str:
        return f"File(uid={self.uid!r}, name={self.filename()!r})"
