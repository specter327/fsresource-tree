"""Filesystem-specific directory resource."""

from __future__ import annotations

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
        if parent is not None and not isinstance(parent, Directory):
            raise TypeError("a Directory parent must be a Directory")
        super().__init__(name=name, parent=parent, uid=uid, metadata=metadata)

    def _validate_attachment(self, resource) -> None:
        from .file import File

        if not isinstance(resource, (Directory, File)):
            raise TypeError("a Directory can contain only Directory or File resources")
        super()._validate_attachment(resource)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Directory:
        from .model import _resource_from_validated_dict, validate_resource_payload

        validate_resource_payload(data, allowed_root_types=("directory",))
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
        return (
            f"Directory(uid={self.uid!r}, name={self.name!r}, "
            f"children={len(self.children)})"
        )
