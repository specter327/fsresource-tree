from pathlib import PurePath

import pytest

from fsresourcetree import Directory, File
from fsresourcetree.operations import ancestors, find, path, walk


def test_walk_uses_depth_first_preorder_and_postorder():
    root = Directory("root")
    first = Directory("first", parent=root)
    File("one", parent=first)
    second = Directory("second", parent=root)
    File("two", parent=second)

    assert [node.name for node in walk(root)] == [
        "root", "first", "one", "second", "two"
    ]
    assert [node.name for node in walk(root, inverse=True)] == [
        "one", "first", "two", "second", "root"
    ]


def test_walk_is_iterative_for_deep_hierarchies():
    root = Directory("root")
    current = root
    for index in range(1500):
        current = Directory(f"d{index}", parent=current)

    assert sum(1 for _ in walk(root)) == 1501
    assert sum(1 for _ in walk(root, inverse=True)) == 1501


def test_walk_rejects_non_filesystem_children():
    root = Directory("root")
    root._children.append(object())

    with pytest.raises(TypeError, match="only Directory, File or SymbolicLink"):
        list(walk(root))


def test_walk_rejects_inconsistent_parent_child_links():
    root = Directory("root")
    child = Directory("child")
    root._children.append(child)

    with pytest.raises(ValueError, match="inconsistent parent/child"):
        list(walk(root))


def test_walk_rejects_cycles():
    root = Directory("root")
    child = Directory("child", parent=root)
    child._children.append(root)
    root._parent = child

    with pytest.raises(ValueError, match="cycle or duplicate"):
        list(walk(root))


def test_ancestors_supports_order_and_excluding_self():
    root = Directory("root")
    nested = Directory("nested", parent=root)
    item = File("report", extension="txt", parent=nested)

    assert list(ancestors(item)) == [root, nested, item]
    assert list(ancestors(item, inverse=True)) == [item, nested, root]
    assert list(ancestors(item, include_self=False)) == [root, nested]
    assert list(ancestors(item, include_self=False, inverse=True)) == [nested, root]
    assert list(ancestors(root, include_self=False)) == []


def test_ancestors_rejects_invalid_resources_and_flags():
    with pytest.raises(TypeError, match="resource must be"):
        list(ancestors(object()))
    with pytest.raises(TypeError, match="include_self"):
        list(ancestors(Directory("root"), include_self=1))
    with pytest.raises(TypeError, match="inverse"):
        list(ancestors(Directory("root"), inverse=1))


def test_ancestors_rejects_parent_cycles_and_inconsistent_links():
    root = Directory("root")
    child = Directory("child", parent=root)
    child._children.append(root)
    root._parent = child

    with pytest.raises(ValueError, match="cycle"):
        list(ancestors(root))

    detached_root = Directory("detached")
    orphan = File("orphan")
    orphan._parent = detached_root
    with pytest.raises(ValueError, match="inconsistent parent/child"):
        list(ancestors(orphan))


def test_path_is_logical_and_uses_file_filename():
    root = Directory("logical-root")
    nested = Directory("documents", parent=root)
    item = File("report", extension="txt", parent=nested)

    assert path(root) == PurePath(".")
    assert path(nested) == PurePath("documents")
    assert path(item) == PurePath("documents", "report.txt")


def test_path_rejects_file_roots_and_invalid_resources():
    with pytest.raises(TypeError, match="Directory root"):
        path(File("standalone"))
    with pytest.raises(TypeError, match="resource must be"):
        path(object())


def test_path_rejects_cycles_and_inconsistent_parent_links():
    root = Directory("root")
    child = Directory("child", parent=root)
    child._children.append(root)
    root._parent = child

    with pytest.raises(ValueError, match="cycle"):
        path(root)

    parent = Directory("parent")
    orphan = File("orphan")
    orphan._parent = parent
    with pytest.raises(ValueError, match="inconsistent parent/child"):
        path(orphan)


def test_find_returns_first_top_down_exact_name_match():
    root = Directory("root")
    first = Directory("match", parent=root)
    File("match", extension="txt", parent=first)

    assert find(root, "match") is first
    assert find(root, "missing") is None
    assert find(first, "match") is first
    assert find(File("standalone"), "standalone").name == "standalone"


def test_find_rejects_invalid_arguments():
    with pytest.raises(TypeError, match="resource must be"):
        find(object(), "target")
    with pytest.raises(TypeError, match="target must be"):
        find(Directory("root"), None)


def test_walk_validates_the_starting_resources_parent_link():
    parent = Directory("parent")
    child = Directory("child")
    child._parent = parent

    with pytest.raises(ValueError, match="inconsistent parent/child"):
        list(walk(child))


def test_ancestors_validates_parent_link_when_excluding_self():
    parent = Directory("parent")
    child = File("child")
    child._parent = parent

    with pytest.raises(ValueError, match="inconsistent parent/child"):
        list(ancestors(child, include_self=False))
