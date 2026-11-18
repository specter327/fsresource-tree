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


@pytest.mark.parametrize("initial_kind", ["file", "directory"])
def test_monitor_recovers_from_physical_type_replacement(tmp_path, initial_kind):
    physical, root, provider = make_root(tmp_path)
    entry = physical / "changing"
    if initial_kind == "file":
        entry.touch()
    else:
        entry.mkdir()
        (entry / "nested.txt").touch()
    unrelated = physical / "unrelated.txt"

    events = []
    root.add_listener(events.append)
    try:
        monitor = root.enable_monitor(interval=60)
        old_resource = root.find("changing")
        assert isinstance(old_resource, File if initial_kind == "file" else Directory)

        if initial_kind == "file":
            entry.unlink()
            entry.mkdir()
        else:
            (entry / "nested.txt").unlink()
            entry.rmdir()
            entry.touch()
        unrelated.touch()

        detected = monitor._poll_once()
        replacement = root.find("changing")
        assert isinstance(replacement, Directory if initial_kind == "file" else File)
        assert any(
            event.change_type is FilesystemChangeType.DELETED
            and event.resource is old_resource
            for event in detected
        )
        assert any(
            event.change_type is FilesystemChangeType.CREATED
            and event.resource is replacement
            for event in detected
        )
        assert any(
            event.change_type is FilesystemChangeType.CREATED
            and event.resource.name == "unrelated"
            for event in detected
        )
        # A subsequent poll must remain healthy after the replacement.
        (physical / "later.txt").touch()
        later = monitor._poll_once()
        assert any(
            event.change_type is FilesystemChangeType.CREATED
            and event.resource.name == "later"
            for event in later
        )
    finally:
        root.disable_monitor()
        provider.close()


def test_monitor_detects_library_rename_with_stable_uid(tmp_path):
    physical, root, provider = make_root(tmp_path)
    item_path = physical / "before.txt"
    item_path.touch()
    root.scan()
    item = root.find("before")
    assert isinstance(item, File)
    events = []
    root.add_listener(events.append)

    try:
        monitor = root.enable_monitor(interval=60)
        original_uid = item.uid
        item.rename("after")
        detected = monitor._poll_once()

        moved = next(
            event for event in detected
            if event.change_type is FilesystemChangeType.MOVED
            and event.resource is item
        )
        assert item.uid == original_uid
        assert moved.previous_path == "/root/before.txt"
        assert moved.current_path == "/root/after.txt"
        assert moved.previous is not None and moved.current is not None
    finally:
        root.disable_monitor()
        provider.close()


def test_monitor_detects_library_move_with_stable_uid(tmp_path):
    physical, root, provider = make_root(tmp_path)
    source = physical / "source"
    destination = physical / "destination"
    source.mkdir()
    destination.mkdir()
    (source / "item.txt").touch()
    root.scan()
    source_model = root.find("source")
    destination_model = root.find("destination")
    assert isinstance(source_model, Directory)
    assert isinstance(destination_model, Directory)
    item = source_model.find("item")
    assert isinstance(item, File)

    try:
        monitor = root.enable_monitor(interval=60)
        original_uid = item.uid
        item.move(destination_model)
        detected = monitor._poll_once()
        moved = next(
            event for event in detected
            if event.change_type is FilesystemChangeType.MOVED
            and event.resource is item
        )
        assert item.uid == original_uid
        assert moved.previous_path == "/root/source/item.txt"
        assert moved.current_path == "/root/destination/item.txt"
    finally:
        root.disable_monitor()
        provider.close()


def test_monitor_does_not_publish_partial_snapshot_after_scan_error(tmp_path, monkeypatch):
    physical, root, provider = make_root(tmp_path)
    from types import SimpleNamespace
    from fsresourcetree import PollingMonitor

    try:
        monitor = PollingMonitor(root, interval=60)
        baseline = monitor._collect_snapshot()
        monitor._snapshot = baseline
        original_scan = root.scan

        def partial_scan(**kwargs):
            result = original_scan(**kwargs)
            return SimpleNamespace(
                directory=result.directory,
                skipped=result.skipped + (
                    (str(physical / "inaccessible"), "Permission denied"),
                ),
            )

        monkeypatch.setattr(root, "scan", partial_scan)
        with pytest.raises(OSError, match="Permission denied"):
            monitor._poll_once()
        assert monitor._snapshot is baseline
    finally:
        provider.close()



def test_type_replacement_stops_monitors_in_replaced_directory_subtree(tmp_path):
    physical, root, provider = make_root(tmp_path)
    changing = physical / "changing"
    nested_path = changing / "nested"
    nested_path.mkdir(parents=True)
    (nested_path / "item.txt").touch()
    root.scan()
    stale = root.find("changing")
    assert isinstance(stale, Directory)
    nested = stale.find("nested")
    assert isinstance(nested, Directory)

    try:
        root_monitor = root.enable_monitor(interval=60)
        stale_monitor = stale.enable_monitor(interval=60)
        nested_monitor = nested.enable_monitor(interval=60)
        assert root_monitor.enabled
        assert stale_monitor.enabled
        assert nested_monitor.enabled

        # Replace the monitored directory subtree with a file.
        (nested_path / "item.txt").unlink()
        nested_path.rmdir()
        changing.rmdir()
        changing.touch()

        events = root_monitor._poll_once()
        replacement = root.find("changing")
        assert isinstance(replacement, File)
        assert any(
            event.change_type is FilesystemChangeType.DELETED
            and event.resource is stale
            for event in events
        )
        assert not stale_monitor.running
        assert not nested_monitor.running
        assert stale not in root.children
        assert provider._active_monitors == {root_monitor}
    finally:
        root.disable_monitor()
        # These calls remain safe after automatic subtree shutdown.
        stale.disable_monitor()
        nested.disable_monitor()
        provider.close()
