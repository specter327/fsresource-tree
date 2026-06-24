# operations/create.py

from collections.abc import Iterable

from ..core.directory import Directory
from ..core.file import File

from .path import path

import os


def create(resource):

    # Iterable de recursos
    if isinstance(resource, Iterable) and not isinstance(
        resource,
        (Directory, File)
    ):
        for item in resource:
            create(item)

        return True

    # Directorio
    if isinstance(resource, Directory):
        os.mkdir(path(resource))
        return True

    # Archivo
    if isinstance(resource, File):
        with open(path(resource), "a"):
            pass

        return True

    raise TypeError(
        f"Unsupported resource type: {type(resource)}"
    )