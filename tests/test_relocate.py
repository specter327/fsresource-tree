import pytest

from fsresource_tree import Directory, FSResourceTree, File, FilesystemProvider
from fsresource_tree.operations import copy, move, rename


def test_rename_preserves_identity_and_updates_physical_name(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    (physical / "before.txt").write_text("opaque payload")
    root = Directory("root")
    item = File("before", extension="txt", parent=root)
    tree = FSResourceTree(roots=[root])
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        uid = item.uid
        rename(item, "after", provider=provider)
        assert item.uid == uid
        assert item.name == "after"
        assert not (physical / "before.txt").exists()
        assert (physical / "after.txt").read_text() == "opaque payload"
        assert tree.get(uid) is item
    finally:
        provider.close()


def test_move_preserves_identity_and_updates_parent_and_index(tmp_path):
    physical = tmp_path / "root"
    (physical / "left").mkdir(parents=True)
    (physical / "right").mkdir()
    (physical / "left" / "item.txt").touch()
    root = Directory("root")
    left = Directory("left", parent=root)
    right = Directory("right", parent=root)
    item = File("item", extension="txt", parent=left)
    tree = FSResourceTree(roots=[root])
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        uid = item.uid
        move(item, right, provider=provider)
        assert item.uid == uid
        assert item.parent is right
        assert left.find("item") is None
        assert right.find("item") is item
        assert tree.get(uid) is item
        assert (physical / "right" / "item.txt").exists()
        assert not (physical / "left" / "item.txt").exists()
    finally:
        provider.close()


def test_copy_file_creates_new_identity_and_preserves_source(tmp_path):
    physical = tmp_path / "root"
    (physical / "source").mkdir(parents=True)
    (physical / "destination").mkdir()
    (physical / "source" / "data.bin").write_bytes(b"payload")
    root = Directory("root")
    source_dir = Directory("source", parent=root)
    destination = Directory("destination", parent=root)
    source = File("data", extension="bin", parent=source_dir, data={"model": "payload"})
    tree = FSResourceTree(roots=[root])
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        duplicate = copy(source, destination, provider=provider, new_name="copy")
        assert isinstance(duplicate, File)
        assert duplicate.uid != source.uid
        assert duplicate.data == source.data
        assert duplicate.data is source.data
        assert duplicate.parent is destination
        assert (physical / "source" / "data.bin").read_bytes() == b"payload"
        assert (physical / "destination" / "copy.bin").read_bytes() == b"payload"
        assert tree.get(duplicate.uid) is duplicate
    finally:
        provider.close()


def test_copy_directory_copies_only_modeled_subtree(tmp_path):
    physical = tmp_path / "root"
    (physical / "source" / "nested").mkdir(parents=True)
    (physical / "source" / "nested" / "data.txt").write_text("hello")
    (physical / "destination").mkdir()
    root = Directory("root")
    source = Directory("source", parent=root)
    nested = Directory("nested", parent=source)
    File("data", extension="txt", parent=nested)
    destination = Directory("destination", parent=root)
    tree = FSResourceTree(roots=[root])
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        duplicate = copy(source, destination, provider=provider)
        assert isinstance(duplicate, Directory)
        assert duplicate.uid != source.uid
        assert isinstance(duplicate.find("nested"), Directory)
        assert (physical / "destination" / "source" / "nested" / "data.txt").read_text() == "hello"
        assert tree.get(duplicate.uid) is duplicate
    finally:
        provider.close()


def test_copy_refuses_existing_destination_without_overwrite(tmp_path):
    physical = tmp_path / "root"
    physical.mkdir()
    (physical / "source.txt").touch()
    (physical / "target.txt").touch()
    root = Directory("root")
    source = File("source", extension="txt", parent=root)
    File("target", extension="txt", parent=root)
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        with pytest.raises(FileExistsError):
            copy(source, root, provider=provider, new_name="target")
    finally:
        provider.close()


def test_move_refuses_descendant_and_root(tmp_path):
    physical = tmp_path / "root"
    (physical / "parent" / "child").mkdir(parents=True)
    root = Directory("root")
    parent = Directory("parent", parent=root)
    child = Directory("child", parent=parent)
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        with pytest.raises(ValueError, match="descendants"):
            move(parent, child, provider=provider)
        with pytest.raises(PermissionError):
            rename(root, "other", provider=provider)
    finally:
        provider.close()


def test_copy_does_not_remove_preexisting_physical_directory_on_conflict(tmp_path):
    physical = tmp_path / "root"
    (physical / "source").mkdir(parents=True)
    (physical / "destination" / "source").mkdir(parents=True)
    (physical / "destination" / "source" / "keep.txt").write_text("keep")
    root = Directory("root")
    source = Directory("source", parent=root)
    destination = Directory("destination", parent=root)
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        with pytest.raises(FileExistsError):
            copy(source, destination, provider=provider)
        assert (physical / "destination" / "source" / "keep.txt").read_text() == "keep"
        assert destination.find("source") is None
    finally:
        provider.close()


def test_copy_rejects_directory_into_its_descendant(tmp_path):
    physical = tmp_path / "root"
    (physical / "source" / "nested").mkdir(parents=True)
    root = Directory("root")
    source = Directory("source", parent=root)
    nested = Directory("nested", parent=source)
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        with pytest.raises(ValueError, match="descendants"):
            copy(source, nested, provider=provider)
    finally:
        provider.close()
