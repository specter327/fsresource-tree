"""
Eliminación física de recursos.

Transforma una estructura lógica ResourceTree
eliminando recursos del sistema operativo.

Soporta dos modos:

- Normal:
    Respeta únicamente recursos registrados en ResourceTree.

- purge=True:
    El filesystem es la fuente de verdad y elimina
    cualquier contenido físico encontrado.
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
# Internal purge
# =========================================================

def _purge_path(
    resource_path: str
) -> bool:
    """
    Elimina físicamente un árbol completo.

    No depende de ResourceTree.
    Usa únicamente el filesystem.
    """

    if not os.path.exists(resource_path):
        return True


    # -----------------------------------------------------
    # Directory
    # -----------------------------------------------------

    if os.path.isdir(resource_path):

        for child in os.listdir(resource_path):

            child_path = os.path.join(
                resource_path,
                child
            )

            _purge_path(child_path)


        os.rmdir(resource_path)

        return True


    # -----------------------------------------------------
    # File
    # -----------------------------------------------------

    os.remove(resource_path)

    return True



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
    recursive_parent: bool = False,
    purge: bool = False
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


        purge:
            Si True, ignora ResourceTree y elimina
            todo el contenido físico encontrado.


    Examples:


        delete(file)

            elimina solo file


        delete(directory, recursive_children=True)

            elimina descendientes registrados


        delete(
            directory,
            recursive_children=True,
            purge=True
        )

            elimina todo el contenido físico
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
                recursive_parent=recursive_parent,
                purge=purge
            )

        return True



    resource_path = path(resource)



    # =====================================================
    # PURGE MODE
    # =====================================================

    if purge:

        if recursive_children:

            _purge_path(
                resource_path
            )

        else:

            _delete_single(resource)



    # =====================================================
    # ResourceTree MODE
    # =====================================================

    else:

        #
        # Children first
        #

        if recursive_children:

            for child in walk(
                resource,
                inverse=True
            ):

                if child is resource:
                    continue

                _delete_single(child)



        #
        # Current
        #

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