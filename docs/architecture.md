# Filesystem specialization architecture

## Inheritance contract

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

The generic package owns resource identity and logical relationships. This package owns the interpretation and manipulation of real filesystem objects.

## Placement of filesystem capabilities

| API / capability | Public surface | Implementation owner |
|---|---|---|
| `File.name`, `File.extension`, `File.filename()` | File model | File model |
| `File.size` | Cached/read-only property | File profile cache |
| `File.query_size()` | File convenience method | Filesystem metadata operation |
| `File.profile()` | File convenience method | Profile/query service |
| `File.create()`, `remove()`, `move()`, `copy()` | File convenience methods | Filesystem operations |
| `File.open()` | File convenience method | Filesystem I/O operation |
| `Directory.move()`, `remove()`, `copy()` | Directory convenience methods | Filesystem operations |
| `Directory.search(regex)` | Inherited generic search | Container in resourcetree |
| `ResourceTree.search(regex)` | Inherited generic search | ResourceTree in resourcetree |
| physical scanning | `scan(location)` / scanner service | Scanner |
| monitoring and callbacks | `enable_monitor()`, `disable_monitor()`, `watch_*` | Monitor service and event bus |
| dictionary, JSON and XML serialization | Model methods | Specialized model classes over the core format encoders |
| Mermaid/canvas output | optional object wrappers | renderers |
| statistics | analyzer service | analysis |
| integrity and access checks | validator service | integrity |
| OS selection | Provider | providers/adapters |

## Model invariants

An `FSResourceTree` has only `Directory` roots and contains only `Directory` and `File` resources. A `Directory` accepts only those two specialized resource types as children. The generic core remains unaware of filesystem classes.

The tree uses the generic `roots` collection. There is no singular-root alias or alternate generic tree name in this package.

## Serialization

`File` and `Directory` override `to_dict()` and `from_dict()` to preserve their explicit type identifiers and filesystem-specific fields. `FSResourceTree` reconstructs roots through the filesystem factory. The inherited JSON and XML methods operate on these specialized dictionaries through dynamic dispatch.

The generic `resourcetree` factory remains limited to `Resource`, `Asset`, `Container` and `ResourceTree`; filesystem knowledge belongs here.

## Property semantics

Properties should not silently perform expensive or failure-prone I/O.

For example, `File.size` should expose the most recently known size in the in-memory profile. `File.query_size()` should explicitly query the filesystem and refresh that value. `File.profile()` should refresh a defined metadata snapshot. This makes I/O visible, allows cached/offline representations and gives monitoring a clear update target.

## Instance methods and operation modules

Expose natural object-oriented entry points on File and Directory, but implement the actual behavior in independent modules:

- `operations/create.py`
- `operations/delete.py`
- `operations/move.py`
- `operations/copy.py`
- `operations/open.py`
- `scanner.py`
- `monitoring/`
- `renderers/`
- `analysis/`
- `integrity/`
- `providers/`

A method such as `file.move(destination)` should delegate to the operation layer. Collection operations should accept iterables or an FSResourceTree and reuse the same implementation, rather than duplicating logic in File, Directory and FSResourceTree.

## Tree composition

An `FSResourceTree` manages specialized Directory roots and their File/Directory descendants. A filesystem scan should create Directory and File objects and register them in the tree. Mounting logical filesystem trees remains an in-memory composition operation; reconciling mounted resources with physical filesystem locations is filesystem-specific.

## Path handling

A path string is an input/output representation at the filesystem boundary. The primary in-memory API should accept and return File, Directory and FSResourceTree objects. A filesystem adapter resolves an object to its physical path; the generic core must never interpret a string as an operating-system path.
