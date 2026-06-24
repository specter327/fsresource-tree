"""Directory: recurso contenedor.

Directory expone `parent` y `children` como DATO puro. No define ningún
método para agregar/quitar hijos o cambiar de padre: esa mutación es
responsabilidad exclusiva de ResourceTree (capa de operaciones), para
respetar la separación DATOS != OPERACIONES y la regla de que los
elementos base nunca actúan sobre otros recursos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ..core.resource import Resource


@dataclass(eq=False, repr=False)
class Directory(Resource):
    parent: Optional["Directory"] = None
    children: List[Resource] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"Directory(uid={self.uid!r}, name={self.name!r}, "
            f"children={len(self.children)})"
        )
