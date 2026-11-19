"""Filesystem-specific directory resource."""

from __future__ import annotations

import threading
from typing import Any

from .resource_operations import FilesystemResourceOperations
from .symbolic_link import SymbolicLink
from resourcetree import Container


class Directory(FilesystemResourceOperations, Container):
    """A filesystem directory modeled as a generic Container."""

    TYPE = "directory"

    def __init__(
        self,
        name: str,
        parent: Directory | None = None,
        uid: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if parent is not None and not isinstance(parent, Directory):
            raise TypeError("a Directory parent must be a Directory")
        super().__init__(name=name, parent=parent, uid=uid, metadata=metadata)
        self._filesystem_monitor_lock = threading.RLock()
        self._filesystem_listeners = []
        self._filesystem_monitor = None

    def _validate_attachment(self, resource) -> None:
        from .file import File
        if not isinstance(resource, (Directory, File, SymbolicLink)):
            raise TypeError("a Directory can contain only Directory, File or SymbolicLink resources")
        super()._validate_attachment(resource)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Directory:
        from .model import _resource_from_validated_dict, validate_resource_payload
        validate_resource_payload(data, allowed_root_types=("directory",))
        return _resource_from_validated_dict(data)

    @property
    def physical_profile(self):
        return getattr(self, "_physical_profile", None)

    def profile(self, *, update_cache: bool = False):
        from ..operations.profile import profile
        return profile(self, provider=self._require_provider(), update_cache=update_cache)

    def scan(
        self,
        *,
        recursive: bool = True,
        excluded_names: set[str] | frozenset[str] = frozenset(),
        exclude=None,
        on_error: str = "raise",
        symlink_policy: str = "skip",
    ):
        from ..operations.scan import scan
        return scan(
            self,
            provider=self._require_provider(),
            recursive=recursive,
            excluded_names=excluded_names,
            exclude=exclude,
            on_error=on_error,
            symlink_policy=symlink_policy,
        )

    def purge(self) -> bool:
        from ..operations.delete import delete
        return delete(self, provider=self._require_provider(), purge=True)

    @property
    def monitor_enabled(self) -> bool:
        """Whether this directory currently has an active polling monitor."""
        monitor = getattr(self, "_filesystem_monitor", None)
        return bool(monitor is not None and monitor.enabled)

    def add_listener(self, callback) -> None:
        """Register a one-argument filesystem change callback on this directory."""
        if not callable(callback):
            raise TypeError("callback must be callable")
        with self._filesystem_monitor_lock:
            listeners = getattr(self, "_filesystem_listeners", None)
            if listeners is None:
                listeners = self._filesystem_listeners = []
            if callback not in listeners:
                listeners.append(callback)
            monitor = getattr(self, "_filesystem_monitor", None)
            if monitor is not None:
                monitor.add_listener(callback)

    def remove_listener(self, callback) -> bool:
        """Remove a previously registered filesystem change callback."""
        with self._filesystem_monitor_lock:
            monitor = getattr(self, "_filesystem_monitor", None)
            removed = monitor.remove_listener(callback) if monitor is not None else False
            listeners = getattr(self, "_filesystem_listeners", [])
            try:
                listeners.remove(callback)
                removed = True
            except ValueError:
                pass
            return removed

    def enable_monitor(
        self,
        *,
        interval: float = 1.0,
        recursive: bool = True,
    ):
        """Start opt-in metadata polling using this directory's bound provider.

        Keep the provider open until disable_monitor() returns. Listener
        callbacks execute on the monitor thread.
        """
        from ..operations.monitor import PollingMonitor

        with self._filesystem_monitor_lock:
            current = getattr(self, "_filesystem_monitor", None)
            if current is not None and current.running:
                if current.enabled:
                    return current
                raise RuntimeError("the previous filesystem monitor is still stopping")
            monitor = PollingMonitor(self, interval=interval, recursive=recursive)
            for callback in getattr(self, "_filesystem_listeners", []):
                monitor.add_listener(callback)
            monitor.start()
            self._filesystem_monitor = monitor
            return monitor

    def disable_monitor(self, *, timeout: float | None = None) -> bool:
        """Stop this directory's polling monitor and release its worker thread."""
        with self._filesystem_monitor_lock:
            monitor = getattr(self, "_filesystem_monitor", None)
        if monitor is None:
            return False

        # Do not hold the directory lock while joining: a listener may itself
        # register/remove listeners and must be allowed to finish its callback.
        monitor.stop(timeout=timeout)
        with self._filesystem_monitor_lock:
            if self._filesystem_monitor is monitor and not monitor.running:
                self._filesystem_monitor = None
        return True

    def __repr__(self) -> str:
        return f"Directory(uid={self.uid!r}, name={self.name!r}, children={len(self.children)})"
