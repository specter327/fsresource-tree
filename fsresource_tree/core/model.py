"""Validation and reconstruction helpers for filesystem model dictionaries."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _validate_identity(data: dict[str, Any], kind: str) -> None:
    for field in ("uid", "name"):
        value = data.get(field)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{kind} {field} must be a non-empty string")

    metadata = data.get("metadata", {})
    if not isinstance(metadata, dict):
        raise TypeError(f"{kind} metadata must be a dictionary")

    for field in ("created_at", "updated_at"):
        value = data.get(field)
        if not isinstance(value, str):
            raise ValueError(f"{kind} {field} must be an ISO-8601 string")
        try:
            datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"{kind} {field} must be a valid ISO-8601 timestamp") from exc


def validate_resource_payload(
    data: dict[str, Any],
    *,
    allowed_root_types: tuple[str, ...] = ("directory", "file"),
    seen_uids: set[str] | None = None,
) -> None:
    """Validate a complete serialized resource hierarchy without recursion."""
    if not isinstance(data, dict):
        raise TypeError("resource data must be a dictionary")

    uids = seen_uids if seen_uids is not None else set()
    seen_objects: set[int] = set()
    stack: list[tuple[dict[str, Any], bool]] = [(data, True)]

    while stack:
        node, is_root = stack.pop()
        if not isinstance(node, dict):
            raise TypeError("serialized child resources must be dictionaries")
        identity = id(node)
        if identity in seen_objects:
            raise ValueError("cyclic or repeated serialized resource reference")
        seen_objects.add(identity)

        kind = node.get("type")
        if kind not in {"directory", "file"}:
            raise ValueError(f"unknown filesystem resource type: {kind!r}")
        if is_root and kind not in allowed_root_types:
            expected = ", ".join(repr(item) for item in allowed_root_types)
            raise ValueError(f"expected root resource type to be one of: {expected}")

        _validate_identity(node, kind)
        uid = node["uid"]
        if uid in uids:
            raise ValueError(f"duplicate serialized resource uid: {uid!r}")
        uids.add(uid)

        if kind == "directory":
            children = node.get("children")
            if not isinstance(children, list):
                raise TypeError("directory children must be a list")
            for child in reversed(children):
                if not isinstance(child, dict):
                    raise TypeError("serialized child resources must be dictionaries")
                stack.append((child, False))
        else:
            extension = node.get("extension")
            if extension is not None and not isinstance(extension, str):
                raise TypeError("file extension must be a string or None")
            if "children" in node:
                raise ValueError("file resources cannot contain children")


def validate_tree_payload(data: dict[str, Any], tree_type: str) -> None:
    """Validate tree identity, root shape and global resource identity."""
    if not isinstance(data, dict):
        raise TypeError("tree data must be a dictionary")
    if data.get("type") != tree_type:
        raise ValueError(f"expected resource type {tree_type!r}")

    for field in ("uid", "name"):
        value = data.get(field)
        if not isinstance(value, str) or not value:
            raise ValueError(f"tree {field} must be a non-empty string")

    roots = data.get("roots")
    if not isinstance(roots, list):
        raise TypeError("tree roots must be a list")

    seen_uids: set[str] = set()
    seen_root_objects: set[int] = set()
    for root in roots:
        if not isinstance(root, dict):
            raise TypeError("tree roots must be resource dictionaries")
        if id(root) in seen_root_objects:
            raise ValueError("duplicate serialized root reference")
        seen_root_objects.add(id(root))
        validate_resource_payload(
            root,
            allowed_root_types=("directory",),
            seen_uids=seen_uids,
        )


def resource_from_dict(data: dict[str, Any]):
    """Reconstruct one filesystem resource from its explicit type."""
    validate_resource_payload(data)
    resource_type = data["type"]
    if resource_type == "directory":
        from .directory import Directory
        return Directory.from_dict(data)
    from .file import File
    return File.from_dict(data)
