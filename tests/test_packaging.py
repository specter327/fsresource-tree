from importlib import import_module, metadata

import fsresource_tree as fs


def test_distribution_version_matches_package_version():
    assert metadata.version("fsresource-tree") == fs.__version__


def test_distribution_declares_the_supported_core_dependency():
    requirements = metadata.requires("fsresource-tree") or []
    assert "resourcetree>=0.5.0" in requirements


def test_public_exports_are_importable():
    expected = {
        "Resource",
        "File",
        "Directory",
        "FSResourceTree",
        "FilesystemProvider",
        "FilesystemProviderProtocol",
        "ProviderCapabilities",
        "PhysicalProfile",
        "FilesystemResourceType",
        "resource_from_path",
        "validate_path",
        "scan",
        "ScanResult",
        "FilesystemChangeEvent",
        "FilesystemChangeType",
        "PollingMonitor",
        "copy",
        "move",
        "rename",
        "operations",
        "renderers",
        "ResourceTreeError",
        "ResourceNotFoundError",
        "ResourceAlreadyRegisteredError",
        "InvalidParentError",
        "UnsupportedOperationError",
    }

    assert set(fs.__all__) == expected
    for name in expected:
        assert getattr(fs, name) is not None


def test_runtime_subpackages_are_importable():
    for module in (
        "fsresource_tree.core",
        "fsresource_tree.operations",
        "fsresource_tree.operations.monitor",
        "fsresource_tree.providers",
        "fsresource_tree.providers.contract",
        "fsresource_tree.profile",
        "fsresource_tree.factory",
        "fsresource_tree.renderers",
    ):
        assert import_module(module) is not None


def test_generic_resource_tree_is_not_reexported_as_a_filesystem_alias():
    assert not hasattr(fs, "ResourceTree")
