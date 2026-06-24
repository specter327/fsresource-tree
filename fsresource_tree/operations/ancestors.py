"""
Recorrido de ancestros dentro de una estructura de recursos.

Obtiene la cadena de padres desde un recurso hasta la raíz.
"""

from __future__ import annotations

from typing import Iterator, Union

from ..core.directory import Directory
from ..core.file import File


# Type definition
ResourceType = Union[Directory, File]


# Function definition
def ancestors(
    resource: ResourceType,
    include_self: bool = True,
    inverse: bool = False
) -> Iterator[ResourceType]:
    """
    Recorre los padres de un recurso hasta la raíz.

    Args:
        resource:
            Recurso inicial.

        include_self:
            Si es True, incluye el recurso inicial.
            Si es False, comienza desde el padre.

        inverse:
            False:
                raíz -> recurso

            True:
                recurso -> raíz


    Examples:

        root
        └── home
            └── user
                └── file


        ancestors(file)

        root
        home
        user
        file


        ancestors(file, inverse=True)

        file
        user
        home
        root

    """

    chain = []

    current = resource

    if not include_self:
        current = getattr(current, "parent", None)

    while current is not None:
        chain.append(current)
        current = getattr(current, "parent", None)


    if inverse:
        for item in chain:
            yield item
    else:
        for item in reversed(chain):
            yield item