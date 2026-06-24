"""Serialización de recursos hacia/desde dict.

from_dict restaura el `uid` original si viene en los datos (en vez de
generar uno nuevo en cada reconstrucción), para que un round-trip
to_dict -> from_dict preserve la identidad de los recursos.
"""

from __future__ import annotations

from typing import Any, Dict, Union

from ..core.directory import Directory
from ..core.file import File
from ..exceptions import ResourceTreeError


def to_dict(resource: Union[Directory, File]) -> Dict[str, Any]:
    if isinstance(resource, Directory):
        return {
            "uid": resource.uid,
            "type": "directory",
            "name": resource.name,
            "metadata": resource.metadata,
            "children": [to_dict(child) for child in resource.children],
        }

    if isinstance(resource, File):
        return {
            "uid": resource.uid,
            "type": "file",
            "name": resource.name,
            "extension": resource.extension,
            "metadata": resource.metadata,
        }

    raise ResourceTreeError(
        f"no se puede serializar un recurso de tipo {type(resource)!r}"
    )


def from_dict(data: Dict[str, Any]) -> Union[Directory, File]:
    resource_type = data.get("type")

    if resource_type == "directory":
        directory = Directory(name=data["name"], metadata=dict(data.get("metadata", {})))
        if "uid" in data:
            directory.uid = data["uid"]
        for child_data in data.get("children", []):
            child = from_dict(child_data)
            child.parent = directory  # type: ignore[attr-defined]
            directory.children.append(child)
        return directory

    if resource_type == "file":
        file_resource = File(
            name=data["name"],
            extension=data.get("extension"),
            metadata=dict(data.get("metadata", {})),
        )
        if "uid" in data:
            file_resource.uid = data["uid"]
        return file_resource

    raise ResourceTreeError(f"tipo de recurso desconocido: {resource_type!r}")
