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

The diagram reflects the current public architecture. `LinuxProvider`, `TermuxProvider` and `WindowsProvider` are registered guarded specializations selected by `ProviderLoader`. Linux and Termux share POSIX descriptor-relative behavior; Windows uses the shared path-based implementation. They are not three independently implemented backends.

### Generic core

`resourcetree` owns identity, metadata, timestamps, parent/children relationships, generic traversal, optional forest management, derived indexing and generic serialization. It has no filesystem path or operating-system semantics.

### Filesystem model

- `File(Asset)` represents a file entry.
- `Directory(Container)` represents a directory and owns child resource relationships.
- `FSResourceTree(ResourceTree)` optionally indexes and manages one or more Directory roots.
- Resources can exist without an `FSResourceTree`; the tree is a manager, not the physical filesystem.
- Model traversal, search, filtering and serialization operate on resource objects and must not silently perform physical I/O.

Paths are inputs to validation and provider operations. Resource objects are the working model. A physical path is not the identity of a resource and should not be confused with its logical `Resource.path()`.

## Hierarchy traversal and navigation

Traversal is an in-memory model operation and must not trigger filesystem I/O.
The generic core provides iterative depth-first traversal for a Resource,
Container or ResourceTree. The filesystem specialization keeps its stricter
resource-type validation while exposing the same preorder/postorder interface
on Directory, File and FSResourceTree.

- Preorder visits a resource before its descendants.
- Postorder visits descendants before their parent and is suitable for
  bottom-up processing such as calculating aggregate directory state.
- Ancestor navigation follows parent links independently of descendant
  traversal, either from the immediate parent toward the root or root-to-parent.
- Multi-root trees preserve root order; sibling order is preserved within each
  subtree.
- ScanResult.walk() traverses the complete modeled subtree rooted at the
  scanned directory. Its discovered tuple remains the scan delta only.

All walkers are lazy and iterative. They validate parent/child consistency and
reject cycles or duplicate references rather than silently producing partial
results. The filesystem walker additionally rejects non-filesystem resource
types in a directory hierarchy.

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

The public `profile()` operation queries the provider and returns a point-in-time profile for a File or Directory. It may either:

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

`ProviderLoader` detects the runtime platform and returns the registered provider. Unsupported runtimes raise `UnsupportedPlatformError`; the loader does not silently fall back to another platform implementation.

Termux is identified as its own execution environment even where it can reuse POSIX primitives. It may have different storage permissions, mount visibility and Android-specific restrictions.

The current required compatibility targets remain GNU/Linux, Termux and Windows. macOS is an extensibility target only until it is explicitly added to the supported test matrix. Termux has a dedicated guarded provider class and runtime selection, while reusing the shared POSIX implementation; actual Termux runtime validation remains an outstanding release task.

### Operating system is not filesystem format

An OS provider and a filesystem format are different layers. Linux may access ext4, FAT, NTFS and other mounted filesystems; Windows may access NTFS, FAT/exFAT and others. The provider must not assume that one operating system implies one filesystem format.

The provider should expose the capabilities and metadata actually available for the mounted volume/resource. It must not fabricate unsupported properties or normalize away meaningful differences. If an operation or property is unsupported, report that explicitly.

### Provider contract

The public structural interface is FilesystemProviderProtocol, which requires only an immutable ProviderCapabilities declaration. Operation services validate the specific requested operation against that provider's declared capabilities and callable method; providers do not have to implement unrelated or unsupported operations. Unsupported requests raise UnsupportedOperationError. Each configured provider reports its runtime platform identifier, known filesystem format (or None when it cannot be identified reliably), race-resistance guarantee, supported operations and available metadata fields. Capabilities describe the configured implementation; they are not inferred from the operating system alone.

The provider contract owns physical operations and queries, including:

- Resolve a resource relative to an explicitly configured physical root.
- Check existence and classify physical entries.
- Create, delete, copy, move and rename entries.
- Query metadata and effective access.
- Enumerate physical directory entries for discovery/materialization.
- Report supported capabilities and provider-native details.

Providers must not own the in-memory tree's search, filtering or indexing algorithms. Those belong to the model/operations layer.

The configured root is a security boundary. Providers must validate resource ancestry and path components, reject unsafe link/reparse traversal according to their guarantees, and document race resistance. A checked path returned for diagnostics must not be treated as a safe substitute for a provider operation.

On POSIX, descriptor-relative operations prevent symlink substitution, but they are not an atomic transaction against concurrent renames of already-opened directories. If an untrusted actor can rename a traversed descendant (for example, `root/a/b`) outside the configured root after it has been opened, later create, delete or purge operations may act through that descriptor on the moved tree. The configured root, its ancestors, and every traversed parent/descendant directory must therefore be protected against hostile concurrent renames or mutations. The provider is not an OS sandbox. On Windows, path-based validation checks existing components for symbolic links and reparse points before create, delete and purge I/O, but cannot prevent a hostile concurrent replacement after validation. Full Windows handle-relative operations remain outside the current security claim.

## Symbolic-link policy

Symbolic links are explicit model resources, not aliases for their targets.
`SymbolicLink` preserves the entry name and target returned by `os.readlink()`.
On Windows, ordinary extended-length drive and UNC prefixes are normalized
for a portable user-facing representation; other device namespaces are kept
unchanged. It is terminal: scanning never descends through it,
and the resource does not expose file/directory mutation operations.

`Directory.scan(symlink_policy=...)` supports:

- `skip` (default): omit symbolic links and record them in
  `ScanResult.skipped`.
- `accept`: attach a `SymbolicLink` resource without resolving
  or traversing its destination. Reparse points that are not reported as
  symbolic links remain skipped.
- `raise`: raise when a symbolic link or reparse point is encountered.

The selected root has a separate opt-in:
`resource_from_path(path, follow_symlinks=True)` resolves the chosen
root to its canonical target before configuring the provider. This does not
change descendant policy.

Following descendant links is not supported. It requires provider-level
logical-to-physical alias mapping and race-resistant root confinement; checking
`Path.resolve()` alone is not a security boundary. Until that provider
work is implemented, no scan policy follows descendant links.

## 5. Operations and side effects

Operations are explicit. Constructing a resource, attaching it to a Directory, registering it in an FSResourceTree, serializing it, or searching it must not change the physical filesystem.

Physical operations require a provider. The public API currently includes `create()`, `exists()`, `delete()`, `copy()`, `move()`, `rename()`, `profile()` and `scan()`. Destructive operations are never hidden side effects and must document exactly what they can change.

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

The public `scan()` operation delegates physical enumeration to the configured provider through `scan_entries()`, then materializes File/Directory resources plus terminal SymbolicLink resources when requested. POSIX enumeration is anchored to the provider's pinned root and directory descriptors, uses no-follow metadata queries, and verifies opened child-directory identity. Windows currently retains path-based enumeration and its documented concurrent-replacement limitation; it is not represented as race-resistant. The scanner does not use `os.scandir()` on resolved paths. It supports recursive or shallow scans, name/callback exclusions and configurable error handling. Symbolic links and reparse points are never followed during descendant discovery. The scan policy is explicit: `symlink_policy="skip"` (default) records and skips them, `"accept"` materializes symbolic links without traversing their targets, and `"raise"` aborts. Unsupported special entries are skipped. Matching existing resources are reused; new resources are attached to the model and any mounted tree index. The scan is additive: it does not prune stale model children or delete physical entries.

Model traversal, recursive iteration, search, filtering, grouping and analysis work over already materialized resource collections and the FSResourceTree index. They do not repeatedly query the filesystem. This separation avoids making every high-level operation an uncontrolled filesystem walk.

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

For directories, execute means search/traversal permission. Missing entries return `False`; symlinks/reparse points and resource-type mismatches are rejected. For descriptor-relative traversal, the local POSIX provider uses search-only directory descriptors (`O_PATH`/`O_SEARCH` where available), so checking a known file does not incorrectly require read permission on every parent directory. The `access` operation is advertised only when the runtime exposes descriptor-relative `os.access()` with no-follow support. If those primitives are unavailable, the provider omits `access` from its capabilities and the public helpers raise `UnsupportedOperationError`; it never falls back to a path-based check that would bypass the pinned root. Every result is subject to TOCTOU: permissions, ACLs, mount state or the entry itself can change before a subsequent operation. The operation itself remains authoritative and may still fail.

## 8. Monitoring

The current implementation provides opt-in polling scoped to a `Directory`:

- `directory.enable_monitor(interval=..., recursive=True)`
- `directory.disable_monitor(timeout=None)`
- `directory.add_listener(callback)` / `directory.remove_listener(callback)`
- `directory.monitor_enabled`

The monitor resolves the provider already bound to the selected directory. It periodically invokes the existing scan/profile operations and compares physical metadata snapshots. It emits immutable `FilesystemChangeEvent` objects with `CREATED`, `DELETED`, `MODIFIED` or `MOVED` types. `MOVED` is emitted when a modeled resource is renamed or moved through the library while retaining its UID; events include `previous_path` and `current_path`. Physical file/directory type replacements detach the stale model node, materialize the replacement type, and produce deletion/creation events. Any monitors attached to the stale directory or its descendants are stopped before detachment, preventing orphaned workers from retaining the provider. The initial scan establishes a baseline and emits no historical creation events. It does not read file contents.

Listener callbacks execute on the monitor thread; callbacks should return quickly. Listener exceptions and polling errors are logged and isolated so they do not terminate the worker. The provider must remain open for the monitor lifetime; provider closure is rejected while any monitor using that provider is active. Stop all monitors before closing the provider.

This is a best-effort metadata observer, not an atomic event journal. External rename/move operations not reflected in the model may appear as deletion plus creation. Changes that occur and revert between polls, and same-size content changes that preserve observable metadata, may be missed. Access-time-only changes are ignored. Polling cost scales with the number of modeled resources and interval; recursive monitoring is intended for relevant subtrees, not large trees or high-frequency whole-filesystem observation.

Native OS notification backends are not implemented.

## 9. Current implementation status

The following describes code that exists now, not the target architecture above.

- Model: `File`, `Directory`, `FSResourceTree`; generic metadata and hierarchy; specialized dict/JSON/XML serialization.
- Materialization: `validate_path()` and `resource_from_path()` classify and materialize one existing entry. Both reject symbolic links by default; `resource_from_path(..., follow_symlinks=True)` explicitly resolves only the selected root path to its canonical target. This opt-in does not enable following descendant links.
- Provider contract: structural `FilesystemProviderProtocol` and immutable per-instance `ProviderCapabilities`.
- Provider selection: `ProviderLoader` detects GNU/Linux, Termux or Windows and instantiates `LinuxProvider`, `TermuxProvider` or `WindowsProvider`. These classes currently share the audited `FilesystemProvider` backend and enforce runtime compatibility; common operations are not duplicated without a demonstrated platform-specific need. Unsupported runtimes fail with `UnsupportedPlatformError`.
- Provider lifecycle: a provider is explicitly configured with a physical root and logical Directory root; `resource_from_path()` uses the loader for top-level directories.
- Public physical operations: `create()`, `exists()`, `delete()`, `copy()`, `move()` and `rename()`; provider also implements modeled recursive deletion and explicit `purge()`. Copy reproduces the modeled subtree only, assigns fresh UIDs and refuses existing targets; move/rename preserve UIDs. Cross-volume moves are not emulated.
- In-memory operations: logical `path()`, `walk()`, `find()` and ancestor traversal.
- Implemented: immutable `PhysicalProfile`, provider-backed `profile()` on File/Directory, UTC observation timestamps, explicit cache update, and distinct absent-versus-query-error behavior.
- Implemented: public physical directory scanning via `operations.scan()` with recursive discovery, exclusions, additive reconciliation, no-follow entry classification and configurable error handling.
- Implemented: public copy/move/rename operations. The local provider uses descriptor-relative POSIX move and opaque regular-file copy where available; directory copy is model-driven and creates destination directories exclusively. The Windows branch remains path-based. These operations are not atomic transactions against hostile concurrent filesystem mutation.
- Implemented conditionally: `readable()`, `writable()` and `executable()` provider-backed checks for the current process identity. POSIX providers advertise the `access` operation only when descriptor-relative, no-follow checks are available in the Python runtime; Windows retains its documented path-based host semantics. Unsupported runtimes omit the capability and fail explicitly rather than weakening root confinement. These are observations, not authorization guarantees.
- Implemented: opt-in directory-scoped metadata polling, stoppable background workers, listener registration/removal and immutable created/deleted/modified/moved events. Monitoring reconciles physical file/directory type replacements, reports modeled rename/move paths, uses the provider-resolved scan/profile API, does not read file contents, and is best-effort rather than an atomic event journal.
- Not implemented yet: independently specialized platform backends where distinct OS semantics require them, arbitrary-principal access evaluation and native OS notification backends.

The provider source uses filesystem metadata/stat calls, directory enumeration, entry creation and deletion. These are filesystem-management operations, not direct file-content access APIs. Opaque filesystem-level copy is permitted as a management operation even if the operating system internally transfers file bytes. The package does not expose content reading, content writing, streaming or content-based hashing.

## 10. Required platform validation

The required matrix is GNU/Linux, Termux and Windows. Tests must cover both shared semantics and provider-specific differences. Unsupported capabilities must be tested as explicit failures rather than silently skipped or emulated with unsafe behavior.

Security tests must cover symlink/reparse handling, root confinement, path traversal, race-sensitive behavior where supported, and the guarantee that package-level operations expose no direct file-content read/write/append/overwrite/stream/hash access. Opaque provider-level copy is explicitly exempt from that direct-content-access prohibition: it may use operating-system copy primitives, but must not expose transferred bytes or add content accessors to File.
