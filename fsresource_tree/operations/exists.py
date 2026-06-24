# Library import
from ..core.directory import Directory
from ..core.file import File
from .path import path
from typing import Union
import os

# Function definition
def exists(resource: Union[Directory, File]) -> bool:
	resource_path = path(resource)

	return os.path.exists(resource_path)