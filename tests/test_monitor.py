import os
import threading

import pytest

from fsresourcetree import (
    Directory,
    File,
    FilesystemChangeType,
    FilesystemProvider,
    ProviderNotConfiguredError,
)


def make_root(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    root = Directory("root")
    provider = FilesystemProvider(physical, resource_root=root)
    return physical, root, provider


def test_monitor_detects_create_modify_and_delete(tmp_path):
    physical, root, provider = make_root(tmp_path)
    events = []
    root.add_listener(events.append)

    try:
        monitor = root.enable_monitor(interval=60)
        assert events == []  # The initial snapshot is a baseline, not an event batch.

        item_path = physical / "report.txt"
        item_path.touch()
        created = monitor._poll_once()
        item = root.find("report")
        assert isinstance(item, File)
        assert any(
            event.change_type is FilesystemChangeType.CREATED
            and event.resource is item for event in created
        )

        previous_mtime = item_path.stat().st_mtime
        os.utime(item_path, (previous_mtime + 10, previous_mtime + 10))
        modified = monitor._poll_once()
        assert any(
            event.change_type is FilesystemChangeType.MODIFIED
            and event.resource is item for event in modified
        )

        item_path.unlink()
        deleted = monitor._poll_once()
        assert any(
            event.change_type is FilesystemChangeType.DELETED
            and event.resource is item for event in deleted
        )
        assert [event.change_type for event in events].count(FilesystemChangeType.CREATED) == 1
        assert [event.change_type for event in events].count(FilesystemChangeType.MODIFIED) >= 1
        assert [event.change_type for event in events].count(FilesystemChangeType.DELETED) == 1
    finally:
        root.disable_monitor()
        provider.close()


def test_monitor_is_opt_in_and_stops_worker(tmp_path):
    _, root, provider = make_root(tmp_path)
    try:
        assert root.monitor_enabled is False
        monitor = root.enable_monitor(interval=60)
        assert root.monitor_enabled is True
        assert root.disable_monitor() is True
        assert root.monitor_enabled is False
        assert root.disable_monitor() is False
        assert monitor.enabled is False
        assert monitor.running is False
    finally:
        root.disable_monitor()
        provider.close()


def test_monitor_listener_registration_and_removal(tmp_path):
    physical, root, provider = make_root(tmp_path)
    received = []
    callback = received.append
    root.add_listener(callback)
    try:
        monitor = root.enable_monitor(interval=60)
        (physical / "new").touch()
        monitor._poll_once()
        assert received
        assert root.remove_listener(callback) is True
        received.clear()
        (physical / "second").touch()
        monitor._poll_once()
        assert received == []
        assert root.remove_listener(callback) is False
    finally:
        root.disable_monitor()
        provider.close()


def test_monitor_recursive_false_limits_discovery_to_direct_children(tmp_path):
    physical, root, provider = make_root(tmp_path)
    (physical / "nested").mkdir()
    (physical / "nested" / "hidden.txt").touch()
    try:
        monitor = root.enable_monitor(interval=60, recursive=False)
        assert isinstance(root.find("nested"), Directory)
        assert root.find("hidden") is None
        monitor._poll_once()
        assert root.find("hidden") is None
    finally:
        root.disable_monitor()
        provider.close()


@pytest.mark.parametrize("interval", [0, -1, True, "1", float("nan"), float("inf")])
def test_monitor_rejects_invalid_interval(tmp_path, interval):
    _, root, provider = make_root(tmp_path)
    try:
        with pytest.raises((TypeError, ValueError)):
            root.enable_monitor(interval=interval)
    finally:
        provider.close()


def test_monitor_requires_a_bound_provider():
    with pytest.raises(ProviderNotConfiguredError):
        Directory("root").enable_monitor()


def test_monitor_cannot_start_after_provider_is_closed(tmp_path):
    _, root, provider = make_root(tmp_path)
    from fsresourcetree import PollingMonitor

    monitor = PollingMonitor(root, interval=60)
    provider.close()
    with pytest.raises(RuntimeError, match="provider is closed"):
        monitor.start()
    assert provider._active_monitors == set()


def test_monitor_rejects_non_callable_listener():
    with pytest.raises(TypeError, match="callback"):
        Directory("root").add_listener(None)


def test_provider_cannot_close_while_monitor_is_running(tmp_path):
    _, root, provider = make_root(tmp_path)
    try:
        root.enable_monitor(interval=60)
        with pytest.raises(RuntimeError, match="stop all directory filesystem monitors"):
            provider.close()
        assert root.monitor_enabled
    finally:
        root.disable_monitor()
        provider.close()


def test_provider_cannot_close_while_descendant_monitor_is_running(tmp_path):
    physical, root, provider = make_root(tmp_path)
    (physical / "nested").mkdir()
    root.scan()
    nested = root.find("nested")
    assert isinstance(nested, Directory)
    try:
        nested.enable_monitor(interval=60)
        with pytest.raises(RuntimeError, match="stop all directory filesystem monitors"):
            provider.close()
    finally:
        nested.disable_monitor()
        provider.close()


def test_monitor_dispatches_from_background_worker(tmp_path):
    physical, root, provider = make_root(tmp_path)
    created = threading.Event()

    def listener(event):
        if event.change_type is FilesystemChangeType.CREATED:
            created.set()

    root.add_listener(listener)
    try:
        root.enable_monitor(interval=0.02)
        (physical / "background.txt").touch()
        assert created.wait(3), "background monitor did not dispatch the create event"
    finally:
        root.disable_monitor(timeout=3)
        provider.close()
