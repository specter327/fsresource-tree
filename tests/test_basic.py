import fsresource_tree as fs



def test_filesystem():


    root = fs.Directory("/")


    file = fs.File(
        "hello.txt",
        root,
        content="hello"
    )


    assert file.parent == root

    assert file.size == 5