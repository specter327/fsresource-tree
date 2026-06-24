import fsresource_tree as fs



def test_filesystem():

    tree = fs.ResourceTree(name="System")
    root = fs.Directory("/")
    file = fs.File(name="hello", extension="txt")
    tree.register(root)
    tree.register(file, parent=root)

    assert file.parent == root