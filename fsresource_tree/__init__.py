"""Filesystem specialization built on top of the generic resourcetree core."""

from . import operations, renderers, serializers
from .core.directory import Directory
from .core.file import File
from .core.resource import Resource
from .core.tree import FSResourceTree, ResourceTree
from .exceptions import (
    InvalidParentError,
    ResourceAlreadyRegisteredError,
    ResourceNotFoundError,
    ResourceTreeError,
)

__version__ = "0.2.0"

__all__ = [
    "Resource",
    "File",
    "Directory",
    "FSResourceTree",
    "ResourceTree",
    "operations",
    "serializers",
    "renderers",
    "ResourceTreeError",
    "ResourceNotFoundError",
    "ResourceAlreadyRegisteredError",
    "InvalidParentError",
]
