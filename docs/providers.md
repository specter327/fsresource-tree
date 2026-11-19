# Provider selection and extension

## Current contract

Operation services depend on `FilesystemProviderProtocol`, a runtime-checkable structural protocol. It deliberately requires only a `capabilities` property. An implementation may support a subset of operations; each service validates the requested operation against both the declared capability and its callable method. Unsupported requests raise `UnsupportedOperationError`.

`ProviderCapabilities` is immutable and describes the configured instance:

- `platform`: runtime identifier (`linux`, `termux`, `win32`, or another explicitly implemented identifier).
- `filesystem`: known filesystem format, or `None` when it cannot be identified reliably.
- `race_resistant`: whether the configured implementation uses its descriptor-relative safety mode.
- `operations`: supported physical operation names.
- `metadata_fields`: metadata fields actually exposed by the provider.

Operating-system identity and filesystem format are separate. The loader does not infer ext4, NTFS, FAT or another format from the operating system.

## Runtime selection

`ProviderLoader.load(root, resource_root=directory)` detects the runtime and selects one of the registered providers:

| Runtime | Provider | Current backend |
|---|---|---|
| GNU/Linux | `LinuxProvider` | Shared POSIX descriptor-relative implementation |
| Termux | `TermuxProvider` | Shared POSIX implementation, reported as Termux |
| Windows | `WindowsProvider` | Shared Windows path-based implementation |

The provider classes are explicit guarded specializations, not claims that all three backends are already independently implemented. They reuse the existing `FilesystemProvider` code to avoid premature duplication. A future platform-specific implementation should be introduced when it needs materially different operations, guarantees, metadata or native APIs.

Unsupported runtime identifiers raise `UnsupportedPlatformError`. There is no silent fallback to another platform implementation. `ProviderLoader.provider_class(platform)` can inspect the class registered for a known identifier; its explicit argument does not force `load()` to impersonate a different runtime. `ProviderLoader.load()` always detects the actual runtime.

Top-level `resource_from_path(existing_directory)` delegates provider selection to the loader. Manually constructed roots can opt into the same behavior:

```python
from fsresourcetree import Directory, ProviderLoader

root = Directory("workspace")
provider = ProviderLoader.load("/srv/workspace", resource_root=root)

# Descendant resources resolve the provider through their root.
# Stop all monitors before closing the provider.
root.close_provider()
```

## Extension rules

1. Keep generic model operations, traversal, search and reconciliation outside providers.
2. Keep the provider contract structural and capability-driven; do not require unrelated methods.
3. Add a new platform class only when its runtime or native behavior warrants one.
4. Reuse shared implementation for genuinely common semantics; override only the platform-specific behavior.
5. Report unsupported operations and metadata explicitly. Never emulate them with weaker guarantees without declaring the difference.
6. Do not infer filesystem format from `sys.platform`.
7. Preserve the configured root boundary, no-follow behavior and documented race-resistance limits.
8. Add platform-specific tests and CI coverage before claiming a new compatibility target.

## Current limitations

- Linux, Termux and Windows have explicit provider class identities and loader selection.
- Linux and Termux currently share POSIX descriptor-relative operations; Termux is distinguished by runtime detection and capability reporting.
- Windows currently uses the shared path-based implementation and retains its documented TOCTOU limitations.
- Native OS change-notification backends, macOS support and independent per-platform backends are not implemented.
- The loader is runtime selection, not filesystem-format detection or a security sandbox.
