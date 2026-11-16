"""Opt-in polling monitor for physical filesystem metadata changes.

Monitoring observes metadata only. It never opens or reads file contents.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable

from ..core.directory import Directory
from ..core.file import File
from ..profile import PhysicalProfile
from ..providers import FilesystemProviderProtocol, require_provider_operation
from .scan import scan

_LOG = logging.getLogger(__name__)


class FilesystemChangeType(str, Enum):
    """Changes detectable from point-in-time filesystem metadata snapshots."""

    CREATED = "created"
    DELETED = "deleted"
    MODIFIED = "modified"


@dataclass(frozen=True, slots=True)
class FilesystemChangeEvent:
    """One detected change to a modeled filesystem resource."""

    change_type: FilesystemChangeType
    resource: Directory | File
    previous: PhysicalProfile | None
    current: PhysicalProfile | None
    detected_at: datetime

    @property
    def resource_uid(self) -> str:
        return self.resource.uid


Listener = Callable[[FilesystemChangeEvent], None]


def _profile_state(profile: PhysicalProfile) -> tuple:
    """Comparable profile fields, excluding the observation timestamp."""
    return (
        profile.exists, profile.entry_type, profile.size,
        profile.last_access_time, profile.last_modified_time,
        profile.creation_time, profile.permissions, profile.owner_id,
        profile.group_id, profile.device_id, profile.inode,
        profile.link_count, profile.native_attributes,
    )


def _walk(directory: Directory, *, recursive: bool) -> tuple[Directory | File, ...]:
    resources: list[Directory | File] = [directory]
    if not recursive:
        return (directory, *directory.children)
    stack = list(reversed(directory.children))
    while stack:
        current = stack.pop()
        resources.append(current)
        if isinstance(current, Directory):
            stack.extend(reversed(current.children))
    return tuple(resources)


class PollingMonitor:
    """Background metadata polling scoped to one Directory and provider.

    Keep the provider open for the entire monitoring lifetime. Listener
    callbacks execute on the monitor thread and should return quickly.
    """

    def __init__(
        self,
        directory: Directory,
        *,
        provider: FilesystemProviderProtocol,
        interval: float,
        recursive: bool = True,
    ) -> None:
        if not isinstance(directory, Directory):
            raise TypeError("directory must be a Directory")
        if isinstance(interval, bool) or not isinstance(interval, (int, float)):
            raise TypeError("interval must be a positive number of seconds")
        if interval <= 0:
            raise ValueError("interval must be greater than zero")
        if not isinstance(recursive, bool):
            raise TypeError("recursive must be a bool")
        self.directory = directory
        self.provider = provider
        self.interval = float(interval)
        self.recursive = recursive
        self._listeners: list[Listener] = []
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._snapshot: dict[str, tuple[Directory | File, PhysicalProfile]] = {}
        self._profile = require_provider_operation(provider, "profile")

    @property
    def enabled(self) -> bool:
        thread = self._thread
        return thread is not None and thread.is_alive() and not self._stop_event.is_set()

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
            if self.enabled:
                return
            self._stop_event.clear()
            self._snapshot = self._collect_snapshot()
            self._thread = threading.Thread(
                target=self._run,
                name=f"fsresource-monitor-{self.directory.uid}",
                daemon=True,
            )
            self._thread.start()

    def stop(self, *, timeout: float | None = None) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout)
            if thread.is_alive():
                raise TimeoutError("filesystem monitor did not stop before timeout")
        if thread is None or not thread.is_alive():
            self._thread = None

    def _collect_snapshot(self) -> dict[str, tuple[Directory | File, PhysicalProfile]]:
        root_profile = self._profile(self.directory)
        if root_profile.exists:
            scan(
                self.directory,
                provider=self.provider,
                recursive=self.recursive,
                on_error="raise",
            )
        snapshot = {}
        for resource in _walk(self.directory, recursive=self.recursive):
            observation = root_profile if resource is self.directory else self._profile(resource)
            snapshot[resource.uid] = (resource, observation)
        return snapshot

    def _dispatch(self, event: FilesystemChangeEvent) -> None:
        with self._lock:
            listeners = tuple(self._listeners)
        for callback in listeners:
            try:
                callback(event)
            except Exception:
                _LOG.exception("filesystem monitor listener failed for %s", event.resource_uid)

    def _poll_once(self) -> tuple[FilesystemChangeEvent, ...]:
        current_snapshot = self._collect_snapshot()
        events: list[FilesystemChangeEvent] = []
        now = datetime.now(timezone.utc)
        for uid in set(self._snapshot) | set(current_snapshot):
            previous_item = self._snapshot.get(uid)
            current_item = current_snapshot.get(uid)
            previous = previous_item[1] if previous_item else None
            current = current_item[1] if current_item else None
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
            elif previous.exists and current.exists and _profile_state(previous) != _profile_state(current):
                change = FilesystemChangeType.MODIFIED
            else:
                continue
            events.append(FilesystemChangeEvent(change, resource, previous, current, now))
        self._snapshot = current_snapshot
        events.sort(key=lambda event: (event.resource.path(), event.change_type.value))
        for event in events:
            self._dispatch(event)
        return tuple(events)

    def _run(self) -> None:
        while not self._stop_event.wait(self.interval):
            try:
                self._poll_once()
            except Exception:
                _LOG.exception("filesystem monitor polling failed for %s", self.directory.uid)


__all__ = ["FilesystemChangeEvent", "FilesystemChangeType", "PollingMonitor"]
