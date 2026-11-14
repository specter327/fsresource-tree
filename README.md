# fsresource-tree

**Filesystem specialization for [resourcetree](https://github.com/specter327/resourcetree).**

`fsresource-tree` models real filesystem entries using the generic resource hierarchy supplied by `resourcetree`. It does not redefine the foundational resource model.

## Inheritance

```text
resourcetree
├── Resource
│   ├── Asset
│   └── Container
└── ResourceTree

fsresource-tree
├── File(Asset)
├── Directory(Container)
└── FSResourceTree(ResourceTree)
```

- `File` extends `Asset` with filesystem-specific file attributes such as extension and, progressively, size, profile and monitoring.
- `Directory` extends `Container` with filesystem-specific directory behavior.
- `FSResourceTree` extends `ResourceTree` with filesystem discovery, physical resource operations and platform-specific behavior.
- `ResourceTree` remains available as a backwards-compatible alias for `FSResourceTree` in this package.

## Design boundary

The generic core owns identity, metadata, hierarchy, traversal, indexing and composition. This specialization owns filesystem concerns: physical paths, scanning, file and directory operations, permissions, size queries, integrity checks, platform compatibility and filesystem monitoring.

The public API is designed to operate primarily on `File`, `Directory` and `FSResourceTree` objects. Text paths are inputs to discovery or resource construction, not the central data model.

## Installation

```bash
pip install fsresource-tree
```

## Basic model

```python
from fsresource_tree import Directory, File, FSResourceTree

root = Directory("/")
documents = Directory("documents", parent=root)
report = File("report", extension="txt", parent=documents)

tree = FSResourceTree(root=root)

print(report.filename())
print(tree.search(r"report"))
```

## Generic core

The underlying classes can be imported directly from `resourcetree`:

```python
from resourcetree import Asset, Container, Resource, ResourceTree
```

## Supported platforms

The target platforms are Windows, GNU/Linux, macOS and Termux. Platform-specific behavior is provided by filesystem providers and must be validated on each target environment.

## Versioning

This release targets `resourcetree>=0.3.0`. The package is published manually by its maintainer; this repository does not publish to PyPI automatically.
