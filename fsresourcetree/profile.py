"""Immutable point-in-time observations of physical filesystem metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PhysicalProfile:
    """Metadata observed from one physical filesystem entry at a single instant.

    ``exists=False`` represents a successful query that found no entry.
    Query failures (permission errors, I/O errors, and so on) are raised and
    are never converted into an absent observation.
    """

    exists: bool
    observed_at: datetime
    entry_type: str | None = None
    size: int | None = None
    last_access_time: datetime | None = None
    last_modified_time: datetime | None = None
    creation_time: datetime | None = None
    permissions: int | None = None
    owner_id: int | None = None
    group_id: int | None = None
    device_id: int | None = None
    inode: int | None = None
    link_count: int | None = None
    native_attributes: tuple[tuple[str, int], ...] = ()

    def to_dict(self) -> dict:
        """Return a serialization-friendly copy of the observation."""
        result = asdict(self)
        for key in (
            "observed_at",
            "last_access_time",
            "last_modified_time",
            "creation_time",
        ):
            value = result[key]
            result[key] = value.isoformat() if value is not None else None
        result["native_attributes"] = dict(self.native_attributes)
        return result
