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


@pytest.mark.parametrize(
    ("mutation", "error", "message"),
    [
        (lambda data: data.pop("uid"), ValueError, "tree uid"),
        (lambda data: data.pop("name"), ValueError, "tree name"),
        (lambda data: data.update(roots={}), TypeError, "roots must be a list"),
        (lambda data: data.update(roots=[{"type": "file"}]), ValueError, "root resource type"),
        (
            lambda data: data["roots"][0].update(created_at="not-a-timestamp"),
            ValueError,
            "valid ISO-8601 timestamp",
        ),
        (
            lambda data: data["roots"][0].update(metadata=[]),
            TypeError,
            "metadata must be a dictionary",
        ),
        (
            lambda data: data["roots"][0].update(children={}),
            TypeError,
            "children must be a list",
        ),
        (
            lambda data: data["roots"][0]["children"][0].update(extension=42),
            TypeError,
            "extension must be a string",
        ),
    ],
)
def test_filesystem_tree_rejects_malformed_serialized_payloads(mutation, error, message):
    tree, _ = make_tree()
    data = tree.to_dict()
    mutation(data)

    with pytest.raises(error, match=message):
        FSResourceTree.from_dict(data)


def test_filesystem_tree_rejects_duplicate_uids_across_branches():
    tree, _ = make_tree()
    data = tree.to_dict()
    data["roots"][0]["children"][0]["children"][0]["uid"] = "root"

    with pytest.raises(ValueError, match="duplicate serialized resource uid"):
        FSResourceTree.from_dict(data)


def test_filesystem_tree_rejects_duplicate_uids_across_roots():
    tree = FSResourceTree(
        roots=[Directory("first", uid="first"), Directory("second", uid="second")]
    )
    data = tree.to_dict()
    data["roots"][1]["uid"] = data["roots"][0]["uid"]

    with pytest.raises(ValueError, match="duplicate serialized resource uid"):
        FSResourceTree.from_dict(data)


def test_filesystem_tree_rejects_cyclic_serialized_resource_mappings():
    tree, _ = make_tree()
    data = tree.to_dict()
    data["roots"][0]["children"].append(data["roots"][0])

    with pytest.raises(ValueError, match="cyclic or repeated"):
        FSResourceTree.from_dict(data)


def test_filesystem_tree_rejects_repeated_serialized_resource_mappings():
    tree, _ = make_tree()
    data = tree.to_dict()
    child = data["roots"][0]["children"][0]
    data["roots"][0]["children"].append(child)

    with pytest.raises(ValueError, match="cyclic or repeated"):
        FSResourceTree.from_dict(data)


def test_directory_from_dict_rejects_missing_children_and_malformed_timestamps():
    tree, _ = make_tree()
    data = tree.roots[0].to_dict()
    data.pop("children")

    with pytest.raises(TypeError, match="children must be a list"):
        Directory.from_dict(data)

    data = tree.roots[0].to_dict()
    data["updated_at"] = None
    with pytest.raises(ValueError, match="ISO-8601 string"):
        Directory.from_dict(data)


def test_file_from_dict_rejects_container_fields_and_invalid_metadata():
    _, file = make_tree()
    data = file.to_dict()
    data["children"] = []

    with pytest.raises(ValueError, match="cannot contain children"):
        File.from_dict(data)

    data = file.to_dict()
    data["metadata"] = "invalid"
    with pytest.raises(TypeError, match="metadata must be a dictionary"):
        File.from_dict(data)
