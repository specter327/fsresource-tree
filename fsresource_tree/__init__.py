"""Filesystem specialization built on top of the generic resourcetree core."""

from . import operations, renderers
from resourcetree import Resource
from .core.directory import Directory
from .core.file import File
from .core.tree import FSResourceTree
from .providers import FilesystemProvider
from .exceptions import (
    InvalidParentError,
    ResourceAlreadyRegisteredError,
    ResourceNotFoundError,
    ResourceTreeError,
)

__version__ = "0.4.0"

__all__ = [
    "Resource",
    "File",
    "Directory",
    "FSResourceTree",
    "FilesystemProvider",
    "operations",
    "renderers",
    "ResourceTreeError",
    "ResourceNotFoundError",
    "ResourceAlreadyRegisteredError",
    "InvalidParentError",
]
