# fsresource-tree

**Filesystem specialization for [resourcetree](https://github.com/specter327/resourcetree).**

`fsresource-tree` maps the generic resource model to filesystem entries. It does not redefine the foundational hierarchy.

## Model layers

```text
resourcetree
├── Resource
│   ├── Asset
│   └── Container
└── ResourceTree

fsresource-tree
├── File(Asset)
├── Directory(Container)
├── FSResourceTree(ResourceTree)
└── FilesystemProvider
```

- `resourcetree` owns identity, metadata, parent/children relationships, generic traversal, indexing, composition and generic dict/JSON/XML serialization.
- `fsresource-tree` defines filesystem-specific `File`, `Directory` and `FSResourceTree` types and their specialized serialization.
- `FilesystemProvider` maps one top-level logical `Directory` to one existing physical directory and owns physical I/O. The model itself does not perform filesystem access.

## Confined local provider

The provider requires an explicit top-level model `Directory` and an existing physical directory. It binds that exact model object to the physical root; other independent model roots cannot be resolved through the same provider. The model root's name is not appended to the physical path. Descendants are resolved relative to it.

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from fsresource_tree import Directory, File, FilesystemProvider
from fsresource_tree.operations import create, delete, exists

with TemporaryDirectory() as temporary:
    root = Directory("workspace")
    documents = Directory("documents", parent=root)
    report = File("report", extension="txt", parent=documents)
    provider = FilesystemProvider(Path(temporary), resource_root=root)

    create(root, provider=provider, recursive_children=True)
    assert exists(report, provider=provider)
    delete(report, provider=provider)
```

Each provider is bound to exactly one logical Directory root. A multi-root FSResourceTree therefore uses one provider mapping per physical root. Physical operations require an explicit provider. `path(resource)` returns a relative logical path and performs no I/O. `delete(..., recursive_children=True)` removes only modeled descendants; `purge=True` explicitly removes unmodeled physical contents under a modeled directory. The provider refuses to delete or purge its configured root and refuses symbolic links and Windows reparse points rather than following them.

**Security boundary:** on POSIX, the provider pins the configured root with a directory descriptor and performs create, existence, delete, recursive-delete preflight and purge traversal relative to open directory descriptors with no-follow flags. This prevents symbolic-link substitution from redirecting those operations outside the pinned root. Close the provider when it is no longer needed, preferably with a `with FilesystemProvider(...)` block.

The Windows implementation currently retains path-based validation and is **not race-resistant** against concurrent hostile mutation. POSIX descriptor-relative operations also do not make recursive deletion transactional against concurrent renames of already-opened directories. The provider is not a complete OS sandbox: the configured directory and its ancestors must not be writable by an untrusted concurrent actor. Full Windows handle-relative operations and stronger concurrent-rename guarantees remain outside this release's security claim.

## Generic core

```python
from resourcetree import Asset, Container, Resource, ResourceTree
```

## Supported platforms

The model is platform-independent. The local provider uses host filesystem path semantics. Windows reparse-point handling and race-resistant descriptor-relative operations require additional platform-specific validation.

## Installation

```bash
pip install fsresource-tree
```

Packages are published manually by the maintainer; this repository does not publish to PyPI automatically.
