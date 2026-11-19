from __future__ import annotations

import pytest

from fsresourcetree import Directory, resource_from_path


def _symlink_or_skip(link, target, *, target_is_directory=False):
    try:
        link.symlink_to(target, target_is_directory=target_is_directory)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"symbolic links are unavailable in this environment: {error}")


def test_resource_from_path_rejects_root_symlink_by_default(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "alias"
    _symlink_or_skip(link, target, target_is_directory=True)

    with pytest.raises(ValueError, match="symbolic links"):
        resource_from_path(link)


def test_resource_from_path_can_explicitly_resolve_root_symlink(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "item.txt").write_text("content")
    link = tmp_path / "alias"
    _symlink_or_skip(link, target, target_is_directory=True)

    root = resource_from_path(link, follow_symlinks=True)
    try:
        assert isinstance(root, Directory)
        assert root.name == "target"
        result = root.scan(recursive=True)
        assert result.count == 1
        assert root.children[0].filename() == "item.txt"
    finally:
        root.close_provider()


def test_scan_skips_descendant_symlinks_by_default(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    (target / "inside.txt").write_text("content")
    root_path = tmp_path / "root"
    root_path.mkdir()
    (root_path / "visible.txt").write_text("content")
    _symlink_or_skip(root_path / "linked", target, target_is_directory=True)

    root = resource_from_path(root_path)
    try:
        result = root.scan(recursive=True)
        assert {child.filename() for child in root.children if hasattr(child, "filename")} == {
            "visible.txt"
        }
        assert any("symbolic link" in reason for _, reason in result.skipped)
    finally:
        root.close_provider()


def test_scan_can_reject_descendant_symlinks_explicitly(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    root_path = tmp_path / "root"
    root_path.mkdir()
    _symlink_or_skip(root_path / "linked", target, target_is_directory=True)

    root = resource_from_path(root_path)
    try:
        with pytest.raises(ValueError, match="symbolic link"):
            root.scan(recursive=True, symlink_policy="raise", on_error="skip")
    finally:
        root.close_provider()


def test_symlink_policy_rejects_unknown_values(tmp_path):
    root_path = tmp_path / "root"
    root_path.mkdir()
    root = resource_from_path(root_path)
    try:
        with pytest.raises(ValueError, match="symlink_policy"):
            root.scan(symlink_policy="follow")
    finally:
        root.close_provider()

def test_follow_symlinks_is_only_valid_for_selected_root(tmp_path):
    from fsresourcetree import Directory

    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "alias"
    _symlink_or_skip(link, target, target_is_directory=True)

    with pytest.raises(ValueError, match="selected root"):
        resource_from_path(
            link,
            parent=Directory(name="parent"),
            follow_symlinks=True,
        )

def test_symlink_raise_policy_preserves_on_error_skip_for_callback_errors(tmp_path):
    root_path = tmp_path / "root"
    root_path.mkdir()
    (root_path / "item.txt").write_text("content")

    root = resource_from_path(root_path)
    try:
        def reject_entry(name, is_directory):
            raise ValueError("callback rejected entry")

        result = root.scan(
            recursive=True,
            exclude=reject_entry,
            symlink_policy="raise",
            on_error="skip",
        )
        assert result.count == 0
        assert result.skipped == ((str(root_path / "item.txt"), "callback rejected entry"),)
    finally:
        root.close_provider()

def test_scan_accepts_symbolic_links_without_traversing_targets(tmp_path):
    from fsresourcetree import SymbolicLink

    target = tmp_path / "target"
    target.mkdir()
    (target / "secret.txt").write_text("content")
    root_path = tmp_path / "root"
    root_path.mkdir()
    link = root_path / "alias"
    _symlink_or_skip(link, target, target_is_directory=True)

    root = resource_from_path(root_path)
    try:
        result = root.scan(recursive=True, symlink_policy="accept")
        accepted = [child for child in root.children if isinstance(child, SymbolicLink)]
        assert len(accepted) == 1
        assert accepted[0].name == "alias"
        assert accepted[0].target == str(target)
        assert result.count == 1
        assert not any(child.name == "secret.txt" for child in root.children)
    finally:
        root.close_provider()


def test_symbolic_link_resource_round_trips_through_model(tmp_path):
    from fsresourcetree import SymbolicLink

    target = tmp_path / "target.txt"
    target.write_text("content")
    root_path = tmp_path / "root"
    root_path.mkdir()
    _symlink_or_skip(root_path / "alias.txt", target)

    root = resource_from_path(root_path)
    try:
        root.scan(symlink_policy="accept")
        payload = root.to_dict()
        restored = Directory.from_dict(payload)
        links = [child for child in restored.children if isinstance(child, SymbolicLink)]
        assert len(links) == 1
        assert links[0].target == str(target)
    finally:
        root.close_provider()

def test_windows_symlink_target_normalization():
    from fsresourcetree.operations.scan import _normalize_symlink_target

    assert _normalize_symlink_target(
        r"\\?\C:\folder\target", windows=True
    ) == r"C:\folder\target"
    assert _normalize_symlink_target(
        r"\\?\UNC\server\share\target", windows=True
    ) == r"\\server\share\target"
    device_path = r"\\?\Volume{01234567-89ab-cdef-0123-456789abcdef}\target"
    assert _normalize_symlink_target(device_path, windows=True) == device_path
    assert _normalize_symlink_target(r"\\?\C:\folder\target", windows=False) == r"\\?\C:\folder\target"



def test_scan_uses_provider_enumeration_instead_of_path_scandir(tmp_path, monkeypatch):
    root_path = tmp_path / "root"
    root_path.mkdir()
    (root_path / "nested").mkdir()
    (root_path / "nested" / "item.txt").write_text("content")

    root = resource_from_path(root_path)
    try:
        def forbidden_scandir(*args, **kwargs):
            raise AssertionError("scan must enumerate through the provider")

        monkeypatch.setattr("os.scandir", forbidden_scandir)
        result = root.scan(recursive=True)
        assert result.count == 2
        assert any(isinstance(child, Directory) and child.name == "nested" for child in root.children)
    finally:
        root.close_provider()
