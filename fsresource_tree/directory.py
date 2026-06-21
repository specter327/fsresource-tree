from resourcetree import Container



class Directory(Container):


    def __init__(
        self,
        name,
        parent=None,
        uid=None,

        permissions="755",
        owner=None
    ):

        super().__init__(
            name,
            parent,
            uid
        )


        self.permissions = permissions

        self.owner = owner