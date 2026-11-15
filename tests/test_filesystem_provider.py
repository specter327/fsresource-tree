from pathlib import Path

import pytest

from fsresource_tree import Directory, File
from fsresource_tree.providers import FilesystemProvider
from fsresource_tree.operations import create, delete, exists, path, walk


def test_provider_maps_logical_root_to_existing_directory(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    model = Directory("logical-root")
    folder = Directory("docs", parent=model)
    item = File("report", extension="txt", parent=folder)
    provider = FilesystemProvider(root, resource_root=model)

    assert path(model) == Path(".")
    assert provider.resolve(item) == root / "docs" / "report.txt"
    create(model, provider=provider, recursive_children=True)
    assert exists(folder, provider=provider)
    assert exists(item, provider=provider)


def test_provider_rejects_traversal_components(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    model = Directory("root")
    outside = Directory("..", parent=model)
    provider = FilesystemProvider(root, resource_root=model)

    with pytest.raises(ValueError):
        provider.resolve(outside)


def test_provider_rejects_symlink_ancestor(tmp_path):
    root = tmp_path / "sandbox"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (root / "escape").symlink_to(outside, target_is_directory=True)
    model = Directory("root")
    linked = Directory("escape", parent=model)
    child = File("secret", parent=linked)
    provider = FilesystemProvider(root, resource_root=model)

    with pytest.raises(ValueError, match="symbolic links"):
        provider.resolve(child)


def test_provider_never_deletes_its_root(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    model = Directory("root")
    provider = FilesystemProvider(root, resource_root=model)

    with pytest.raises(PermissionError):
        provider.delete(model)
    with pytest.raises(PermissionError):
        provider.purge(model)
    assert root.is_dir()


def test_recursive_delete_only_removes_modeled_children(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    model = Directory("root")
    folder = Directory("docs", parent=model)
    item = File("report", extension="txt", parent=folder)
    provider = FilesystemProvider(root, resource_root=model)
    create(model, provider=provider, recursive_children=True)

    (root / "docs" / "untracked").write_text("keep")
    with pytest.raises(OSError):
        delete(folder, provider=provider, recursive_children=True)
    assert (root / "docs" / "untracked").exists()
    assert (root / "docs" / "report.txt").exists()


def test_purge_refuses_symlinks_and_does_not_follow_them(tmp_path):
    root = tmp_path / "sandbox"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    protected = outside / "keep.txt"
    protected.write_text("protected")
    model = Directory("root")
    folder = Directory("docs", parent=model)
    provider = FilesystemProvider(root, resource_root=model)
    create(folder, provider=provider)
    (root / "docs" / "escape").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ValueError, match="symbolic links"):
        provider.purge(folder)
    assert protected.read_text() == "protected"


def test_walk_is_iterative_for_deep_hierarchies():
    root = Directory("root")
    current = root
    for index in range(1500):
        current = Directory(f"d{index}", parent=current)
    assert sum(1 for _ in walk(root)) == 1501
    assert sum(1 for _ in walk(root, inverse=True)) == 1501

def test_provider_rejects_resources_from_another_logical_root(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    bound = Directory("bound")
    foreign = Directory("foreign")
    provider = FilesystemProvider(root, resource_root=bound)

    with pytest.raises(ValueError, match="logical root"):
        provider.resolve(foreign)

@pytest.mark.parametrize("name", ["C:", "CON", "NUL.txt", "trailing.", "trailing "])
def test_provider_rejects_nonportable_path_components(tmp_path, name):
    root = tmp_path / "sandbox"
    root.mkdir()
    model = Directory("root")
    invalid = Directory(name, parent=model)
    provider = FilesystemProvider(root, resource_root=model)

    with pytest.raises(ValueError):
        provider.resolve(invalid)


@pytest.mark.skipif(__import__("os").name != "posix", reason="descriptor-relative provider is POSIX-specific")
def test_posix_provider_uses_a_pinned_directory_descriptor(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    model = Directory("root")
    provider = FilesystemProvider(root, resource_root=model)
    try:
        assert provider.race_resistant
        item = File("payload", extension="bin", parent=model)
        provider.create(item)
        assert provider.exists(item)
        assert provider.delete(item)
    finally:
        provider.close()


@pytest.mark.skipif(__import__("os").name != "posix", reason="descriptor-relative provider is POSIX-specific")
def test_posix_create_refuses_a_symlink_at_the_final_component(tmp_path):
    root = tmp_path / "sandbox"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.write_text("protected")
    model = Directory("root")
    item = File("payload", parent=model)
    provider = FilesystemProvider(root, resource_root=model)
    try:
        (root / "payload").symlink_to(outside)
        with pytest.raises((FileExistsError, ValueError)):
            provider.create(item)
        assert outside.read_text() == "protected"
    finally:
        provider.close()


@pytest.mark.skipif(__import__("os").name != "posix", reason="descriptor-relative provider is POSIX-specific")
def test_posix_delete_refuses_a_symlink_at_the_final_component(tmp_path):
    root = tmp_path / "sandbox"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.write_text("protected")
    model = Directory("root")
    item = File("payload", parent=model)
    provider = FilesystemProvider(root, resource_root=model)
    try:
        (root / "payload").symlink_to(outside)
        with pytest.raises(ValueError, match="symbolic link"):
            provider.delete(item)
        assert outside.read_text() == "protected"
    finally:
        provider.close()


def test_provider_context_manager_releases_its_root_descriptor(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    model = Directory("root")
    provider = FilesystemProvider(root, resource_root=model)
    if provider.race_resistant:
        descriptor = provider._root_fd
        with provider:
            assert provider._root_fd == descriptor
        assert provider._root_fd is None
