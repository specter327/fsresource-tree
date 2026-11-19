import pytest

from fsresourcetree import Directory, File, FormatTypes, SymbolicLink, extensions_for
from fsresourcetree.operations import filter_tree, find


def make_tree():
    root = Directory("root")
    photos = Directory("photos", parent=root)
    File("one", extension="JPG", parent=photos)
    File("two", extension="png", parent=photos)
    File("notes", extension="txt", parent=photos)
    docs = Directory("docs", parent=root)
    File("report", extension="PDF", parent=docs)
    File("movie", extension="mp4", parent=root)
    return root, photos, docs


def test_format_find_returns_flat_matching_files_case_insensitively():
    root, _, _ = make_tree()
    results = find(root, format=(FormatTypes.IMAGE,))
    assert [item.filename() for item in results] == ["one.JPG", "two.png"]


def test_format_find_supports_multiple_categories_and_explicit_extensions():
    root, _, _ = make_tree()
    results = find(root, format=(FormatTypes.IMAGE, FormatTypes.DOCUMENT))
    assert [item.filename() for item in results] == ["one.JPG", "two.png", "notes.txt", "report.PDF"]
    assert [item.filename() for item in find(root, extensions=("MP4",))] == ["movie.mp4"]


def test_format_find_keeps_legacy_exact_name_behavior():
    root, photos, _ = make_tree()
    assert find(root, "photos") is photos
    assert find(root, "missing") is None
    with pytest.raises(TypeError, match="target must be a string"):
        find(root, None)


def test_format_find_validates_filters():
    root, _, _ = make_tree()
    with pytest.raises(ValueError, match="provide target"):
        find(root)
    with pytest.raises(TypeError, match="FormatTypes"):
        find(root, format=("image",))
    with pytest.raises(ValueError, match="cannot be combined"):
        find(root, "photos", format=FormatTypes.IMAGE)


def test_filter_tree_preserves_only_matching_files_and_ancestors():
    root, _, _ = make_tree()
    filtered = filter_tree(root, format=FormatTypes.IMAGE)
    assert filtered is not root
    assert filtered.name == "root"
    assert [node.filename() for node in find(filtered, format=FormatTypes.IMAGE)] == ["one.JPG", "two.png"]
    assert [child.name for child in filtered.children] == ["photos"]
    assert [child.filename() for child in filtered.children[0].children] == ["one.JPG", "two.png"]
    assert len(root.children) == 3


def test_filter_tree_keeps_empty_root_and_omits_symbolic_links():
    root = Directory("root")
    SymbolicLink("link", target="outside.jpg", parent=root)
    filtered = filter_tree(root, extensions=(".jpg",))
    assert filtered.name == "root"
    assert filtered.children == ()


def test_format_registry_is_available_and_has_expected_members():
    assert ".jpeg" in extensions_for(FormatTypes.IMAGE)
    assert ".wav" in extensions_for(FormatTypes.AUDIO)
