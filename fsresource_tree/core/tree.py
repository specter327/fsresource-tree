"""ResourceTree: registro lógico de recursos.

ResourceTree no almacena nada físicamente. Mantiene un índice por `uid`
(`resources`) y, al registrar, conecta los objetos entre sí mutando sus
propios atributos `parent`/`children`. Es el único componente autorizado
a hacer esa mutación: Directory y File no exponen ningún método para
modificarse a sí mismos en ese sentido.

Decisiones de diseño explícitas (ver análisis previo a la implementación):
- `parent` debe ser un Directory ya registrado en este mismo árbol.
- `remove()` es siempre en cascada: al quitar un recurso se quitan también
  todos sus descendientes del registro, para no dejar uids "huérfanos"
  registrados pero inalcanzables desde ningún root.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, Iterator, Optional, Union

from ..core.directory import Directory
from ..core.resource import Resource
from ..exceptions import (
    InvalidParentError,
    ResourceAlreadyRegisteredError,
    ResourceNotFoundError,
)


@dataclass(eq=False, repr=False)
class ResourceTree:
    name: str
    description: Optional[str] = None
    uid: str = field(default_factory=lambda: uuid.uuid4().hex, init=False)
    resources: Dict[str, Resource] = field(default_factory=dict, init=False)

    def register(self, resource: Resource, parent: Optional[Directory] = None) -> str:
        """Registra `resource` en el árbol y crea la relación lógica con
        `parent`, si se indica. No crea nada físicamente."""
        if resource.uid in self.resources:
            raise ResourceAlreadyRegisteredError(
                f"el recurso {resource.uid!r} ya está registrado"
            )

        if parent is not None:
            if not isinstance(parent, Directory):
                raise InvalidParentError("parent debe ser una instancia de Directory")
            if parent.uid not in self.resources:
                raise InvalidParentError(
                    "parent debe estar registrado en este árbol antes de usarse"
                )
            parent.children.append(resource)
            resource.parent = parent  # type: ignore[attr-defined]

        self.resources[resource.uid] = resource
        return resource.uid

    def get(self, uid: str) -> Resource:
        try:
            return self.resources[uid]
        except KeyError as exc:
            raise ResourceNotFoundError(
                f"no existe ningún recurso registrado con uid {uid!r}"
            ) from exc

    def remove(self, resource: Union[str, Resource]) -> bool:
        """Quita `resource` (y, en cascada, todos sus descendientes) del
        registro. Devuelve False si el recurso no estaba registrado."""
        uid = resource if isinstance(resource, str) else resource.uid
        target = self.resources.get(uid)
        if target is None:
            return False

        parent = getattr(target, "parent", None)
        if parent is not None and target in parent.children:
            parent.children.remove(target)
            target.parent = None  # type: ignore[attr-defined]

        for descendant in self._descendants(target):
            self.resources.pop(descendant.uid, None)

        self.resources.pop(uid, None)
        return True

    def registered(self, resource: Union[str, Resource]) -> bool:
        uid = resource if isinstance(resource, str) else resource.uid
        return uid in self.resources

    @staticmethod
    def _descendants(resource: Resource) -> Iterator[Resource]:
        children = getattr(resource, "children", None)
        if not children:
            return
        for child in list(children):
            yield child
            yield from ResourceTree._descendants(child)

    def __repr__(self) -> str:
        return (
            f"ResourceTree(uid={self.uid!r}, name={self.name!r}, "
            f"resources={len(self.resources)})"
        )
