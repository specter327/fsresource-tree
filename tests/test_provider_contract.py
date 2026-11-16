from datetime import datetime, timezone
from pathlib import Path

from fsresource_tree import (
    Directory,
    File,
    FilesystemProvider,
    FilesystemProviderProtocol,
    PhysicalProfile,
    ProviderCapabilities,
    UnsupportedOperationError,
)
from fsresource_tree.operations import create, delete, exists, profile


class StructuralProvider:
    """Test provider that implements the contract without inheriting a base."""

    capabilities = ProviderCapabilities(
        platform="test",
        filesystem=None,
        race_resistant=False,
        operations=frozenset({"create", "exists", "delete", "delete_tree", "purge", "profile"}),
        metadata_fields=frozenset({"exists", "entry_type", "size"}),
    )

    def __init__(self):
        self.created = []

    def create(self, resource):
        self.created.append(resource)
        return Path(resource.name)

    def exists(self, resource):
        return True

    def delete(self, resource):
        return True

    def delete_tree(self, resource):
        return True

    def purge(self, directory):
        return True

    def profile(self, resource):
        return PhysicalProfile(exists=True, observed_at=datetime.now(timezone.utc))


def test_local_provider_exposes_immutable_runtime_capabilities(tmp_path):
    root = tmp_path / "sandbox"
    root.mkdir()
    logical_root = Directory("root")
    provider = FilesystemProvider(root, resource_root=logical_root)

    capabilities = provider.capabilities

    assert isinstance(provider, FilesystemProviderProtocol)
    assert capabilities.platform
    assert capabilities.filesystem is None
    assert capabilities.race_resistant is provider.race_resistant
    assert {"create", "exists", "delete", "delete_tree", "purge", "profile"} <= capabilities.operations
    assert {"exists", "entry_type", "size", "permissions"} <= capabilities.metadata_fields
    try:
        capabilities.platform = "changed"
    except (AttributeError, TypeError):
        pass
    else:
        raise AssertionError("provider capabilities must be immutable")


def test_operation_services_accept_structural_provider_implementations():
    provider = StructuralProvider()
    root = Directory("root")
    file = File("report", parent=root)

    assert isinstance(provider, FilesystemProviderProtocol)
    assert create(file, provider=provider) is True
    assert provider.created == [file]
    assert exists(file, provider=provider) is True
    assert profile(file, provider=provider).exists is True


def test_capabilities_freeze_mutable_inputs():
    operations = {"exists"}
    metadata_fields = {"size"}
    capabilities = ProviderCapabilities(
        platform="test",
        filesystem=None,
        race_resistant=False,
        operations=operations,
        metadata_fields=metadata_fields,
    )

    operations.add("delete")
    metadata_fields.add("permissions")

    assert capabilities.operations == frozenset({"exists"})
    assert capabilities.metadata_fields == frozenset({"size"})


def test_local_provider_identifies_termux_environment(tmp_path, monkeypatch):
    root = tmp_path / "sandbox"
    root.mkdir()
    monkeypatch.setenv("TERMUX_VERSION", "0.118.0")
    provider = FilesystemProvider(root, resource_root=Directory("root"))

    assert provider.capabilities.platform == "termux"


class CreateOnlyProvider:
    capabilities = ProviderCapabilities(
        platform="test",
        filesystem=None,
        race_resistant=False,
        operations=frozenset({"create"}),
        metadata_fields=frozenset(),
    )

    def create(self, resource):
        return Path(resource.name)


def test_provider_protocol_does_not_require_unsupported_methods():
    provider = CreateOnlyProvider()
    file = File("report", parent=Directory("root"))

    assert create(file, provider=provider) is True
    try:
        delete(file, provider=provider)
    except UnsupportedOperationError as error:
        assert "delete" in str(error)
    else:
        raise AssertionError("unsupported provider operation must fail explicitly")
