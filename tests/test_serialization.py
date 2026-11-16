from datetime import datetime, timezone

import pytest

from fsresource_tree import Directory, File, FSResourceTree


def make_tree():
    root = Directory("/", uid="root", metadata={"volume": "system"})
    documents = Directory("documents", parent=root, uid="documents")
    file = File(
        "report",
        extension="json",
        parent=documents,
        uid="report",
        metadata={"verified": True},
        data={"records": [1, 2, 3]},
    )
    root.created_at = datetime(2024, 1, 2, 3, 4, tzinfo=timezone.utc)
    root.updated_at = datetime(2024, 2, 3, 4, 5, tzinfo=timezone.utc)
    tree = FSResourceTree(roots=[root], name="system", uid="tree")
    return tree, file


def assert_restored(tree):
    assert isinstance(tree, FSResourceTree)
    assert tree.uid == "tree"
    assert tree.name == "system"
    assert len(tree.roots) == 1
    root = tree.roots[0]
    assert isinstance(root, Directory)
    assert root.uid == "root"
    assert root.metadata == {"volume": "system"}
    assert root.created_at == datetime(2024, 1, 2, 3, 4, tzinfo=timezone.utc)
    assert root.updated_at == datetime(2024, 2, 3, 4, 5, tzinfo=timezone.utc)

    documents = root.children[0]
    assert isinstance(documents, Directory)
    assert documents.parent is root
    file = documents.children[0]
    assert isinstance(file, File)
    assert file.parent is documents
    assert file.uid == "report"
    assert file.name == "report"
    assert file.extension == "json"
    assert file.filename() == "report.json"
    assert file.metadata == {"verified": True}
    assert file.data == {"records": [1, 2, 3]}
    assert tree.get(file.uid) is file
    assert file.tree is tree
    assert len(tree) == 3


def test_file_dictionary_roundtrip_preserves_specialized_fields():
    _, file = make_tree()
    restored = File.from_dict(file.to_dict())

    assert isinstance(restored, File)
    assert restored.uid == file.uid
    assert restored.extension == file.extension
    assert restored.data == file.data
    assert restored.metadata == file.metadata
    assert restored.created_at == file.created_at
    assert restored.updated_at == file.updated_at


def test_directory_dictionary_roundtrip_rebuilds_specialized_children():
    tree, _ = make_tree()
    restored = Directory.from_dict(tree.roots[0].to_dict())

    assert isinstance(restored.children[0], Directory)
    assert isinstance(restored.children[0].children[0], File)
    assert restored.children[0].children[0].extension == "json"


def test_filesystem_tree_dictionary_roundtrip_rebuilds_specialized_index():
    tree, _ = make_tree()
    restored = FSResourceTree.from_dict(tree.to_dict())
    assert_restored(restored)


@pytest.mark.parametrize("format_name", ["json", "xml"])
def test_filesystem_tree_format_roundtrip_preserves_specialized_model(format_name):
    tree, _ = make_tree()
    serialized = getattr(tree, f"to_{format_name}")()
    restored = getattr(FSResourceTree, f"from_{format_name}")(serialized)
    assert_restored(restored)


def test_generic_core_factory_does_not_reconstruct_filesystem_types():
    from resourcetree.serialization.model import resource_from_dict

    tree, _ = make_tree()
    with pytest.raises(ValueError, match="unknown resource type"):
        resource_from_dict(tree.roots[0].to_dict())


def test_filesystem_tree_rejects_unknown_serialized_resource_types():
    tree, _ = make_tree()
    data = tree.to_dict()
    data["roots"][0]["children"][0]["children"][0]["type"] = "asset"

    with pytest.raises(ValueError, match="unknown filesystem resource type"):
        FSResourceTree.from_dict(data)
