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


def test_filesystem_tree_add_roots_is_atomic_when_a_root_is_invalid():
    tree = FSResourceTree()
    valid_root = Directory("valid")
    invalid_root = File("not-a-directory")

    with pytest.raises(TypeError, match="roots must be Directory"):
        tree.add_roots([valid_root, invalid_root])

    assert tree.roots == ()
    assert len(tree) == 0
    assert valid_root.tree is None
    assert invalid_root.tree is None


def test_filesystem_tree_rejects_duplicate_uids_without_partial_registration():
    tree = FSResourceTree()
    first = Directory("first", uid="duplicate")
    second = Directory("second", uid="duplicate")

    with pytest.raises(ValueError, match="duplicate resource uid"):
        tree.add_roots([first, second])

    assert tree.roots == ()
    assert len(tree) == 0
    assert first.tree is None
    assert second.tree is None


def test_managed_directory_rejects_generic_children_without_index_mutation():
    root = Directory("root")
    tree = FSResourceTree(roots=[root])
    invalid = resourcetree.Asset("generic")

    with pytest.raises(TypeError, match="only Directory or File"):
        root.append_child(invalid)

    assert root.children == ()
    assert invalid.parent is None
    assert invalid.tree is None
    assert len(tree) == 1


def test_root_registration_rejects_corrupted_generic_descendants_atomically():
    tree = FSResourceTree()
    root = Directory("root")
    invalid = resourcetree.Asset("not-a-file")
    root._children.append(invalid)
    invalid._parent = root

    with pytest.raises(TypeError, match="only Directory or File"):
        tree.add_root(root)

    assert tree.roots == ()
    assert len(tree) == 0
    assert root.tree is None
    assert invalid.tree is None


def test_child_registration_rejects_corrupted_descendants_atomically():
    root = Directory("root")
    tree = FSResourceTree(roots=[root])
    branch = Directory("branch")
    invalid = resourcetree.Asset("not-a-file")
    branch._children.append(invalid)
    invalid._parent = branch

    with pytest.raises(TypeError, match="only Directory or File"):
        tree.register(branch, parent=root)

    assert root.children == ()
    assert branch.parent is None
    assert branch.tree is None
    assert invalid.tree is None
    assert len(tree) == 1


def test_mount_rejects_corrupted_source_without_partial_transfer():
    destination_root = Directory("destination")
    destination = FSResourceTree(roots=[destination_root])
    source_root = Directory("source")
    source = FSResourceTree(roots=[source_root])
    invalid = resourcetree.Asset("not-a-file")
    source_root._children.append(invalid)
    invalid._parent = source_root

    with pytest.raises(TypeError, match="only Directory or File"):
        destination.mount(destination_root, source)

    assert destination_root.children == ()
    assert source.roots == (source_root,)
    assert source.get(source_root.uid) is source_root
    assert source.get(invalid.uid) is None
    assert source_root.tree is source
    assert invalid.tree is None
    assert len(destination) == 1
    assert len(source) == 1


def test_remove_detaches_subtree_and_clears_derived_membership():
    root = Directory("root")
    branch = Directory("branch", parent=root)
    item = File("item", parent=branch)
    tree = FSResourceTree(roots=[root])

    assert tree.remove(branch) is True
    assert root.children == ()
    assert branch.parent is None
    assert branch.tree is None
    assert item.tree is None
    assert tree.get(branch.uid) is None
    assert tree.get(item.uid) is None
    assert len(tree) == 1


def test_remove_root_detaches_entire_subtree_and_clears_index():
    root = Directory("root")
    item = File("item", parent=root)
    tree = FSResourceTree(roots=[root])

    assert tree.remove_root(root) is True
    assert tree.roots == ()
    assert root.parent is None
    assert root.tree is None
    assert item.tree is None
    assert tree.get(root.uid) is None
    assert tree.get(item.uid) is None
    assert len(tree) == 0
