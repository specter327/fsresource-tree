import stat
from types import SimpleNamespace

import pytest

from fsresourcetree import Directory, File, resource_from_path, validate_path


def test_validate_path_identifies_existing_file_and_directory(tmp_path):
    directory = tmp_path / "documents"
    directory.mkdir()
    file = directory / "report.tar.gz"
    file.write_text("data", encoding="utf-8")

    assert validate_path(str(directory)) is Directory
    assert validate_path(file) is File


def test_validate_path_checks_the_expected_resource_type(tmp_path):
    directory = tmp_path / "documents"
    directory.mkdir()

    assert validate_path(directory, expected_type=Directory) is Directory
    with pytest.raises(TypeError, match="expected a filesystem file"):
        validate_path(directory, expected_type=File)
    with pytest.raises(TypeError, match="expected_type must be"):
        validate_path(directory, expected_type=str)


def test_resource_from_path_materializes_the_actual_entry_type(tmp_path):
    directory = tmp_path / "documents"
    directory.mkdir()
    file = directory / "report.tar.gz"
    file.write_text("data", encoding="utf-8")

    directory_resource = resource_from_path(directory)
    file_resource = resource_from_path(str(file), parent=directory_resource)

    assert isinstance(directory_resource, Directory)
    assert directory_resource.name == "documents"
    assert isinstance(file_resource, File)
    assert file_resource.name == "report.tar"
    assert file_resource.extension == "gz"
    assert file_resource.parent is directory_resource


def test_resource_from_path_preserves_dotfile_name(tmp_path):
    dotfile = tmp_path / ".gitignore"
    dotfile.write_text("", encoding="utf-8")

    resource = resource_from_path(dotfile)

    assert isinstance(resource, File)
    assert resource.name == ".gitignore"
    assert resource.extension is None


def test_resource_from_path_preserves_trailing_dot_filename(tmp_path):
    trailing_dot_file = tmp_path / "report."
    try:
        trailing_dot_file.write_text("", encoding="utf-8")
    except OSError:
        pytest.skip("the platform does not support filenames ending in a dot")

    resource = resource_from_path(trailing_dot_file)

    assert isinstance(resource, File)
    assert resource.name == "report."
    assert resource.extension is None
    assert resource.filename() == "report."


def test_validate_path_rejects_windows_reparse_points(tmp_path, monkeypatch):
    directory = tmp_path / "junction"
    directory.mkdir()
    original_lstat = type(directory).lstat

    def fake_lstat(path):
        if path == directory:
            return SimpleNamespace(
                st_mode=stat.S_IFDIR,
                st_file_attributes=getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400),
            )
        return original_lstat(path)

    monkeypatch.setattr(type(directory), "lstat", fake_lstat)

    with pytest.raises(ValueError, match="filesystem reparse points"):
        validate_path(directory)


def test_resource_from_path_rejects_non_directory_parent(tmp_path):
    file = tmp_path / "report.txt"
    file.write_text("", encoding="utf-8")

    with pytest.raises(TypeError, match="parent must be a Directory"):
        resource_from_path(file, parent=File("parent"))


def test_validate_path_rejects_missing_paths(tmp_path):
    with pytest.raises(FileNotFoundError):
        validate_path(tmp_path / "missing")


def test_validate_path_rejects_symbolic_links(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(target)
    except (NotImplementedError, OSError):
        pytest.skip("symbolic links are unavailable on this platform")

    with pytest.raises(
        ValueError,
        match="(symbolic links are not filesystem resources|filesystem reparse points are not resources)",
    ):
        validate_path(link)

def test_resource_from_path_rejects_terminal_parent_component(tmp_path):
    child = tmp_path / "child"
    child.mkdir()

    with pytest.raises(ValueError, match="paths ending in"):
        resource_from_path(child / "..")


@pytest.mark.parametrize("path_factory", [lambda: ".", lambda: __import__("pathlib").Path()])
def test_resource_from_path_materializes_current_directory(path_factory, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    resource = resource_from_path(path_factory())

    assert isinstance(resource, Directory)
    assert resource.name == tmp_path.name


def test_materialized_root_binds_provider_and_descendants_use_it(tmp_path):
    root = resource_from_path(tmp_path)
    report = File("report", extension="txt", parent=root)

    assert root.filesystem_provider is not None
    assert report.filesystem_provider is root.filesystem_provider

    assert report.create() is True
    assert report.exists() is True
    report.rename("annual-report")
    assert (tmp_path / "annual-report.txt").exists()

    duplicate = report.copy(root, new_name="backup")
    assert duplicate.exists() is True
    assert duplicate.delete() is True
    assert report.delete() is True


def test_unbound_virtual_resource_raises_explicit_provider_error():
    from fsresourcetree import ProviderNotConfiguredError

    with pytest.raises(ProviderNotConfiguredError, match="not associated"):
        Directory("virtual").create()


def test_provider_is_unbound_when_closed(tmp_path):
    from fsresourcetree import FilesystemProvider, ProviderNotConfiguredError

    root = Directory(tmp_path.name)
    provider = FilesystemProvider(tmp_path, resource_root=root)
    assert root.filesystem_provider is provider
    provider.close()

    with pytest.raises(ProviderNotConfiguredError):
        root.exists()
