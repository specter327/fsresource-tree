"""Excepciones propias de resource_tree."""

from __future__ import annotations


class ResourceTreeError(Exception):
    """Excepción base para errores de la librería."""


class ResourceNotFoundError(ResourceTreeError, KeyError):
    """No existe un recurso registrado con el uid solicitado."""


class ResourceAlreadyRegisteredError(ResourceTreeError, ValueError):
    """El recurso ya está registrado en el árbol."""


class InvalidParentError(ResourceTreeError, ValueError):
    """El parent indicado no es un Directory válido o no está registrado."""
