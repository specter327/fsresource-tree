import pytest
import resourcetree

import fsresource_tree as fs


def test_filesystem_models_inherit_generic_core():
    assert issubclass(fs.File, resourcetree.Asset)
    assert issubclass(fs.Directory, resourcetree.Container)
    assert issubclass(fs.FSResourceTree, resourcetree.ResourceTree)


def test_filesystem_tree_registers_specialized_resources():
    tree = fs.FSResourceTree(name="System")
    root = fs.Directory("/")
    file = fs.File(name="hello", extension="txt")

    tree.register(root)
    tree.register(file, parent=root)

    assert file.parent is root
    assert tree.get(file.uid) is file
    assert isinstance(file, resourcetree.Asset)
    assert isinstance(root, resourcetree.Container)


def test_filesystem_tree_uses_explicit_roots_collection():
    root = fs.Directory("/")
    tree = fs.FSResourceTree(roots=[root])
    assert tree.roots == (root,)
    assert not hasattr(tree, "root")


def test_filesystem_tree_rejects_non_directory_roots():
    with pytest.raises(TypeError, match="roots must be Directory"):
        fs.FSResourceTree(roots=[fs.File("standalone")])

    generic_root = resourcetree.Container("generic")
    with pytest.raises(TypeError, match="only Directory or File"):
        fs.FSResourceTree(roots=[fs.Directory("valid", parent=None), generic_root])


def test_directory_rejects_generic_resources():
    root = fs.Directory("/")
    with pytest.raises(TypeError, match="only Directory or File"):
        root.append_child(resourcetree.Asset("not-a-file"))


def test_filesystem_tree_rejects_generic_tree_mounts():
    target_root = fs.Directory("target")
    target = fs.FSResourceTree(roots=[target_root])
    generic = resourcetree.ResourceTree(roots=[resourcetree.Container("generic")])

    with pytest.raises(TypeError, match="only an FSResourceTree"):
        target.mount(target_root, generic)


def test_file_filename():
    file = fs.File("report", extension="txt")
    assert file.filename() == "report.txt"


def test_filesystem_package_does_not_export_generic_tree_alias():
    assert not hasattr(fs, "ResourceTree")
