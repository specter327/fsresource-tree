import pytest
import resourcetree

from fsresource_tree import Directory, File, FSResourceTree


@pytest.mark.parametrize("resource_type", [File, Directory])
def test_filesystem_resources_reject_generic_container_parents(resource_type):
    generic_parent = resourcetree.Container("generic")

    with pytest.raises(TypeError, match="parent must be a Directory"):
        resource_type("child", parent=generic_parent)


def test_filesystem_hierarchy_can_exist_without_a_resource_tree():
    root = Directory("root")
    nested = Directory("nested", parent=root)
    file = File("report", extension="txt", parent=nested)

    assert root.tree is None
    assert nested.tree is None
    assert file.tree is None
    assert root.children == (nested,)
    assert nested.parent is root
    assert nested.children == (file,)
    assert file.parent is nested


def test_registering_existing_filesystem_hierarchy_indexes_every_resource():
    root = Directory("root")
    nested = Directory("nested", parent=root)
    file = File("report", extension="txt", parent=nested)

    tree = FSResourceTree(roots=[root])

    assert len(tree) == 3
    assert tree.roots == (root,)
    assert tree.get(root.uid) is root
    assert tree.get(nested.uid) is nested
    assert tree.get(file.uid) is file
    assert all(resource.tree is tree for resource in (root, nested, file))


def test_directory_rejects_invalid_attachment_without_mutating_hierarchy():
    root = Directory("root")
    invalid = resourcetree.Asset("generic")

    with pytest.raises(TypeError, match="only Directory or File"):
        root.append_child(invalid)

    assert root.children == ()
    assert invalid.parent is None
    assert invalid.tree is None


def test_file_remains_a_terminal_resource():
    file = File("report", extension="txt")

    assert not isinstance(file, resourcetree.Container)
    assert not hasattr(file, "append_child")
    assert not hasattr(file, "children")
