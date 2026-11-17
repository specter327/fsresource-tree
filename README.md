# fsresourcetree

**Filesystem specialization for [resourcetree](https://github.com/specter327/resourcetree).**

`fsresourcetree` maps filesystem concepts to the generic resource model. It does not redefine the foundational hierarchy and is not limited to an in-memory-only filesystem model.

## Model layers

```text
resourcetree
├── Resource
│   ├── Asset
│   └── Container
└── ResourceTree

fsresourcetree
├── File(Asset)
├── Directory(Container)
└── FSResourceTree(ResourceTree)
```

- `resourcetree` owns identity, metadata, parent/children relationships, generic traversal, indexing, composition and generic dict/JSON/XML serialization.
- `fsresourcetree` defines filesystem-specific `File`, `Directory` and `FSResourceTree` types, filesystem operations, and their specialized serialization.
- The resource hierarchy represents filesystem entries and can be used to operate on the corresponding physical filesystem.

## Virtual and physical state

The model and the real filesystem are separate sources of truth. A File or Directory may exist virtually without existing physically; a physical entry may exist without being materialized in the model. Properties such as `size`, timestamps, permissions and `exists` are physical observations that can change independently of the in-memory object.

`File.profile()` and `Directory.profile()` query provider-backed metadata and return an immutable `PhysicalProfile` snapshot. The default call does not mutate the resource; pass `update_cache=True` to store the snapshot as `resource.physical_profile`. A missing entry is represented by `exists=False`; permission and I/O failures remain exceptions. Every snapshot records its UTC observation time. A cached observation is never a guarantee that the physical entry has not changed since it was queried.

## Effective access checks

```python
from fsresourcetree import Directory, File, FilesystemProvider, readable, writable, executable

root = Directory("workspace")
report = File("report.txt", parent=root)

with FilesystemProvider("/srv/workspace", resource_root=root) as provider:
    can_read = report.readable()
    can_write = report.writable()
    can_execute = report.executable()

    # Module-level functions remain available for explicit dependency injection.
    assert readable(report, provider=provider) == can_read
```

The methods are available on both `File` and `Directory`; `is_readable()`, `is_writable()` and `is_executable()` are equivalent aliases. For directories, execute access means search/traversal permission. Checks use the current process identity. POSIX uses effective UID/GID checks where Python exposes them; Windows follows native `os.access()` semantics and is not a complete NTFS ACL evaluator. Arbitrary users/groups cannot be impersonated. A missing entry returns `False`; symbolic links/reparse points, invalid resource types and other I/O failures remain errors. Results are point-in-time observations, not authorization guarantees for later operations; the attempted operation remains authoritative. On POSIX, search-only directory descriptors (`O_PATH`/`O_SEARCH` where available) allow checks through known parent directories without requiring read permission on those directories. When the provider is descriptor-pinned but the runtime cannot perform descriptor-relative `os.access()` checks, it raises `UnsupportedOperationError` rather than falling back to a path-based check outside that descriptor boundary.

## Scope and non-goals

**`fsresourcetree` does not expose file-content reading or writing APIs.** Filesystem-level `copy()` remains in scope as an opaque provider operation: callers request a copy but never receive or manipulate the transferred bytes.

Filesystem manipulation is within the package's scope. Permitted operation categories include:

- Creating and deleting files and directories.
- Copying, moving and renaming files and directories.
- Checking whether paths and filesystem entries exist.
- Inspecting filesystem metadata, such as type, size, timestamps, permissions and ownership, where supported by the platform.
- Listing directory contents and materializing filesystem entries as `File` and `Directory` resources.
- Other filesystem-management operations that do not read or write file contents.

This defines the package boundary; it does **not** claim that every permitted operation is already implemented. The public physical-operation API provides `create()`, `exists()`, `delete()`, `copy()`, `move()` and `rename()` (including modeled recursive deletion and explicit `purge()`). Logical `path()`, `walk()` and `find()` operate on the in-memory model. Path materialization is provided by `validate_path()` and `resource_from_path()`. Public recursive physical discovery is available through `operations.scan()` (also exported as `fsresourcetree.scan`). It is additive, reuses matching resources, supports exclusions and never follows links. Metadata profiling is available through `profile()`.

The content boundary excludes APIs for reading, writing, appending, overwriting, streaming or hashing file contents. An opaque filesystem copy operation is a separate management operation explicitly permitted by the project: it transfers an entry without exposing its bytes to the caller or adding content-access methods to the resource model. Metadata profiling uses stat-style metadata only.

The generic `Asset.data` field inherited by `File` is an in-memory model payload only. It is not connected to physical file contents. Applications that need physical content I/O must do so independently, using Python's standard `open()` function and its file objects / I/O wrappers (`IOWrapper`). Those workflows are outside the responsibility of `fsresourcetree`.

## Providers and supported platforms

Filesystem-specific behavior belongs to specialized providers rather than a forced uniform abstraction. The current provider abstraction is structural: operation services consume `FilesystemProviderProtocol`, whose minimal contract is an immutable `ProviderCapabilities` declaration. Each operation is checked independently against the provider's declared capabilities and callable method; unsupported requests raise `UnsupportedOperationError`. Providers are not required to implement unrelated operations. Capabilities report runtime platform, known filesystem format, race-resistance guarantee, supported operations and metadata fields. The intended platform implementations include `LinuxProvider`, `TermuxProvider`, `WindowsProvider` and may admit additional implementations such as `MacOSProvider`, selected through a dynamic provider loader. This architecture is documented as the target; the current code still has one `FilesystemProvider` implementation and no dynamic loader.

The required compatibility targets are:

- **GNU/Linux**
- **Termux**
- **Windows**

macOS is an extensibility target, not a current compatibility commitment. Operating systems and filesystem formats are different layers: a provider must expose the capabilities actually available on the mounted filesystem (for example, NTFS, FAT/exFAT or ext filesystems) rather than assuming one format per OS.

See [the architecture document](docs/architecture.md) for the virtual/physical state model, provider contract, explicit side effects, metadata, discovery, monitoring and current implementation status.

## Input paths, names and resource objects

Filesystem paths and names are accepted as input data, but the library's working model is made of `File` and `Directory` objects. Hierarchy management, traversal, search and tree registration operate on resource objects; path strings are inputs to filesystem operations, not substitutes for resources.

When an existing path is supplied for materialization, validate its actual filesystem entry type before constructing the model. `validate_path()` returns the matching resource class and can enforce an expected type; `resource_from_path()` performs that validation and materializes the corresponding object:

```python
from fsresourcetree import Directory, File, resource_from_path, validate_path

root = resource_from_path("/srv/workspace")
assert isinstance(root, Directory)

report = resource_from_path("/srv/workspace/report.txt", parent=root)
assert isinstance(report, File)

assert validate_path("/srv/workspace", expected_type=Directory) is Directory
assert validate_path("/srv/workspace/report.txt", expected_type=File) is File
```

Path materialization inspects the entry itself with `lstat`: symbolic links, Windows reparse points and special entries (sockets, devices, FIFOs, etc.) are rejected rather than silently classified as their targets. A path ending in `..` is also rejected because it identifies a navigation operation, not a named resource. The resulting object stores its logical name and filesystem-specific attributes, not the input path. Materialization itself creates only the resource object; separate filesystem-management operations may create, remove, copy, move or otherwise modify physical entries, subject to the file-content I/O restriction above.

A name alone does not reveal whether a physical entry is a file or directory. For name-only construction, the caller explicitly chooses the model type:

```python
directory = Directory("documents")
file = File("report", extension="txt", parent=directory)
```

This distinction is intentional: paths are inputs to validation and filesystem operations, names initialize model objects, and resource objects are the library's working unit.

### Physical copy, move and rename

All three operations require an explicit provider and resource objects:

```python
from fsresourcetree import copy, move, rename

rename(report, "annual-report", provider=provider)
move(report, archive_directory, provider=provider)
duplicate = copy(report, backup_directory, provider=provider, new_name="report-backup")
```

Move and rename preserve the resource UID and update the in-memory parent/name after the physical operation succeeds. Copy creates new resource identities. Directory copies reproduce the modeled subtree only; run `scan()` first if the model must reflect all physical descendants. Existing copy targets are refused rather than intentionally overwritten. File data is transferred internally by the provider; no bytes are returned and no file-content accessor is added. The local provider copies regular files and creates directories exclusively. Cross-volume moves are not converted into copy-and-delete operations. The current implementation does not promise an atomic transaction against hostile concurrent filesystem mutation; Windows remains path-based, and POSIX descriptor-relative operations still have the provider's documented concurrent-rename limitations.

### Resource instance methods

Physical providers are bound once to a physical Directory root. Instance methods resolve the provider from the resource itself or its nearest ancestor; callers do not pass it to every operation. The simplest setup is to materialize an existing directory as a root:

```python
from fsresourcetree import File, resource_from_path

root = resource_from_path("/srv/workspace")  # creates and binds its local provider
report = File("report", extension="txt", parent=root)

report.create()
assert report.exists()
report.rename("annual-report")
backup = report.copy(root, new_name="backup")
backup.delete()

root.scan(recursive=True)
root.close_provider()  # release the pinned root descriptor
```

For a model built manually, configure the provider once at its root:

```python
from fsresourcetree import Directory, File, FilesystemProvider

root = Directory("workspace")
provider = FilesystemProvider("/srv/workspace", resource_root=root)
report = File("report", extension="txt", parent=root)
report.create()
```

Available on both `File` and `Directory`: `create()`, `exists()`, `delete()`, `rename()`, `move()`, `copy()`, and `profile()`. `Directory` additionally exposes `scan()` and `purge()`. The provider is bound to the root, inherited by descendants, and unbound when the provider is closed; call `root.close_provider()` to release it. A resource without a configured provider raises `ProviderNotConfiguredError`; an unsupported runtime platform raises `UnsupportedPlatformError`. Neither condition is silently ignored. Module-level operation functions continue to accept an explicit provider for dependency injection.

Physical `delete()` and `purge()` do not detach the resource from the in-memory hierarchy. This preserves the distinction between the model and physical state.

## Generic core

The underlying classes can be imported directly from `resourcetree`:

```python
from resourcetree import Asset, Container, Resource, ResourceTree
```

## Installation

```bash
pip install fsresource-tree
```

Packages are published manually by the maintainer; this repository does not publish to PyPI automatically.


## Provider security limitations

On POSIX, descriptor-relative operations prevent symlink substitution, but they are not an atomic transaction against concurrent renames of already-opened directories. If an untrusted actor can rename a traversed descendant (for example, `root/a/b`) outside the configured root after it has been opened, later create, delete or purge operations may act through that descriptor on the moved tree. The configured root, its ancestors, and every traversed parent/descendant directory must therefore be protected against hostile concurrent renames or mutations. The provider is not an OS sandbox. On Windows, path-based validation checks existing components for symbolic links and reparse points before create, delete and purge I/O, but cannot prevent a hostile concurrent replacement after validation. Full Windows handle-relative operations remain outside the current security claim.
