"""Internal reconstruction factory for filesystem model dictionaries."""

from __future__ import annotations

from typing import Any


def resource_from_dict(data: dict[str, Any]):
    """Reconstruct one filesystem resource from its explicit type."""
    if not isinstance(data, dict):
        raise TypeError("resource data must be a dictionary")

    resource_type = data.get("type")
    if resource_type == "directory":
        from .directory import Directory
        return Directory.from_dict(data)
    if resource_type == "file":
        from .file import File
        return File.from_dict(data)
    raise ValueError(f"unknown filesystem resource type: {resource_type!r}")
