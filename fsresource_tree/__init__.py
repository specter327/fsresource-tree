"""resource_tree: modelo lógico en memoria para estructuras jerárquicas
de recursos.

No interactúa con disco ni con ningún sistema externo: es la base
arquitectónica sobre la cual se construyen especializaciones concretas
como fsresource-tree (filesystem POSIX), vsresource-tree (filesystem
virtual), netfsresource-tree (filesystem remoto) o webresource-tree
(APIs/endpoints como recursos).
"""

from . import operations, renderers, serializers
from .core.directory import Directory
from .core.file import File
from .core.resource import Resource
from .core.tree import ResourceTree
from .exceptions import (
    InvalidParentError,
    ResourceAlreadyRegisteredError,
    ResourceNotFoundError,
    ResourceTreeError,
)

__version__ = "0.1.0"

__all__ = [
    "Resource",
    "Directory",
    "File",
    "ResourceTree",
    "operations",
    "serializers",
    "renderers",
    "ResourceTreeError",
    "ResourceNotFoundError",
    "ResourceAlreadyRegisteredError",
    "InvalidParentError",
]
