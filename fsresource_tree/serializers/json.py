"""Serialización de recursos hacia/desde JSON, sobre la base de dict.py."""

from __future__ import annotations

import json
from typing import Optional, Union

from ..core.directory import Directory
from ..core.file import File
from ..serializers.dict import from_dict, to_dict


def to_json(resource: Union[Directory, File], indent: Optional[int] = None) -> str:
    return json.dumps(to_dict(resource), indent=indent)


def from_json(data: str) -> Union[Directory, File]:
    return from_dict(json.loads(data))
