# Filesystem specialization architecture

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
├── FSResourceTree(ResourceTree)
└── FilesystemProvider
```

## Responsibility boundaries

### resourcetree

The generic core owns resource identity, metadata, timestamps, parent/children relationships, generic traversal, optional forest management, derived indexing and base dictionary/JSON/XML serialization. It has no filesystem I/O or operating-system path semantics.

### fsresource-tree model

- `File(Asset)` adds file-specific fields such as extension and payload.
- `Directory(Container)` constrains children to filesystem resource types.
- `FSResourceTree(ResourceTree)` constrains roots and descendants to Directory/File.
- Specialized `to_dict/from_dict` implementations preserve concrete filesystem resource types. The generic core factory does not know these types.

### FilesystemProvider

The provider owns physical path resolution and local filesystem I/O. It maps the top-level logical Directory to one existing physical directory. Its name is a model label and is not appended to the provider root path.

Physical operations require an explicit provider. The model can be built, traversed, searched and serialized without touching the host filesystem.

## Operation boundary

| Operation | Responsibility |
|---|---|
| `path(resource)` | In-memory relative logical path |
| `walk(resource)` | Iterative in-memory traversal |
| `exists(resource, provider=...)` | Physical existence check |
| `create(resource, provider=...)` | Physical creation |
| `delete(resource, provider=...)` | Physical deletion |
| `FilesystemProvider.resolve(...)` | Confined mapping to a physical path |
| `FilesystemProvider.purge(...)` | Explicit removal of unmodeled physical contents |

Recursive modeled deletion preflights the physical directory contents before modifying the tree. It refuses a mismatch rather than silently deleting unmodeled entries. Purge is separate and explicit. The configured provider root cannot be deleted or purged.

## Security boundary and remaining hardening

The provider rejects traversal components and symbolic links/reparse points in existing path components. On Windows, create, delete and purge remain path-based: every existing component is checked before I/O, but a hostile concurrent replacement after validation can still redirect an operation. On POSIX, descriptor-relative no-follow operations prevent symlink substitution but are not atomic against concurrent renames of already-opened directories. If an actor can rename a traversed descendant (for example, `root/a/b`) outside the configured root after it has been opened, subsequent create, delete or purge operations may act through that descriptor on the moved tree. The configured root, its ancestors, and all traversed parent/descendant directories must therefore be protected against hostile concurrent renames or mutations. Do not treat this provider as a hardened sandbox against concurrent hostile filesystem mutation.

## Serialization

File and Directory own their specialized dictionary representation. FSResourceTree reconstructs roots through the filesystem-specific factory. The inherited JSON/XML encoders serialize those dictionaries through dynamic dispatch. The generic core remains unaware of filesystem types.

## Extension model

Future platform-specific providers may implement the same provider boundary for POSIX, Windows, Android/Termux, remote filesystems or virtual filesystems. Such providers belong in this specialization or dedicated adapters, never in the generic core.
