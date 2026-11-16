import os
import pytest
from fsresource_tree import Directory, FSResourceTree, File, FilesystemProvider
from fsresource_tree.operations import scan

def test_scan_materializes_nested_files_and_directories(tmp_path):
    physical = tmp_path / "root"
    (physical / "docs" / "nested").mkdir(parents=True)
    (physical / "docs" / "nested" / "report.txt").touch()
    (physical / "README").touch()
    root = Directory("root")
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        result = scan(root, provider=provider)
        assert result.count == 4
        assert {item.name for item in result.discovered} == {"docs", "nested", "report", "README"}
        assert isinstance(root.find("docs"), Directory)
        assert isinstance(root.find("README"), File)
    finally:
        provider.close()

def test_scan_updates_tree_index_when_root_is_mounted(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    (physical / "new.txt").touch()
    root = Directory("root")
    tree = FSResourceTree(roots=[root])
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        result = scan(root, provider=provider)
        assert result.count == 1
        item = root.find("new")
        assert isinstance(item, File)
        assert tree.get(item.uid) is item
    finally:
        provider.close()

def test_scan_is_additive_and_reuses_existing_model_children(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    (physical / "known.txt").touch()
    (physical / "new.txt").touch()
    root = Directory("root")
    known = File("known", extension="txt", parent=root)
    stale = File("stale", extension="txt", parent=root)
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        first = scan(root, provider=provider)
        second = scan(root, provider=provider)
        assert first.count == 1
        assert second.count == 0
        assert root.find("known") is known
        assert root.find("stale") is stale
    finally:
        provider.close()

def test_scan_supports_exclusions_and_non_recursive_mode(tmp_path):
    physical = tmp_path / "root"
    (physical / "skip").mkdir(parents=True)
    (physical / "skip" / "hidden.txt").touch()
    (physical / "visible").mkdir()
    (physical / "visible" / "nested.txt").touch()
    root = Directory("root")
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        result = scan(root, provider=provider, recursive=False, excluded_names={"skip"})
        assert result.count == 1
        assert isinstance(root.find("visible"), Directory)
        assert root.find("skip") is None
    finally:
        provider.close()

def test_scan_rejects_model_physical_type_conflicts(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    (physical / "conflict").touch()
    root = Directory("root")
    Directory("conflict", parent=root)
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        with pytest.raises(TypeError, match="type conflict"):
            scan(root, provider=provider)
    finally:
        provider.close()

def test_scan_never_follows_or_materializes_symlinks(tmp_path):
    if os.name != "posix":
        pytest.skip("symlink test uses POSIX semantics")
    physical = tmp_path / "root"
    physical.mkdir()
    outside = tmp_path / "outside.txt"
    outside.touch()
    (physical / "linked.txt").symlink_to(outside)
    root = Directory("root")
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        result = scan(root, provider=provider)
        assert result.count == 0
        assert root.children == ()
        assert result.skipped == ((str(physical / "linked.txt"), "symbolic link or reparse point"),)
    finally:
        provider.close()

def test_scan_requires_existing_physical_directory(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    root = Directory("root")
    provider = FilesystemProvider(physical, resource_root=root)
    provider.delete(root)
    try:
        with pytest.raises(FileNotFoundError):
            scan(root, provider=provider)
    finally:
        provider.close()
