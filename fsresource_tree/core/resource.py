"""Compatibility import for the generic Resource base class.

Filesystem resources inherit their shared identity and metadata model
from the resourcetree package; this module intentionally defines no
parallel Resource implementation.
"""

from resourcetree import Resource

__all__ = ["Resource"]
