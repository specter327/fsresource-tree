"""Resolución de rutas lógicas a partir de las relaciones parent."""

from __future__ import annotations

from typing import List, Optional, Union

from ..core.directory import Directory
from ..core.file import File
import os

_SEPARATOR = os.sep


def path(resource: Union[Directory, File]) -> str:
    """Resuelve una ruta lógica subiendo por los `parent` de `resource`.

    Usa `filename()` (name + extension) para el segmento final si
    `resource` es un File, y `name` para el resto de los segmentos.

    Nota: esta resolución es genérica y deliberadamente simple; no
    normaliza separadores especiales (p. ej. una raíz llamada "/", que
    produce un separador duplicado al unirse). Ese tipo de convención es
    responsabilidad de especializaciones concretas como fsresource-tree.
    """
    segments: List[str] = []
    current: Optional[Union[Directory, File]] = resource
    is_leaf = True

    while current is not None:
        if is_leaf and hasattr(current, "filename"):
            segments.append(current.filename())
        else:
            segments.append(current.name)
        is_leaf = False
        current = getattr(current, "parent", None)

    segments.reverse()
    return _SEPARATOR.join(segments)
