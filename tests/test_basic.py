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


def test_file_filename():
    file = fs.File("report", extension="txt")
    assert file.filename() == "report.txt"


def test_resource_tree_alias_is_compatible():
    assert fs.ResourceTree is fs.FSResourceTree
