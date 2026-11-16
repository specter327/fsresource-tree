import os

import pytest

from fsresource_tree import Directory, File, FilesystemProvider
from fsresource_tree.operations.access import executable, readable, writable


def test_file_access_helpers_observe_current_process_access(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    (physical / "report.txt").write_text("sample")
    root = Directory("root")
    report = File("report", extension="txt", parent=root)

    with FilesystemProvider(physical, resource_root=root) as provider:
        assert report.readable(provider=provider)
        assert report.writable(provider=provider)
        if os.name == "posix":
            assert not report.executable(provider=provider)


def test_directory_executable_means_search_access(tmp_path):
    physical = tmp_path / "root"
    (physical / "workspace").mkdir(parents=True)
    root = Directory("root")
    workspace = Directory("workspace", parent=root)

    with FilesystemProvider(physical, resource_root=root) as provider:
        assert workspace.readable(provider=provider)
        assert workspace.writable(provider=provider)
        assert workspace.executable(provider=provider)


def test_access_helpers_return_false_for_missing_resource(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    root = Directory("root")
    missing = File("missing", parent=root)

    with FilesystemProvider(physical, resource_root=root) as provider:
        assert missing.readable(provider=provider) is False
        assert missing.writable(provider=provider) is False
        assert missing.executable(provider=provider) is False


def test_module_level_access_helpers_match_resource_methods(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    (physical / "item").touch()
    root = Directory("root")
    item = File("item", parent=root)

    with FilesystemProvider(physical, resource_root=root) as provider:
        assert readable(item, provider=provider) == item.readable(provider=provider)
        assert writable(item, provider=provider) == item.writable(provider=provider)
        assert executable(item, provider=provider) == item.executable(provider=provider)


def test_access_rejects_invalid_resource_and_mode(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    root = Directory("root")
    with FilesystemProvider(physical, resource_root=root) as provider:
        with pytest.raises(TypeError):
            readable(object(), provider=provider)
        with pytest.raises(ValueError):
            provider.access(root, os.R_OK | (1 << 20))
