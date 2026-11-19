# Format classification and search

Format categories provide semantic extension-based filtering without reading file contents.

```python
from fsresourcetree import FormatTypes, resource_from_path, operations

root = resource_from_path("/srv/media")
root.scan(recursive=True)

# Flat list of matching File resources, in depth-first order.
images = operations.find(root, format=(FormatTypes.IMAGE,))
for image in images:
    print(image.path())

# Preserve the directory hierarchy in a detached, filtered model.
image_tree = operations.filter_tree(root, format=FormatTypes.IMAGE)

# Explicit extensions can be used alone or combined with categories.
pdfs = operations.find(root, extensions=(".pdf",))
documents_and_images = operations.find(
    root, format=(FormatTypes.DOCUMENT, FormatTypes.IMAGE)
)
root.close_provider()
```

## Semantics

- Scanning and filtering are separate: scan discovers physical entries; search operates on the in-memory model.
- Format classification uses the modeled file extension only. It does not inspect MIME types, file signatures or file contents.
- Extension comparisons are case-insensitive. A leading dot is optional for explicit extension filters.
- `find(resource, target)` retains its historical exact-name behavior and returns the first match or `None`.
- `find(resource, format=...)` returns a flat list of matching `File` objects.
- `filter_tree(directory, ...)` returns a detached hierarchy containing matching files and only directories that lead to matches. The requested root remains present even when there are no matches.
- Neither operation changes the source hierarchy or the physical filesystem.
- Symbolic links are not classified as regular files and are omitted from filtered trees.
- Categories are registered in `FORMAT_EXTENSIONS`; applications can inspect the immutable built-in mapping and supply explicit extensions for additional formats.

The registry is an extension-based convenience, not a content-type security boundary. An extension does not prove that a file's bytes conform to that format.
