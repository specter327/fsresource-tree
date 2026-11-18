"""Opt-in polling monitor for physical filesystem metadata changes.

Monitoring observes metadata only. It never opens or reads file contents.
"""
from __future__ import annotations

import logging
import math
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable

from ..core.directory import Directory
from ..core.file import File
from ..profile import PhysicalProfile

_LOG = logging.getLogger(__name__)


class FilesystemChangeType(str, Enum):
    """Changes detectable from point-in-time filesystem metadata snapshots."""

    CREATED = "created"
    DELETED = "deleted"
    MODIFIED = "modified"
    MOVED = "moved"


@dataclass(frozen=True, slots=True)
class FilesystemChangeEvent:
    """One detected change to a modeled filesystem resource.

    ``previous_path`` and ``current_path`` preserve the logical location on
    each side of a move; they are also populated for other event types when
    that side of the observation exists.
    """

    change_type: FilesystemChangeType
    resource: Directory | File
    previous: PhysicalProfile | None
    current: PhysicalProfile | None
    detected_at: datetime
    previous_path: str | None = None
    current_path: str | None = None

    @property
    def resource_uid(self) -> str:
        return self.resource.uid


Listener = Callable[[FilesystemChangeEvent], None]


def _profile_state(profile: PhysicalProfile) -> tuple:
    """Comparable profile fields, excluding the observation timestamp."""
    return (
        profile.exists,
        profile.entry_type,
        profile.size,
        profile.last_modified_time,
        profile.creation_time,
        profile.permissions,
        profile.owner_id,
        profile.group_id,
        profile.device_id,
        profile.inode,
        profile.link_count,
        profile.native_attributes,
    )


def _resource_path(resource: Directory | File) -> str:
    """Return the logical hierarchy path using physical File basenames."""
    segments: list[str] = []
    current: Directory | File | None = resource
    while current is not None:
        segments.append(current.filename() if isinstance(current, File) else current.name)
        current = current.parent
    return "/" + "/".join(reversed(segments))


def _walk(directory: Directory, *, recursive: bool) -> tuple[Directory | File, ...]:
    resources: list[Directory | File] = [directory]
    if not recursive:
        return (directory, *directory.children)
    stack = list(reversed(directory.children))
    while stack:
        current = stack.pop()
        if not isinstance(current, (Directory, File)):
            continue
        resources.append(current)
        if isinstance(current, Directory):
            stack.extend(reversed(current.children))
    return tuple(resources)


class PollingMonitor:
    """Background metadata polling scoped to one Directory.

    The Directory's bound provider must remain open for the monitor lifetime.
    Listener callbacks execute on the monitor thread and should return quickly.
    """

    def __init__(
        self,
        directory: Directory,
        *,
        interval: float = 1.0,
        recursive: bool = True,
    ) -> None:
        if not isinstance(directory, Directory):
            raise TypeError("directory must be a Directory")
        if isinstance(interval, bool) or not isinstance(interval, (int, float)):
            raise TypeError("interval must be a positive finite number of seconds")
        if not math.isfinite(interval) or interval <= 0:
            raise ValueError("interval must be a positive finite number of seconds")
        if not isinstance(recursive, bool):
            raise TypeError("recursive must be a bool")

        self.directory = directory
        self.provider = directory._require_provider()
        self.interval = float(interval)
        self.recursive = recursive
        self._listeners: list[Listener] = []
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._snapshot: dict[str, tuple[Directory | File, PhysicalProfile, str]] = {}

    @property
    def enabled(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive() and not self._stop_event.is_set()

    @property
    def running(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive()

    def add_listener(self, callback: Listener) -> None:
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def remove_listener(self, callback: Listener) -> bool:
        with self._lock:
            try:
                self._listeners.remove(callback)
            except ValueError:
                return False
            return True

    def start(self) -> None:
        with self._lock:
            if self.running:
                if self.enabled:
                    return
                raise RuntimeError("filesystem monitor is still stopping")
            self._stop_event.clear()
            registry_lock = getattr(self.provider, "_monitor_lock", None)
            registry = getattr(self.provider, "_active_monitors", None)
            if registry_lock is not None and registry is not None:
                with registry_lock:
                    if getattr(self.provider, "_monitor_closed", False):
                        raise RuntimeError("filesystem provider is closed")
                    registry.add(self)
            try:
                self._snapshot = self._collect_snapshot()
                self._thread = threading.Thread(
                    target=self._run,
                    name=f"fsresourcetree-monitor-{self.directory.uid}",
                    daemon=True,
                )
                self._thread.start()
            except BaseException:
                if registry_lock is not None and registry is not None:
                    with registry_lock:
                        registry.discard(self)
                self._thread = None
                raise

    def stop(self, *, timeout: float | None = None) -> None:
        if timeout is not None:
            if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
                raise TypeError("timeout must be a non-negative number or None")
            if not math.isfinite(timeout) or timeout < 0:
                raise ValueError("timeout must be a non-negative finite number or None")
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout)
            if thread.is_alive():
                raise TimeoutError("filesystem monitor did not stop before timeout")
        if thread is None or not thread.is_alive():
            self._thread = None
            registry_lock = getattr(self.provider, "_monitor_lock", None)
            registry = getattr(self.provider, "_active_monitors", None)
            if registry_lock is not None and registry is not None:
                with registry_lock:
                    registry.discard(self)

    def _remove_type_conflicts(self, skipped: tuple[tuple[str, str], ...]) -> bool:
        """Detach stale model nodes whose physical entry changed resource type.

        The next scan pass materializes the replacement using the correct
        resource class. Detaching through the parent keeps ResourceTree indexes
        consistent and also retires any stale descendants of a replaced
        Directory.
        """
        root_path = self.provider.resolve(self.directory, allow_missing=False)
        conflicts = [
            Path(path) for path, reason in skipped
            if reason.startswith("model/physical type conflict")
        ]
        changed = False
        for physical_path in sorted(conflicts, key=lambda item: len(item.parts)):
            try:
                relative = physical_path.relative_to(root_path)
            except ValueError:
                continue
            if not relative.parts:
                continue
            parent = self.directory
            for segment in relative.parts[:-1]:
                child = next(
                    (
                        item for item in parent.children
                        if (item.filename() if isinstance(item, File) else item.name) == segment
                    ),
                    None,
                )
                if not isinstance(child, Directory):
                    parent = None
                    break
                parent = child
            if parent is None:
                continue
            stale = next(
                (
                    item for item in parent.children
                    if (item.filename() if isinstance(item, File) else item.name) == relative.name
                ),
                None,
            )
            if stale is not None:
                parent.remove_child(stale)
                changed = True
        return changed

    def _collect_snapshot(self) -> dict[str, tuple[Directory | File, PhysicalProfile, str]]:
        root_profile = self.directory.profile()
        if root_profile.exists:
            result = self.directory.scan(
                recursive=self.recursive, on_error="skip"
            )
            recoverable_skips = {
                "symbolic link or reparse point",
                "unsupported filesystem entry type",
            }
            type_conflicts = []
            for path, reason in result.skipped:
                if reason.startswith("model/physical type conflict"):
                    type_conflicts.append((path, reason))
                elif reason not in recoverable_skips and reason != "excluded by scan policy":
                    # A partial snapshot after an I/O/race error could make
                    # resources look deleted. Preserve the previous snapshot
                    # instead of dispatching false deletion events.
                    raise OSError(f"filesystem scan failed at {path!r}: {reason}")
            if self._remove_type_conflicts(tuple(type_conflicts)):
                # Re-scan after removing stale model objects. This discovers
                # replacement entries and prevents one conflict from
                # permanently blocking unrelated changes.
                self.directory.scan(recursive=self.recursive, on_error="raise")
        snapshot: dict[str, tuple[Directory | File, PhysicalProfile, str]] = {}
        for resource in _walk(self.directory, recursive=self.recursive):
            observation = root_profile if resource is self.directory else resource.profile()
            snapshot[resource.uid] = (resource, observation, _resource_path(resource))
        return snapshot

    def _dispatch(self, event: FilesystemChangeEvent) -> None:
        with self._lock:
            listeners = tuple(self._listeners)
        for callback in listeners:
            try:
                callback(event)
            except Exception:
                _LOG.exception(
                    "filesystem monitor listener failed for %s",
                    event.resource_uid,
                )

    def _poll_once(self) -> tuple[FilesystemChangeEvent, ...]:
        current_snapshot = self._collect_snapshot()
        events: list[FilesystemChangeEvent] = []
        detected_at = datetime.now(timezone.utc)

        for uid in set(self._snapshot) | set(current_snapshot):
            previous_item = self._snapshot.get(uid)
            current_item = current_snapshot.get(uid)
            previous = previous_item[1] if previous_item else None
            current = current_item[1] if current_item else None
            previous_path = previous_item[2] if previous_item else None
            current_path = current_item[2] if current_item else None
            resource = (current_item or previous_item)[0]

            if previous is None:
                if current is not None and current.exists:
                    change = FilesystemChangeType.CREATED
                else:
                    continue
            elif current is None:
                if previous.exists:
                    change = FilesystemChangeType.DELETED
                else:
                    continue
            elif not previous.exists and current.exists:
                change = FilesystemChangeType.CREATED
            elif previous.exists and not current.exists:
                change = FilesystemChangeType.DELETED
            elif previous.exists and current.exists and previous_path != current_path:
                change = FilesystemChangeType.MOVED
            elif (
                previous.exists
                and current.exists
                and _profile_state(previous) != _profile_state(current)
            ):
                change = FilesystemChangeType.MODIFIED
            else:
                continue

            events.append(
                FilesystemChangeEvent(
                    change, resource, previous, current, detected_at,
                    previous_path=previous_path, current_path=current_path,
                )
            )

        self._snapshot = current_snapshot
        events.sort(
            key=lambda event: (
                event.current_path or event.previous_path or _resource_path(event.resource),
                event.change_type.value,
            )
        )
        for event in events:
            self._dispatch(event)
        return tuple(events)

    def _run(self) -> None:
        try:
            while not self._stop_event.wait(self.interval):
                try:
                    self._poll_once()
                except Exception:
                    _LOG.exception(
                        "filesystem monitor polling failed for %s",
                        self.directory.uid,
                    )
        finally:
            registry_lock = getattr(self.provider, "_monitor_lock", None)
            registry = getattr(self.provider, "_active_monitors", None)
            if registry_lock is not None and registry is not None:
                with registry_lock:
                    registry.discard(self)


__all__ = ["FilesystemChangeEvent", "FilesystemChangeType", "PollingMonitor"]
