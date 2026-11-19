import pytest

from fsresourcetree import (
    Directory,
    LinuxProvider,
    ProviderLoader,
    TermuxProvider,
    UnsupportedPlatformError,
    WindowsProvider,
    resource_from_path,
    detect_runtime_platform,
)


def test_loader_maps_supported_runtime_identifiers():
    assert ProviderLoader.provider_class("linux") is LinuxProvider
    assert ProviderLoader.provider_class("termux") is TermuxProvider
    assert ProviderLoader.provider_class("win32") is WindowsProvider


def test_loader_exposes_supported_platforms():
    assert ProviderLoader.supported_platforms() == ("linux", "termux", "win32")


@pytest.mark.parametrize("platform", ["darwin", "freebsd", "unknown"])
def test_loader_rejects_unsupported_platforms(platform):
    with pytest.raises(UnsupportedPlatformError, match=platform):
        ProviderLoader.provider_class(platform)


def test_loader_selects_current_runtime_and_binds_provider(tmp_path):
    root_path = tmp_path / "workspace"
    root_path.mkdir()
    logical_root = Directory("workspace")

    provider = ProviderLoader.load(root_path, resource_root=logical_root)

    assert isinstance(provider, ProviderLoader.provider_class())
    assert logical_root.filesystem_provider is provider
    assert provider.capabilities.platform in ProviderLoader.supported_platforms()
    logical_root.close_provider()


def test_platform_specific_provider_rejects_mismatched_runtime(tmp_path):
    root_path = tmp_path / "workspace"
    root_path.mkdir()
    logical_root = Directory("workspace")
    selected = ProviderLoader.provider_class()
    other = next(
        provider
        for platform, provider in (
            ("linux", LinuxProvider),
            ("termux", TermuxProvider),
            ("win32", WindowsProvider),
        )
        if provider is not selected
    )

    with pytest.raises(UnsupportedPlatformError, match="requires runtime platform"):
        other(root_path, resource_root=logical_root)

    assert logical_root.filesystem_provider is None



def test_runtime_detection_identifies_termux(monkeypatch):
    monkeypatch.setenv("TERMUX_VERSION", "0.118.0")
    assert detect_runtime_platform() == "termux"


def test_resource_from_path_uses_the_runtime_loader(tmp_path):
    root_path = tmp_path / "workspace"
    root_path.mkdir()

    resource = resource_from_path(root_path)

    assert isinstance(resource.filesystem_provider, ProviderLoader.provider_class())
    resource.close_provider()
