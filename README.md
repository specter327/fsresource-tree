# fsresources-tree

Filesystem implementation using resourcetree.


Example:

```python
import fsresources_tree as fs


root = fs.Directory("/")

file = fs.File(
    "test.txt",
    root,
    content="hello"
)