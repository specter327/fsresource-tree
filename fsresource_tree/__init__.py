"""
fsresources-tree

Filesystem implementation based on resourcetree
"""


from .directory import Directory
from .file import File


__version__ = "0.1.0"


__all__ = [
    "Directory",
    "File"
]