from fsresourcetree import Directory, FSResourceTree, File, FilesystemProvider
from fsresourcetree.operations import scan, walk


def test_filesystem_objects_expose_consistent_walk_methods():
    root = Directory("root")
    branch = Directory("branch", parent=root)
    leaf = File("leaf", extension="txt", parent=branch)

    assert list(root.walk()) == [root, branch, leaf]
    assert list(root.walk(order="post")) == [leaf, branch, root]
    assert list(branch.walk(order="post")) == [leaf, branch]
    assert list(leaf.walk()) == [leaf]
    assert list(walk(root, order="post")) == [leaf, branch, root]


def test_filesystem_tree_walks_all_roots_in_postorder():
    first = Directory("first")
    first_child = File("one", parent=first)
    second = Directory("second")
    second_child = File("two", parent=second)
    tree = FSResourceTree(roots=[first, second])

    assert list(tree.walk()) == [first, first_child, second, second_child]
    assert list(tree.walk(order="post")) == [first_child, first, second_child, second]


def test_scan_result_exposes_walk_and_ancestor_navigation(tmp_path):
    physical = tmp_path / "root"
    (physical / "nested").mkdir(parents=True)
    (physical / "nested" / "item.txt").touch()
    root = Directory("root")
    tree = FSResourceTree(roots=[root])
    provider = FilesystemProvider(physical, resource_root=root)
    try:
        result = scan(root, provider=provider)
        assert [item.name for item in result.walk()] == ["root", "nested", "item"]
        assert list(result.walk(order="post"))[-1] is root
        assert list(result.ancestors()) == []
    finally:
        provider.close()
