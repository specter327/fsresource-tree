"""Renderizado de estructuras de recursos a diagramas Mermaid."""

from __future__ import annotations

from typing import List, Set, Union

from ..core.directory import Directory
from ..core.file import File
from ..operations.walker import walk


def _node_id(resource: Union[Directory, File]) -> str:
    # Prefijo "n" porque un id de nodo Mermaid no puede empezar con
    # ciertos caracteres; el uid (hex) por sí solo podría hacerlo.
    return f"n{resource.uid}"


def _label(resource: Union[Directory, File]) -> str:
    name = resource.filename() if isinstance(resource, File) else resource.name
    return name.replace('"', "'")


def mermaid(resource: Union[Directory, File]) -> str:
    """Genera un diagrama `graph TD` de la estructura a partir de `resource`.

    Usa el `uid` de cada recurso como identificador de nodo (no el
    `name`), para no romper la sintaxis Mermaid con nombres arbitrarios
    (p. ej. "/", espacios, comillas). El `name`/`filename()` se muestra
    como etiqueta entre comillas.
    """
    declarations: List[str] = []
    edges: List[str] = []
    declared: Set[str] = set()

    def declare(node: Union[Directory, File]) -> None:
        if node.uid not in declared:
            declarations.append(f'    {_node_id(node)}["{_label(node)}"]')
            declared.add(node.uid)

    for node in walk(resource):
        declare(node)
        for child in getattr(node, "children", ()):
            declare(child)
            edges.append(f"    {_node_id(node)} --> {_node_id(child)}")

    return "\n".join(["graph TD", *declarations, *edges])
