import pytest

from fsresourcetree import Directory, FSResourceTree, File, FilesystemProvider


def test_file_instance_methods_delegate_to_physical_operations(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    root = Directory("root")
    item = File("report", extension="txt", parent=root)
    tree = FSResourceTree(roots=[root])
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        assert not item.exists()
        assert item.create()
        assert item.exists()
        item.rename("annual-report")
        assert item.name == "annual-report"
        assert (physical / "annual-report.txt").is_file()

        duplicate = item.copy(root, new_name="backup")
        assert isinstance(duplicate, File)
        assert duplicate.uid != item.uid
        assert duplicate.exists()
        assert tree.get(duplicate.uid) is duplicate

        assert duplicate.delete()
        assert not duplicate.exists()
        # Physical deletion does not silently detach or destroy the model object.
        assert duplicate.parent is root
        assert tree.get(duplicate.uid) is duplicate
    finally:
        provider.close()


def test_directory_instance_methods_create_scan_and_purge(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    root = Directory("root")
    workspace = Directory("workspace", parent=root)
    File("readme", extension="txt", parent=workspace)
    tree = FSResourceTree(roots=[root])
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        assert workspace.create(recursive_children=True)
        assert workspace.exists()
        (physical / "workspace" / "external.txt").touch()

        result = workspace.scan()
        assert result.count == 1
        external = workspace.find("external")
        assert isinstance(external, File)
        assert tree.get(external.uid) is external

        assert workspace.purge()
        assert not workspace.exists()
        assert workspace.parent is root
    finally:
        provider.close()


def test_directory_move_method_updates_hierarchy_and_physical_location(tmp_path):
    physical = tmp_path / "root"
    (physical / "left").mkdir(parents=True)
    (physical / "right").mkdir()
    (physical / "left" / "folder").mkdir()
    root = Directory("root")
    left = Directory("left", parent=root)
    right = Directory("right", parent=root)
    folder = Directory("folder", parent=left)
    tree = FSResourceTree(roots=[root])
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        uid = folder.uid
        returned = folder.move(right, new_name="moved")
        assert returned is folder
        assert folder.uid == uid
        assert folder.parent is right
        assert tree.get(uid) is folder
        assert (physical / "right" / "moved").is_dir()
        assert not (physical / "left" / "folder").exists()
    finally:
        provider.close()
