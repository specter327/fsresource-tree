"""Filesystem symbolic-link resource.

A SymbolicLink preserves the link itself; it never resolves or traverses its
destination and intentionally exposes no filesystem mutation operations.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from resourcetree import Asset

if TYPE_CHECKING:
    from .directory import Directory


class SymbolicLink(Asset):
    """A symbolic link represented as a terminal resource."""

    TYPE = "symbolic_link"

    def __init__(
        self,
        name: str,
        target: str,
        parent: Directory | None = None,
        uid: str | None = None,
        metadata: dict[str, Any] | None = None,
        data: Any = None,
    ) -> None:
        if not isinstance(target, str) or not target:
            raise ValueError("symbolic-link target must be a non-empty string")
        if parent is not None:
            from .directory import Directory
            if not isinstance(parent, Directory):
                raise TypeError("a SymbolicLink parent must be a Directory")
        super().__init__(name=name, parent=parent, uid=uid, data=data, metadata=metadata)
        self.target = target

    def _to_dict_shallow(self) -> dict[str, Any]:
        result = super()._to_dict_shallow()
        result["target"] = self.target
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SymbolicLink:
        from .model import _resource_from_validated_dict, validate_resource_payload
        validate_resource_payload(data, allowed_root_types=("symbolic_link",))
        return _resource_from_validated_dict(data)

    def __repr__(self) -> str:
        return f"SymbolicLink(uid={self.uid!r}, name={self.name!r}, target={self.target!r})"
