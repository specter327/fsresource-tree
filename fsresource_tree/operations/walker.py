"""Recorrido de estructuras de recursos."""

from __future__ import annotations

from typing import Iterator, Union

from ..core.directory import Directory
from ..core.file import File


def walk(
    resource: Union[Directory, File], inverse: bool = False
) -> Iterator[Union[Directory, File]]:
    """Recorre la estructura a partir de `resource`.

    inverse=False (default): orden top-down, el recurso primero y luego
    sus hijos, recursivamente.
    inverse=True: orden bottom-up, los hijos primero y `resource` al final.
    """
    children = getattr(resource, "children", ())

    if not inverse:
        yield resource
        for child in children:
            yield from walk(child, inverse=inverse)
    else:
        for child in children:
            yield from walk(child, inverse=inverse)
        yield resource
