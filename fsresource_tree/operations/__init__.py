"""Operations over filesystem resource models.

Traversal and logical path calculation are in-memory operations. Physical
operations require an explicit FilesystemProvider.
"""

from .ancestors import ancestors
from .create import create
from .delete import delete
from .exists import exists
from .path import path
from .profile import profile
from .search import find
from .scan import ScanResult, scan
from .walker import walk

__all__ = ["ancestors", "create", "delete", "exists", "find", "path", "profile", "scan", "ScanResult", "walk"]
