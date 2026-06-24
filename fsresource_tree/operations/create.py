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


# =========================================================
# Types
# =========================================================

Resource = Union[Directory, File]


# =========================================================
# Internal creation
# =========================================================

def _create_single(
    resource: Resource
) -> bool:

    resource_path = path(resource)


    # -----------------------------------------------------
    # Directory
    # -----------------------------------------------------

    if isinstance(resource, Directory):

        if os.path.exists(resource_path):
            return True

        os.mkdir(resource_path)

        return True



    # -----------------------------------------------------
    # File
    # -----------------------------------------------------

    if isinstance(resource, File):

        parent = os.path.dirname(resource_path) or "."

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



# =========================================================
# Public operation
# =========================================================

def create(
    resource,
    recursive_children: bool = False,
    recursive_parent: bool = False
) -> bool:
    """
    Creates a physical resource.

    Args:

        resource:
            Directory, File or iterable of resources.

        recursive_children:
            Create all descendants.

        recursive_parent:
            Create all required ancestors.


    Examples:

        create(file)

            only file


        create(file, recursive_parent=True)

            /
            home
            user
            file


        create(root, recursive_children=True)

            entire subtree

    """



    # =====================================================
    # Iterable support
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
    # Ancestors
    # =====================================================

    if recursive_parent:

        for parent in ancestors(
            resource,
            include_self=False
        ):

            _create_single(parent)



    # =====================================================
    # Current resource
    # =====================================================

    _create_single(resource)



    # =====================================================
    # Descendants
    # =====================================================

    if recursive_children:

        for child in walk(
            resource,
            inverse=False
        ):

            if child is resource:
                continue


            # Garantiza que la ruta superior exista

            create(
                child,
                recursive_parent=True,
                recursive_children=False
            )



    return True