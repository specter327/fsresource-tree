"""Clase base para todos los recursos del árbol.

Un Resource es exclusivamente DATO: identidad (uid) + nombre + metadata
libre. No conoce relaciones jerárquicas (eso es responsabilidad de las
subclases Directory/File) y nunca ejecuta operaciones sobre otros
recursos ni sobre estructuras externas.

Nota de implementación: se desactiva la generación automática de
__eq__/__repr__ de @dataclass porque Directory/File forman referencias
circulares (parent <-> children). Si se dejara el comportamiento por
defecto, comparar o imprimir un recurso podría entrar en recursión
infinita al intentar recorrer toda la estructura conectada. En su lugar,
identidad, igualdad y hash se basan únicamente en `uid`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(eq=False, repr=False)
class Resource:
    name: str
    metadata: Dict[Any, Any] = field(default_factory=dict)
    uid: str = field(default_factory=lambda: uuid.uuid4().hex, init=False)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Resource):
            return NotImplemented
        return self.uid == other.uid

    def __hash__(self) -> int:
        return hash(self.uid)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(uid={self.uid!r}, name={self.name!r})"
