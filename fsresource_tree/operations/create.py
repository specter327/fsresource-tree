"""
Creación física de recursos.

Transforma una estructura lógica ResourceTree
en una estructura real del sistema operativo.
"""

from __future__ import annotations

from typing import Union

from ..core.directory import Directory
from ..core.file import File

from ..operations.path import path
from ..operations.walker import walk
from ..operations.ancestors import ancestors

import os


Resource = Union[Directory, File]


def _create_single(
    resource: Resource
) -> bool:

    resource_path = path(resource)


    if isinstance(resource, Directory):

        if not os.path.exists(resource_path):
            os.mkdir(resource_path)

        return True


    if isinstance(resource, File):

        parent = os.path.dirname(resource_path)

        if not os.path.exists(parent):
            raise FileNotFoundError(
                f"Parent directory does not exist: {parent}"
            )

        if not os.path.exists(resource_path):
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


    # =====================================================
    # Iterable
    # =====================================================

    if (
        hasattr(resource, "__iter__")
        and not isinstance(resource, (Directory, File))
    ):

        for item in resource:

            create(
                item,
                recursive_children=recursive_children,
                recursive_parent=recursive_parent
            )

        return True



    # =====================================================
    # Parents
    # =====================================================

    if recursive_parent:

        for parent in ancestors(
            resource,
            include_self=False
        ):

            _create_single(parent)



    # =====================================================
    # Current
    # =====================================================

    _create_single(resource)



    # =====================================================
    # Children
    # =====================================================

    if recursive_children:

        for child in walk(resource):

            if child is resource:
                continue


            # aseguramos que el padre físico exista

            create(
                child,
                recursive_parent=False,
                recursive_children=False
            )


    return True