"""Búsqueda dentro de estructuras de recursos."""

from __future__ import annotations

from typing import Optional, Union

from ..core.directory import Directory
from ..core.file import File
from ..operations.walker import walk


def find(
    resource: Union[Directory, File], target: str
) -> Optional[Union[Directory, File]]:
    """Busca, dentro de la estructura de `resource`, el primer nodo cuyo
    `name` sea igual a `target` (recorrido top-down). Devuelve None si no
    se encuentra ninguna coincidencia."""
    for node in walk(resource):
        if node.name == target:
            return node
    return None
