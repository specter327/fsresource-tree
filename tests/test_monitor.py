import os

import pytest

from fsresource_tree import (
    Directory, File, FilesystemChangeType, FilesystemProvider,
)


def test_monitor_detects_create_modify_and_delete_without_content_access(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    root = Directory("root")
    provider = FilesystemProvider(physical, resource_root=root)
    events = []
    root.add_listener(events.append)

    try:
        monitor = root.enable_monitor(provider=provider, interval=60)
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
        os.utime(item_path, (previous_mtime + 5, previous_mtime + 5))
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
    physical = tmp_path / "root"
    physical.mkdir()
    root = Directory("root")
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        assert root.monitor_enabled is False
        monitor = root.enable_monitor(provider=provider, interval=60)
        assert root.monitor_enabled is True
        assert root.disable_monitor() is True
        assert root.monitor_enabled is False
        assert root.disable_monitor() is False
        assert monitor.enabled is False
    finally:
        root.disable_monitor()
        provider.close()


def test_monitor_listener_registration_and_removal(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    root = Directory("root")
    provider = FilesystemProvider(physical, resource_root=root)
    received = []
    callback = received.append
    root.add_listener(callback)
    try:
        monitor = root.enable_monitor(provider=provider, interval=60)
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
    physical = tmp_path / "root"
    (physical / "nested").mkdir(parents=True)
    (physical / "nested" / "hidden.txt").touch()
    root = Directory("root")
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        monitor = root.enable_monitor(provider=provider, interval=60, recursive=False)
        assert isinstance(root.find("nested"), Directory)
        assert root.find("hidden") is None
        monitor._poll_once()
        assert root.find("hidden") is None
    finally:
        root.disable_monitor()
        provider.close()


@pytest.mark.parametrize("interval", [0, -1, True, "1"])
def test_monitor_rejects_invalid_interval(tmp_path, interval):
    physical = tmp_path / "root"
    physical.mkdir()
    root = Directory("root")
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        with pytest.raises((TypeError, ValueError)):
            root.enable_monitor(provider=provider, interval=interval)
    finally:
        provider.close()


def test_monitor_rejects_non_callable_listener(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    root = Directory("root")
    with pytest.raises(TypeError, match="callback"):
        root.add_listener(None)


def test_monitor_dispatches_from_background_worker(tmp_path):
    import threading

    physical = tmp_path / "root"
    physical.mkdir()
    root = Directory("root")
    provider = FilesystemProvider(physical, resource_root=root)
    created = threading.Event()

    def listener(event):
        if event.change_type is FilesystemChangeType.CREATED:
            created.set()

    root.add_listener(listener)
    try:
        root.enable_monitor(provider=provider, interval=0.02)
        (physical / "background.txt").touch()
        assert created.wait(3), "background monitor did not dispatch the create event"
    finally:
        root.disable_monitor(timeout=3)
        provider.close()
