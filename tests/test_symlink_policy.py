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
