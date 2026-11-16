# Physical directory scanning

`scan()` discovers filesystem descendants and materializes them as `Directory` and `File` resources. It is an explicit physical observation; ordinary model traversal and search remain in-memory operations.

```python
from fsresource_tree import Directory, FilesystemProvider
from fsresource_tree.operations import scan

root = Directory("workspace")
with FilesystemProvider("/srv/workspace", resource_root=root) as provider:
    result = scan(root, provider=provider, recursive=True,
                  excluded_names={".git", "__pycache__"}, on_error="raise")

print(f"New resources: {result.count}")
print(f"Skipped entries: {len(result.skipped)}")
```

## Semantics

- Scanning is additive. Existing model children are reused when names and physical entry types match.
- A model/physical type conflict raises `TypeError`; it is not silently replaced.
- The scan never removes stale model children and never deletes filesystem entries.
- `recursive=False` observes only direct children.
- `excluded_names` excludes matching entries and entire excluded subtrees.
- `exclude(name, is_directory)` supports a custom exclusion predicate.
- `on_error="raise"` propagates I/O and model conflicts. `"skip"` records `(path, reason)` pairs in `ScanResult.skipped`.
- Symbolic links, Windows reparse points and special entries are skipped. File contents are never opened or read.
- If the root belongs to an `FSResourceTree`, newly attached resources update the tree index through the normal hierarchy API.

## Security note

The provider validates the configured root and resource ancestry. Scanning uses no-follow metadata observations and revalidates each candidate before materialization. This is not an atomic snapshot against hostile concurrent filesystem mutations; the provider is not an OS sandbox.
