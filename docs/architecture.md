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
| `File.name`, `File.extension` | File properties | File model |
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
| serialization | optional object wrappers | serializers |
| Mermaid/canvas output | optional object wrappers | renderers |
| statistics | analyzer service | analysis |
| integrity and access checks | validator service | integrity |
| OS selection | Provider | providers/adapters |

## Important property semantics

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
- `serializers/`
- `renderers/`
- `analysis/`
- `integrity/`
- `providers/`

A method such as `file.move(destination)` should delegate to the operation layer. Collection operations should accept iterables or a ResourceTree and reuse the same implementation, rather than duplicating logic in File, Directory and ResourceTree.

## Tree composition

`FSResourceTree` inherits the generic root and membership model. A filesystem scan should create Directory and File objects and register them in the tree. Mounting logical trees should remain a generic operation; reconciling mounted resources with physical filesystem locations is filesystem-specific.

## Path handling

A path string is an input/output representation at the filesystem boundary. The primary in-memory API should accept and return File, Directory and FSResourceTree objects. A filesystem adapter resolves an object to its physical path; the generic core must never interpret a string as an operating-system path.
