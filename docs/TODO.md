# Roadmap

This roadmap records the implementation that exists in the repository and separates it from remaining validation or extension work. A checked item means the capability is implemented; it does not imply that every platform has identical guarantees.

## Phase 1 — Stabilize the foundation

- [x] Keep model-only construction, hierarchy management, traversal, search and serialization independent of implicit filesystem mutations.
- [x] Keep physical file-content read/write/append/overwrite/stream/hash APIs outside the package boundary.
- [x] Keep opaque provider-level filesystem copy as an explicit management operation that does not expose transferred bytes.
- [ ] Complete the security review of destructive operations, race-sensitive behavior and partial-failure cleanup.
- [ ] Validate GNU/Linux and Windows through the automated matrix, and validate Termux on a real Android/Termux runtime.
- [ ] Document any platform-specific guarantee that cannot be tested in CI.

## Phase 2 — Provider contract and platform selection

- [x] Define the structural `FilesystemProviderProtocol` and immutable `ProviderCapabilities`.
- [x] Validate each requested operation against declared capabilities and the provider's callable method.
- [x] Implement guarded `LinuxProvider`, `TermuxProvider` and `WindowsProvider` specializations.
- [x] Implement `ProviderLoader` runtime detection and integrate it with `resource_from_path()`.
- [x] Keep operating-system identity separate from filesystem-format identification.
- [ ] Add an independent platform backend only when a concrete semantic or native-API difference justifies it.
- [ ] Add macOS only after an explicit support decision and platform test coverage.

The Linux and Termux classes currently share POSIX descriptor-relative behavior. Windows uses the shared path-based implementation. These are guarded runtime specializations, not three independently implemented backends.

## Phase 3 — Physical metadata and access observations

- [x] Define immutable `PhysicalProfile` snapshots with UTC observation timestamps.
- [x] Implement provider-backed metadata profiling without reading file contents.
- [x] Make cache updates explicit through `update_cache=True`.
- [x] Distinguish an absent entry from permission and I/O failures.
- [x] Implement `readable()`, `writable()` and `executable()` plus resource methods and aliases.
- [ ] Extend common metadata only where the provider can report it accurately; preserve native details rather than fabricating portability.

Access checks describe the current process identity and are advisory point-in-time observations. They are not authorization guarantees for later operations.

## Phase 4 — Explicit filesystem management

- [x] Implement provider-backed `create()`, `exists()` and `delete()`.
- [x] Implement `copy()`, `move()` and `rename()`.
- [x] Preserve resource UIDs for move/rename and allocate fresh identities for copies.
- [x] Keep modeled recursive deletion separate from explicit `purge()` of unmodeled physical descendants.
- [x] Expose instance-level operations on `File` and `Directory`, with provider resolution from the bound root.
- [ ] Finish the cross-platform security and partial-failure audit; do not imply transactional behavior where it is not provided.

Directory copy reproduces the modeled subtree only. Call `scan()` first when all physical descendants must be represented in the model. Cross-volume moves are not emulated.

## Phase 5 — Discovery and model operations

- [x] Implement public physical directory discovery through `scan()` and `Directory.scan()`.
- [x] Support recursive or shallow scans, name/callback exclusions and configurable error handling.
- [x] Skip symbolic links, reparse points and unsupported special entries.
- [x] Reuse matching resources and add newly discovered entries without silently pruning stale model children.
- [x] Keep traversal, search and logical path operations in-memory.
- [ ] Consider an explicit reconciliation/pruning operation only with separately documented destructive semantics.

## Phase 6 — Monitoring

- [x] Implement opt-in directory-scoped metadata polling.
- [x] Implement listener registration/removal and immutable `CREATED`, `DELETED`, `MODIFIED` and `MOVED` events.
- [x] Make monitor lifecycle explicit and prevent provider closure while dependent monitors are active.
- [x] Reconcile modeled rename/move and physical file/directory type replacement cases.
- [x] Document polling cost, best-effort semantics and changes that cannot be detected from metadata.
- [ ] Add native OS notification backends only when provider capabilities and maintenance cost justify them.

## Phase 7 — Release engineering and completion

- [ ] Keep the version source, package metadata, release script and distribution verification in agreement.
- [ ] Build and inspect both wheel and sdist before creating a Git release tag.
- [ ] Verify each built artifact in an isolated environment against the supported generic-core dependency.
- [ ] Confirm the full CI matrix and end-to-end demonstration pass for the release candidate.
- [ ] Publish a tagged release only after the checks above succeed.

## Non-negotiable constraints

- Never expose direct file-content read/write/append/overwrite/stream/hash APIs.
- Never hide physical mutations behind construction, serialization, traversal or search.
- Never silently substitute an unsupported provider or capability.
- Never represent cached metadata as a guaranteed live filesystem view.
- Never claim a stronger security or race-resistance guarantee than the selected provider actually provides.
- Never force platform/filesystem-specific behavior into a false uniform abstraction.
