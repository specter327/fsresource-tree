import stat
from pathlib import Path
from types import SimpleNamespace

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


@pytest.mark.skipif(__import__("os").name != "posix", reason="descriptor-relative provider is POSIX-specific")
def test_closed_descriptor_provider_fails_closed(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    model = Directory("root")
    item = File("payload", parent=model)
    provider = FilesystemProvider(root, resource_root=model)
    provider.close()

    with pytest.raises(RuntimeError, match="closed"):
        provider.exists(item)


@pytest.mark.skipif(__import__("os").name != "posix", reason="descriptor-relative provider is POSIX-specific")
def test_posix_create_refuses_symlinked_parent_directory(tmp_path):
    root = tmp_path / "sandbox"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    model = Directory("root")
    linked = Directory("linked", parent=model)
    item = File("payload", parent=linked)
    provider = FilesystemProvider(root, resource_root=model)
    try:
        (root / "linked").symlink_to(outside, target_is_directory=True)
        with pytest.raises(OSError):
            provider.create(item)
        assert not (outside / "payload").exists()
    finally:
        provider.close()


def test_purge_removes_nested_unmodeled_contents_without_touching_siblings(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    model = Directory("root")
    folder = Directory("docs", parent=model)
    nested = Directory("nested", parent=folder)
    item = File("report", extension="txt", parent=nested)
    sibling = File("keep", extension="txt", parent=model)
    provider = FilesystemProvider(root, resource_root=model)
    try:
        create(model, provider=provider, recursive_children=True)
        (root / "docs" / "nested" / "untracked.bin").write_bytes(b"untracked")
        assert provider.purge(folder)
        assert not (root / "docs").exists()
        assert (root / "keep.txt").is_file()
        assert provider.exists(sibling)
    finally:
        provider.close()


@pytest.mark.skipif(__import__("os").name != "posix", reason="descriptor-relative provider is POSIX-specific")
def test_posix_create_blocks_symlink_inserted_after_parent_resolution(tmp_path, monkeypatch):
    root = tmp_path / "sandbox"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.write_text("protected")
    model = Directory("root")
    item = File("payload", parent=model)
    provider = FilesystemProvider(root, resource_root=model)
    original_open_parent = provider._open_parent_fd

    def insert_symlink(relative):
        parent_fd, name = original_open_parent(relative)
        (root / name).symlink_to(outside)
        return parent_fd, name

    monkeypatch.setattr(provider, "_open_parent_fd", insert_symlink)
    try:
        with pytest.raises((FileExistsError, ValueError)):
            provider.create(item)
        assert outside.read_text() == "protected"
    finally:
        provider.close()



@pytest.mark.parametrize("operation", ["create", "delete", "purge"])
def test_path_based_operations_reject_symlinked_ancestors(tmp_path, monkeypatch, operation):
    root = tmp_path / "sandbox"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    protected = outside / "secret"
    protected.write_text("protected")
    model = Directory("root")
    linked = Directory("linked", parent=model)
    provider = FilesystemProvider(root, resource_root=model)

    # Exercise the Windows-style path-based fallback on every CI platform.
    monkeypatch.setattr(provider, "_descriptor_mode", False)
    (root / "linked").symlink_to(outside, target_is_directory=True)

    try:
        if operation == "create":
            resource = File("created", parent=linked)
            with pytest.raises(ValueError, match="symbolic links and reparse points"):
                provider.create(resource)
            assert not (outside / "created").exists()
        elif operation == "delete":
            resource = File("secret", parent=linked)
            with pytest.raises(ValueError, match="symbolic links and reparse points"):
                provider.delete(resource)
            assert protected.read_text() == "protected"
        else:
            with pytest.raises(ValueError, match="symbolic links and reparse points"):
                provider.purge(linked)
            assert protected.read_text() == "protected"
    finally:
        provider.close()


@pytest.mark.parametrize("operation", ["create", "delete", "purge"])
def test_path_based_operations_reject_reparse_point_ancestors(
    tmp_path, monkeypatch, operation
):
    root = tmp_path / "sandbox"
    root.mkdir()
    physical_parent = root / "parent"
    physical_parent.mkdir()
    model = Directory("root")
    parent = Directory("parent", parent=model)
    provider = FilesystemProvider(root, resource_root=model)
    # Force the path-based implementation so this regression also exercises
    # the Windows fallback on POSIX CI hosts.
    provider._descriptor_mode = False

    if operation == "purge":
        target = Directory("target", parent=parent)
        (physical_parent / "target").mkdir()
    else:
        target = File("payload", parent=parent)
        if operation == "delete":
            (physical_parent / "payload").write_text("protected", encoding="utf-8")

    original_lstat = Path.lstat
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

    def fake_lstat(path):
        if path == physical_parent:
            return SimpleNamespace(
                st_mode=stat.S_IFDIR | 0o755,
                st_file_attributes=reparse_flag,
            )
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", fake_lstat)

    with pytest.raises(ValueError, match="reparse points"):
        if operation == "create":
            provider.create(target)
        elif operation == "delete":
            provider.delete(target)
        else:
            provider.purge(target)

    if operation == "create":
        assert not (physical_parent / "payload").exists()
    elif operation == "delete":
        assert (physical_parent / "payload").read_text(encoding="utf-8") == "protected"
    else:
        assert (physical_parent / "target").is_dir()
