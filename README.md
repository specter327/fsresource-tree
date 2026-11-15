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

The provider root must already exist and be a directory. The top-level model `Directory` represents that physical root; its name is not appended to the physical path. Descendants are resolved relative to it.

```python
from pathlib import Path
from tempfile import TemporaryDirectory

from fsresource_tree import Directory, File, FilesystemProvider
from fsresource_tree.operations import create, delete, exists

with TemporaryDirectory() as temporary:
    root = Directory("workspace")
    documents = Directory("documents", parent=root)
    report = File("report", extension="txt", parent=documents)
    provider = FilesystemProvider(Path(temporary))

    create(root, provider=provider, recursive_children=True)
    assert exists(report, provider=provider)
    delete(report, provider=provider)
```

Physical operations require an explicit provider. `path(resource)` returns a relative logical path and performs no I/O. `delete(..., recursive_children=True)` removes only modeled descendants; `purge=True` explicitly removes unmodeled physical contents under a modeled directory. The provider refuses to delete or purge its configured root and refuses symbolic links rather than following them.

**Security boundary:** this provider enforces lexical confinement and checks existing path components for symbolic links. Path-based checks cannot eliminate every time-of-check/time-of-use race against a concurrent hostile process. Do not use it as a hardened sandbox against an attacker who can concurrently mutate the provider directory. Descriptor-relative, platform-specific operations are a separate hardening layer.

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
