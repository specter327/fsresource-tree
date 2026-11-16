# fsresource-tree

**Filesystem specialization for [resourcetree](https://github.com/specter327/resourcetree).**

`fsresource-tree` models filesystem entries using the generic resource hierarchy supplied by `resourcetree`. It does not redefine the foundational resource model.

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

- `File` extends `Asset` with filesystem-specific attributes such as extension.
- `Directory` extends `Container` and accepts only filesystem `Directory` and `File` children.
- `FSResourceTree` extends `ResourceTree` and manages one or more directory roots containing filesystem resource types only.

The package exports `FSResourceTree` as its only tree class name. Use the generic `ResourceTree` directly from `resourcetree` when a domain-neutral forest is required.

## Design boundary

The generic core owns identity, metadata, hierarchy, traversal, indexing and composition. This specialization owns filesystem concerns: physical paths, scanning, file and directory operations, permissions, size queries, integrity checks, platform compatibility and filesystem monitoring.

The public API operates on `File`, `Directory` and `FSResourceTree` objects. Text paths are inputs to discovery or resource construction, not the central data model.

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

tree = FSResourceTree(roots=[root])

print(report.filename())
print(tree.search(r"report"))
```

Every registered filesystem root must be a `Directory`; an empty tree can be populated later. A directory can contain only `Directory` and `File` instances. This prevents generic resources from entering a filesystem-specific model accidentally.

## Serialization

Filesystem classes override the generic dictionary contract so that specialized types and fields survive reconstruction:

```python
from fsresource_tree import Directory, File, FSResourceTree

root = Directory("/")
File("report", extension="txt", parent=root, data={"size": 128})
tree = FSResourceTree(roots=[root])

restored = FSResourceTree.from_dict(tree.to_dict())
restored_json = FSResourceTree.from_json(tree.to_json())
restored_xml = FSResourceTree.from_xml(tree.to_xml())

assert isinstance(restored.roots[0], Directory)
assert isinstance(restored.roots[0].children[0], File)
assert restored.roots[0].children[0].extension == "txt"
```

The round-trip preserves resource and tree identifiers, names, timestamps, metadata, file payloads, extensions and hierarchy. The core index is rebuilt from the restored roots. The generic `resourcetree` factory intentionally does not know filesystem types.

## Generic core

The underlying classes can be imported directly from `resourcetree`:

```python
from resourcetree import Asset, Container, Resource, ResourceTree
```

## Supported platforms

The target platforms are Windows, GNU/Linux, macOS and Termux. Platform-specific behavior is provided by filesystem providers and must be validated on each target environment.

## Versioning

This release requires `resourcetree>=0.5.0`. The package is published manually by its maintainer; this repository does not publish to PyPI automatically.
