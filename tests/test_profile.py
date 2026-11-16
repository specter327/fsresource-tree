from datetime import timezone

import pytest

from fsresourcetree import Directory, File, PhysicalProfile
from fsresourcetree.providers import FilesystemProvider


def test_file_profile_returns_metadata_without_mutating_resource(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    physical = root / "report.txt"
    physical.write_bytes(b"sample")
    model = Directory("root")
    resource = File("report", extension="txt", parent=model)
    provider = FilesystemProvider(root, resource_root=model)

    observation = resource.profile(provider=provider)

    assert isinstance(observation, PhysicalProfile)
    assert observation.exists is True
    assert observation.entry_type == "file"
    assert observation.size == 6
    assert observation.last_modified_time.tzinfo == timezone.utc
    assert observation.observed_at.tzinfo == timezone.utc
    assert resource.physical_profile is None


def test_profile_cache_update_is_explicit(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "report").touch()
    model = Directory("root")
    resource = File("report", parent=model)
    provider = FilesystemProvider(root, resource_root=model)

    observation = resource.profile(provider=provider, update_cache=True)

    assert resource.physical_profile is observation


def test_profile_absence_is_distinct_from_query_failure(tmp_path, monkeypatch):
    root = tmp_path / "sandbox"
    root.mkdir()
    model = Directory("root")
    resource = File("missing", parent=model)
    provider = FilesystemProvider(root, resource_root=model)

    absent = resource.profile(provider=provider)
    assert absent.exists is False
    assert absent.entry_type is None
    assert absent.size is None

    def denied(relative):
        raise PermissionError("denied")

    if provider.race_resistant:
        monkeypatch.setattr(provider, "_stat_relative", denied)
    else:
        class DeniedPath:
            def lstat(self):
                raise PermissionError("denied")

        monkeypatch.setattr(provider, "resolve", lambda *args, **kwargs: DeniedPath())

    with pytest.raises(PermissionError, match="denied"):
        resource.profile(provider=provider)


def test_profile_rejects_resource_type_mismatch(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "file").touch()
    model = Directory("root")
    resource = Directory("file", parent=model)
    provider = FilesystemProvider(root, resource_root=model)

    with pytest.raises(NotADirectoryError):
        resource.profile(provider=provider)


def test_directory_profile_reports_directory_metadata(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    (root / "folder").mkdir()
    model = Directory("root")
    resource = Directory("folder", parent=model)
    provider = FilesystemProvider(root, resource_root=model)

    observation = resource.profile(provider=provider)

    assert observation.exists is True
    assert observation.entry_type == "directory"
    assert observation.permissions is not None
