"""File: recurso hoja.

Un File nunca contiene hijos. Incluye `parent` (a diferencia de la
versión mínima del enunciado) porque las operaciones genéricas (path,
find) necesitan poder subir por los padres sin importar si el nodo de
partida es un Directory o un File.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..core.directory import Directory
from ..core.resource import Resource


@dataclass(eq=False, repr=False)
class File(Resource):
    extension: Optional[str] = None
    parent: Optional[Directory] = None

    def filename(self) -> str:
        """Resuelve name + "." + extension (o solo name si no hay extension)."""
        if self.extension:
            return f"{self.name}.{self.extension}"
        return self.name

    def __repr__(self) -> str:
        return f"File(uid={self.uid!r}, name={self.filename()!r})"
