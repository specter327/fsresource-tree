"""Filesystem specialization built on top of the generic resourcetree core."""

from . import operations, renderers
from resourcetree import Resource
from .core.directory import Directory
from .core.file import File
from .core.tree import FSResourceTree
from .exceptions import (
    InvalidParentError,
    ResourceAlreadyRegisteredError,
    ResourceNotFoundError,
    ResourceTreeError,
)

__version__ = "0.3.0"

__all__ = [
    "Resource",
    "File",
    "Directory",
    "FSResourceTree",
    "operations",
    "renderers",
    "ResourceTreeError",
    "ResourceNotFoundError",
    "ResourceAlreadyRegisteredError",
    "InvalidParentError",
]
