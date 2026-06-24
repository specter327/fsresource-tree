"""Operaciones sobre estructuras de recursos: walk, path, find.

Estas funciones operan directamente sobre el grafo en memoria (via
parent/children) y no requieren una instancia de ResourceTree.
"""

from ..operations.path import path
from ..operations.search import find
from ..operations.walker import walk
from ..operations.exists import exists
from ..operations.create import create

__all__ = ["walk", "path", "find", "exists", "create"]
