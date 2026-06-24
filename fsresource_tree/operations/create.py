"""
Creación física de recursos.

Transforma una estructura lógica ResourceTree
en una estructura real del sistema operativo.
"""

from __future__ import annotations

from typing import Union, Iterable

from ..core.directory import Directory
from ..core.file import File

from ..operations.path import path
from ..operations.walker import walk
from ..operations.ancestors import ancestors

import os


# Type definition
Resource = Union[Directory, File]


def _create_single(
    resource: Resource
) -> bool:
    """
    Crea únicamente el recurso indicado.

    No crea padres.
    No crea hijos.
    """

    resource_path = path(resource)


    # Directory
    if isinstance(resource, Directory):

        if os.path.exists(resource_path):
            return True

        os.mkdir(resource_path)

        return True


    # File
    if isinstance(resource, File):

        parent = os.path.dirname(resource_path)

        if not os.path.exists(parent):
            raise FileNotFoundError(
                f"Parent directory does not exist: {parent}"
            )

        with open(resource_path, "a"):
            pass

        return True


    raise TypeError(
        f"Unsupported resource: {type(resource)}"
    )



def create(
    resource,
    recursive_children: bool = False,
    recursive_parent: bool = False
) -> bool:
    """
    Crea un recurso físico.

    Args:

        resource:
            Directory, File o iterable de recursos.

        recursive_children:
            Crea también todos los descendientes.

        recursive_parent:
            Crea también todos los padres necesarios.


    Examples:


        create(file)

            /
            home
            user
            file


        create(file, recursive_parent=True)

            Crea:
            /
            home
            user
            file


        create(root, recursive_children=True)

            Crea:
            toda la estructura inferior

    """


    # Iterable support
    if (
        hasattr(resource, "__iter__")
        and not isinstance(resource, (Directory, File))
    ):

        for item in resource:

            create(
                item,
                recursive_children=False,
                recursive_parent=False
            )

        return True



    # Create parents first
    if recursive_parent:

        for parent in ancestors(
            resource,
            include_self=False
        ):

            _create_single(parent)



    # Create current resource

    _create_single(resource)



    # Create children

    if recursive_children:

        for child in walk(
            resource,
            inverse=False
        ):

            if child is resource:
                continue

            _create_single(child)


    return True