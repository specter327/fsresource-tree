"""
Eliminación física de recursos.

Transforma una estructura lógica ResourceTree
eliminando recursos del sistema operativo.
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
# Type definition
# =========================================================

Resource = Union[Directory, File]



# =========================================================
# Internal delete
# =========================================================

def _delete_single(
    resource: Resource
) -> bool:
    """
    Elimina únicamente el recurso indicado.

    No elimina padres.
    No elimina hijos.
    """

    resource_path = path(resource)


    if not os.path.exists(resource_path):
        return True



    # -----------------------------------------------------
    # File
    # -----------------------------------------------------

    if isinstance(resource, File):

        os.remove(resource_path)

        return True



    # -----------------------------------------------------
    # Directory
    # -----------------------------------------------------

    if isinstance(resource, Directory):

        os.rmdir(resource_path)

        return True



    raise TypeError(
        f"Unsupported resource: {type(resource)}"
    )



# =========================================================
# Public operation
# =========================================================

def delete(
    resource,
    recursive_children: bool = False,
    recursive_parent: bool = False
) -> bool:
    """
    Elimina un recurso físico.

    Args:

        resource:
            Directory, File o iterable.


        recursive_children:
            Elimina todos los descendientes.


        recursive_parent:
            Elimina padres vacíos después.


    Examples:


        delete(file)

            elimina solo file


        delete(directory, recursive_children=True)

            elimina todo el árbol inferior


        delete(file, recursive_parent=True)

            elimina:
            file
            directorios vacíos superiores

    """



    # =====================================================
    # Iterable
    # =====================================================

    if (
        hasattr(resource, "__iter__")
        and not isinstance(resource, (Directory, File))
    ):

        for item in resource:

            delete(
                item,
                recursive_children=recursive_children,
                recursive_parent=recursive_parent
            )

        return True



    # =====================================================
    # Children first
    # =====================================================

    if recursive_children:

        for child in walk(
            resource,
            inverse=True
        ):

            if child is resource:
                continue

            _delete_single(child)



    # =====================================================
    # Current
    # =====================================================

    _delete_single(resource)



    # =====================================================
    # Cleanup parents
    # =====================================================

    if recursive_parent:

        for parent in ancestors(
            resource,
            include_self=False
        ):

            parent_path = path(parent)

            if os.path.exists(parent_path):

                try:

                    os.rmdir(parent_path)

                except OSError:

                    # contiene otros recursos
                    break



    return True