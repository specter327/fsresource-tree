# Filesystem specialization architecture

## 1. Purpose and boundaries

`fsresourcetree` represents filesystem resources and provides controlled operations over real filesystem entries. It is not merely an in-memory tree, but its model must remain usable without touching the host filesystem.

The package has one non-negotiable I/O boundary:

> It may create, inspect, enumerate, copy, move, rename and delete filesystem entries. It must not expose APIs that read, write, append, overwrite, stream or hash file contents.

Allowed filesystem work includes entry creation/removal, metadata queries, directory enumeration, path/type checks and filesystem-management operations. Opaque filesystem-level copying is explicitly allowed: it transfers an entry without exposing the bytes to callers or adding content-access methods to the model. The package must not provide content read/write/append/overwrite/stream/hash APIs. Applications that need direct content access use Python `open()`, file objects or independent I/O wrappers outside this package.

The generic `Asset.data` field inherited by `File` is an in-memory model payload. It is not a physical file-content accessor and must never be implicitly synchronized with a disk file.

## 2. Model and physical environment

```text
resourcetree
├── Resource
│   ├── Asset
│   └── Container
└── ResourceTree

fsresourcetree
├── File(Asset)
├── Directory(Container)
├── FSResourceTree(ResourceTree)
├── provider contract
│   ├── LinuxProvider
│   ├── TermuxProvider
│   ├── WindowsProvider
│   └── additional providers (for example, MacOSProvider)
└── provider loader / factory
```

The diagram describes the intended architecture. The platform-specific providers and dynamic loader are not implemented yet. The current code has one concrete `FilesystemProvider` with POSIX descriptor-relative behavior where available and a path-based Windows branch.

### Generic core

`resourcetree` owns identity, metadata, timestamps, parent/children relationships, generic traversal, optional forest management, derived indexing and generic serialization. It has no filesystem path or operating-system semantics.

### Filesystem model

- `File(Asset)` represents a file entry.
- `Directory(Container)` represents a directory and owns child resource relationships.
- `FSResourceTree(ResourceTree)` optionally indexes and manages one or more Directory roots.
- Resources can exist without an `FSResourceTree`; the tree is a manager, not the physical filesystem.
- Model traversal, search, filtering and serialization operate on resource objects and must not silently perform physical I/O.

Paths are inputs to validation and provider operations. Resource objects are the working model. A physical path is not the identity of a resource and should not be confused with its logical `Resource.path()`.

## 3. Virtual state and physical state

Virtual and physical state are separate sources of truth. They may agree, differ, or exist independently.

| State | Meaning | Examples |
|---|---|---|
| Virtual | Values held by the in-memory resource model | name, extension, parent, children, metadata, cached observations |
| Physical / effective | Values observed from the real filesystem through a provider | existence, size, timestamps, permissions, ownership, entry type |

Examples:

- A virtual File or Directory may not exist physically yet.
- A physical entry may exist without a corresponding resource in the current model.
- A resource's virtual name or parent may differ from the physical entry until an explicit operation reconciles them.
- Physical metadata can change outside the process at any time.

A cached physical observation is not a live guarantee. It must carry observation time and enough status to distinguish at least: not observed, observed present, and observed absent. A failed query (for example, permission denied) must not be silently converted into “does not exist”.

### Profiling and synchronization

The intended `profile()` operation queries the provider and returns a point-in-time profile for a File or Directory. It may either:

1. Return the observation without mutating the resource model; or
2. Explicitly update the resource's cached physical properties.

The API must make the choice explicit. A profile is an observation, not a lock on the filesystem and not a permanent truth. Profiling must use metadata APIs only; it must never read file contents.

A profile should preserve native/provider-specific properties where meaningful instead of forcing every filesystem into an artificial common denominator. Common fields can be exposed consistently while capabilities and native details remain discoverable.

## 4. Provider architecture

### Platform providers

Platform differences belong behind specialized providers. The intended implementations are:

- `LinuxProvider`
- `TermuxProvider`
- `WindowsProvider`
- `MacOSProvider` as a possible additional provider, not a current compatibility commitment.

A dynamic provider loader/factory will detect the runtime platform and return the appropriate provider. If no provider is available, it must raise a clear, semantic exception; it must not silently fall back to an implementation with different safety guarantees.

Termux is identified as its own execution environment even where it can reuse POSIX primitives. It may have different storage permissions, mount visibility and Android-specific restrictions.

The current required compatibility targets remain GNU/Linux, Termux and Windows. macOS is an extensibility target only until it is explicitly added to the supported test matrix. The current local provider reports the Termux runtime separately when the Termux environment marker is present; this environment identification does not yet constitute a dedicated Termux provider implementation.

### Operating system is not filesystem format

An OS provider and a filesystem format are different layers. Linux may access ext4, FAT, NTFS and other mounted filesystems; Windows may access NTFS, FAT/exFAT and others. The provider must not assume that one operating system implies one filesystem format.

The provider should expose the capabilities and metadata actually available for the mounted volume/resource. It must not fabricate unsupported properties or normalize away meaningful differences. If an operation or property is unsupported, report that explicitly.

### Provider contract

The public structural interface is FilesystemProviderProtocol, which requires only an immutable ProviderCapabilities declaration. Operation services validate the specific requested operation against that provider's declared capabilities and callable method; providers do not have to implement unrelated or unsupported operations. Unsupported requests raise UnsupportedOperationError. Each configured provider reports its runtime platform identifier, known filesystem format (or None when it cannot be identified reliably), race-resistance guarantee, supported operations and available metadata fields. Capabilities describe the configured implementation; they are not inferred from the operating system alone.

The provider contract will own physical operations and queries, including:

- Resolve a resource relative to an explicitly configured physical root.
- Check existence and classify physical entries.
- Create, delete, copy, move and rename entries.
- Query metadata and effective access.
- Enumerate physical directory entries for discovery/materialization.
- Report supported capabilities and provider-native details.

Providers must not own the in-memory tree's search, filtering or indexing algorithms. Those belong to the model/operations layer.

The configured root is a security boundary. Providers must validate resource ancestry and path components, reject unsafe link/reparse traversal according to their guarantees, and document race resistance. A checked path returned for diagnostics must not be treated as a safe substitute for a provider operation.

On POSIX, descriptor-relative operations prevent symlink substitution, but they are not an atomic transaction against concurrent renames of already-opened directories. If an untrusted actor can rename a traversed descendant (for example, `root/a/b`) outside the configured root after it has been opened, later create, delete or purge operations may act through that descriptor on the moved tree. The configured root, its ancestors, and every traversed parent/descendant directory must therefore be protected against hostile concurrent renames or mutations. The provider is not an OS sandbox. On Windows, path-based validation checks existing components for symbolic links and reparse points before create, delete and purge I/O, but cannot prevent a hostile concurrent replacement after validation. Full Windows handle-relative operations remain outside the current security claim.

## 5. Operations and side effects

Operations are explicit. Constructing a resource, attaching it to a Directory, registering it in an FSResourceTree, serializing it, or searching it must not change the physical filesystem.

Physical operations require a provider. Destructive operations are never hidden side effects and must document exactly what they can change.

| Operation | Intended effect |
|---|---|
| `create` | Create a physical file/directory represented by a resource |
| `rename` | Rename a physical entry and reconcile its virtual name when requested |
| `move` | Move a physical entry to a destination resource/directory |
| `copy` | Copy filesystem entries without reading or writing their contents through package-level content APIs |
| `delete` | Delete the selected physical entry |
| `profile` | Query physical metadata; optionally refresh cached observations |
| `scan` | Discover physical entries and materialize/update resource objects |

For destructive or potentially irreversible operations, the call must be explicit, its scope/options must be visible, and its documentation must state preconditions, affected entries, failure behavior and whether partial effects are possible. Recursive deletion and purge must remain distinct: deleting a modeled subtree must not silently delete unknown physical children; purging unknown descendants requires a separate explicit opt-in.

Provider operations should validate/preflight before mutation where practical. They must use semantic exceptions for invalid resource types, unsupported capabilities, permission failures, missing entries, conflicts and unsafe paths. Native exceptions may be chained as causes.

## 6. Discovery, traversal and high-level operations

There are two distinct workflows:

1. **Physical discovery:** a provider enumerates the filesystem and returns entry information. A scan operation converts those observations into File/Directory objects and updates the selected model/tree according to an explicit reconciliation policy.
2. **Model operations:** traversal, recursive iteration, search, filtering, grouping and analysis work over already materialized resource collections and the FSResourceTree index. They do not repeatedly query the filesystem.

This separation avoids making every high-level operation an uncontrolled filesystem walk. A scan can be expensive and must make its recursion, exclusions, link handling, error policy and model-update behavior explicit.

## 7. Metadata and access decisions

Common metadata candidates include:

- `size`
- `last_access_time`
- `last_modified_time`
- `creation_time` where the platform exposes it
- `permissions`
- `owner` and `group` where supported
- `exists`
- physical entry type and provider/filesystem-specific attributes

These values are observations, not immutable model identity. The model must distinguish cached values from freshly queried physical values.

Decision helpers `readable()`, `writable()` and `executable()` (also exposed as resource methods and `is_*` aliases) ask the provider about access for the current process identity. POSIX uses effective UID/GID checks where Python exposes them; Windows follows native `os.access()` semantics and is not a general ACL evaluator. Arbitrary user/group impersonation is not implemented. The helpers do not infer access solely from Unix mode bits or cached profile metadata. A missing entry returns `False`; unsafe links and other I/O errors remain errors. These point-in-time checks are advisory and are not authorization guarantees for later operations.

### Effective access query semantics

The public `readable()`, `writable()` and `executable()` helpers are provider-backed observations for the current process identity. The local POSIX provider requests effective IDs when the runtime exposes `os.access(..., effective_ids=True)`; otherwise it uses the platform's default identity semantics. The API does not impersonate arbitrary users, groups or service accounts and does not evaluate Linux capabilities or every ACL implementation.

On Windows, Python's `os.access()` behavior is not a complete NTFS security-descriptor/ACL evaluator. These helpers report the host API's current-process result, not a portable or exhaustive authorization decision.

For directories, execute means search/traversal permission. Missing entries return `False`; symlinks/reparse points and resource-type mismatches are rejected. For descriptor-relative traversal, the local POSIX provider uses search-only directory descriptors (`O_PATH`/`O_SEARCH` where available), so checking a known file does not incorrectly require read permission on every parent directory. If a descriptor-pinned POSIX provider cannot perform descriptor-relative `os.access()` checks on a runtime, it raises `UnsupportedOperationError` rather than falling back to a path-based check that would bypass the pinned root. Every result is subject to TOCTOU: permissions, ACLs, mount state or the entry itself can change before a subsequent operation. The operation itself remains authoritative and may still fail.

## 8. Monitoring

The initial monitoring strategy may use explicit polling for an individual resource:

- `enable_monitor(interval=...)`
- `disable_monitor()`
- `add_listener(callback)`

Polling repeatedly queries metadata and compares observations before dispatching change events. It can consume substantial CPU, I/O and battery, especially at short intervals. It is intended only for a small number of critical resources, not whole trees or large resource collections.

Monitoring must be opt-in, stoppable, resource-scoped, and explicit about polling cost and missed/intermediate changes. Native OS notification backends may be added later behind provider capabilities; they must not be falsely represented as universally available.

## 9. Current implementation status

The following describes code that exists now, not the target architecture above.

- Model: `File`, `Directory`, `FSResourceTree`; generic metadata and hierarchy; specialized dict/JSON/XML serialization.
- Materialization: `validate_path()` and `resource_from_path()` classify and materialize one existing entry.
- Provider: one `FilesystemProvider`, explicitly configured with a physical root and logical Directory root.
- Public physical operations: `create()`, `exists()`, `delete()`, `copy()`, `move()` and `rename()`; provider also implements modeled recursive deletion and explicit `purge()`. Copy reproduces the modeled subtree only, assigns fresh UIDs and refuses existing targets; move/rename preserve UIDs. Cross-volume moves are not emulated.
- In-memory operations: logical `path()`, `walk()`, `find()` and ancestor traversal.
- Implemented: immutable `PhysicalProfile`, provider-backed `profile()` on File/Directory, UTC observation timestamps, explicit cache update, and distinct absent-versus-query-error behavior.
- Implemented: public physical directory scanning via `operations.scan()` with recursive discovery, exclusions, additive reconciliation, no-follow entry classification and configurable error handling.
- Implemented: public copy/move/rename operations. The local provider uses descriptor-relative POSIX move and opaque regular-file copy where available; directory copy is model-driven and creates destination directories exclusively. The Windows branch remains path-based. These operations are not atomic transactions against hostile concurrent filesystem mutation.
- Implemented: `readable()`, `writable()` and `executable()` provider-backed checks for the current process identity, with POSIX effective-ID use where available and documented Windows limitations. These are observations, not authorization guarantees.
- Not implemented yet: platform-specific provider classes and loader, arbitrary-principal access evaluation, monitoring/listeners and change events.

The provider source uses filesystem metadata/stat calls, directory enumeration, entry creation and deletion. These are filesystem-management operations, not direct file-content access APIs. Opaque filesystem-level copy is permitted as a management operation even if the operating system internally transfers file bytes. The package does not expose content reading, content writing, streaming or content-based hashing.

## 10. Required platform validation

The required matrix is GNU/Linux, Termux and Windows. Tests must cover both shared semantics and provider-specific differences. Unsupported capabilities must be tested as explicit failures rather than silently skipped or emulated with unsafe behavior.

Security tests must cover symlink/reparse handling, root confinement, path traversal, race-sensitive behavior where supported, and the guarantee that package-level operations expose no direct file-content read/write/append/overwrite/stream/hash access. Opaque provider-level copy is explicitly exempt from that direct-content-access prohibition: it may use operating-system copy primitives, but must not expose transferred bytes or add content accessors to File.
