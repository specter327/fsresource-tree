import os

import pytest

from fsresourcetree import Directory, File, FilesystemProvider
from fsresourcetree.operations.access import executable, readable, writable


def test_file_access_helpers_observe_current_process_access(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    (physical / "report.txt").write_text("sample")
    root = Directory("root")
    report = File("report", extension="txt", parent=root)

    with FilesystemProvider(physical, resource_root=root):
        assert report.readable()
        assert report.writable()
        if os.name == "posix":
            assert not report.executable()


def test_directory_executable_means_search_access(tmp_path):
    physical = tmp_path / "root"
    (physical / "workspace").mkdir(parents=True)
    root = Directory("root")
    workspace = Directory("workspace", parent=root)

    with FilesystemProvider(physical, resource_root=root):
        assert workspace.readable()
        assert workspace.writable()
        if os.name == "posix":
            assert workspace.executable()


def test_access_helpers_return_false_for_missing_resource(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    root = Directory("root")
    missing = File("missing", parent=root)

    with FilesystemProvider(physical, resource_root=root):
        assert missing.readable() is False
        assert missing.writable() is False
        assert missing.executable() is False


def test_module_level_access_helpers_match_resource_methods(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    (physical / "item").touch()
    root = Directory("root")
    item = File("item", parent=root)

    with FilesystemProvider(physical, resource_root=root) as provider:
        assert readable(item, provider=provider) == item.readable()
        assert writable(item, provider=provider) == item.writable()
        assert executable(item, provider=provider) == item.executable()


def test_access_rejects_invalid_resource_and_mode(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    root = Directory("root")
    with FilesystemProvider(physical, resource_root=root) as provider:
        with pytest.raises(TypeError):
            readable(object(), provider=provider)
        with pytest.raises(ValueError):
            provider.access(root, os.R_OK | (1 << 20))


def test_access_rejects_symbolic_links(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    (physical / "target").touch()
    try:
        (physical / "link").symlink_to(physical / "target")
    except (NotImplementedError, OSError):
        pytest.skip("symlink creation is unavailable on this platform")
    root = Directory("root")
    link = File("link", parent=root)

    with FilesystemProvider(physical, resource_root=root):
        with pytest.raises(ValueError, match="symbolic links"):
            link.readable()


def test_readable_file_through_search_only_parent(tmp_path):
    if os.name != "posix" or not (
        hasattr(os, "O_PATH") or hasattr(os, "O_SEARCH")
    ):
        pytest.skip("search-only directory descriptors are unavailable")
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root privileges bypass the directory permission scenario")

    physical = tmp_path / "root"
    nested = physical / "search-only"
    nested.mkdir(parents=True)
    target = nested / "known.txt"
    target.write_text("readable")
    target.chmod(0o644)
    nested.chmod(0o111)

    root = Directory("root")
    search_only = Directory("search-only", parent=root)
    report = File("known", extension="txt", parent=search_only)

    with FilesystemProvider(physical, resource_root=root):
        assert report.readable() is True
        # File write access is independent of parent-directory write access.
        assert report.writable() is True


def test_descriptor_provider_fails_closed_without_descriptor_relative_access(tmp_path, monkeypatch):
    physical = tmp_path / "root"
    physical.mkdir()
    (physical / "item").touch()
    root = Directory("root")
    item = File("item", parent=root)

    with FilesystemProvider(physical, resource_root=root) as provider:
        if not provider.race_resistant:
            pytest.skip("descriptor-relative provider mode is unavailable")

        monkeypatch.setattr(os, "supports_dir_fd", set(os.supports_dir_fd) - {os.access})
        with pytest.raises(NotImplementedError, match="descriptor-relative access checks"):
            item.readable()


def test_is_accessible_aliases_match_short_resource_methods(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    (physical / "item").touch()
    root = Directory("root")
    item = File("item", parent=root)

    with FilesystemProvider(physical, resource_root=root):
        assert item.is_readable() == item.readable()
        assert item.is_writable() == item.writable()
        assert item.is_executable() == item.executable()
