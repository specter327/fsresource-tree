# Roadmap

This roadmap distinguishes the current implementation from the intended architecture. Work proceeds incrementally; do not introduce the entire target API in one release.

## Phase 1 — Stabilize the current foundation

- [ ] Complete the audit of filesystem operations against the strict no-file-content-I/O boundary.
- [ ] Keep model-only operations free of implicit filesystem access.
- [ ] Strengthen semantic exceptions and preflight guarantees for existing create/delete/purge operations.
- [ ] Keep GNU/Linux, Termux and Windows behavior covered by tests.
- [ ] Complete and integrate the current stacked PR chain only after review and CI are green.

## Phase 2 — Provider contract and platform selection

- [x] Define a minimal structural provider contract based on capability declarations.
- [x] Expose immutable per-instance provider capability reporting.
- [x] Validate each requested operation independently and raise a semantic unsupported-operation exception.
- [ ] Extend the contract when copy/move/rename and discovery operations are implemented.
- [x] Separate the provider interface from the current local implementation.
- [ ] Separate platform implementations once their distinct semantics are specified.
- [ ] Implement `LinuxProvider`, `TermuxProvider` and `WindowsProvider`.
- [ ] Add a dynamic loader/factory that detects the runtime environment and raises an explicit unsupported-platform exception when no provider exists.
- [ ] Keep additional providers (for example, `MacOSProvider`) possible without claiming current support.
- [ ] Model filesystem capabilities separately from operating-system identity; do not assume Linux means ext or Windows means NTFS.

## Phase 3 — Physical metadata and profiles

- [x] Define immutable File/Directory profile snapshots with observation timestamps.
- [x] Implement provider-backed `profile()` using metadata APIs only.
- [x] Make cache refresh/model synchronization explicit.
- [x] Distinguish absent observations from query failures; preserve permission and I/O errors.
- [ ] Add common metadata fields where available while retaining native/provider-specific details.
- [ ] Implement effective access checks (`is_readable()`, `is_writable()`, `is_executable()`) against an explicit or documented security identity.

## Phase 4 — Explicit filesystem management

- [ ] Implement `copy()`, `move()` and `rename()` through providers.
- [ ] Define precise virtual-model reconciliation behavior for each physical operation.
- [ ] Keep destructive operations explicit and document scope, preconditions, partial-failure behavior and irreversible effects.
- [ ] Keep modeled recursive deletion separate from explicit purge of unknown physical descendants.
- [ ] Add semantic exceptions for unsupported operations, conflicts, permissions and unsafe paths.

## Phase 5 — Discovery and model operations

- [ ] Implement physical directory enumeration and recursive scan/materialization with explicit exclusions and error policy.
- [ ] Define reconciliation when physical entries and virtual resources differ.
- [ ] Keep traversal, search, filtering, grouping and analysis over materialized resource collections and the FSResourceTree index.
- [ ] Avoid making every high-level operation perform a fresh recursive filesystem walk.

## Phase 6 — Monitoring

- [ ] Implement opt-in per-resource polling and change listeners.
- [ ] Make interval, stop behavior, callbacks and event payloads explicit.
- [ ] Warn that polling can consume substantial CPU, I/O and battery; recommend it only for a small number of critical resources, never whole trees or large collections.
- [ ] Add native notification backends only where provider capabilities support them.

## Non-negotiable constraints

- Never expose direct file-content read/write/append/overwrite/stream/hash APIs. Opaque filesystem-level copy remains an explicitly permitted management operation; OS-internal byte transfer does not turn it into a caller-facing content API.
- Never hide destructive physical mutations behind model construction, serialization, traversal or search.
- Never silently substitute an unsupported provider or capability.
- Never represent cached metadata as a guaranteed live view of the filesystem.
- Never force platform/filesystem-specific behavior into a false uniform abstraction.
