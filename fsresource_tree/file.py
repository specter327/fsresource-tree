from resourcetree import Asset



class File(Asset):


    def __init__(
        self,
        name,
        parent=None,
        uid=None,

        content=None,

        encoding="utf-8"
    ):


        super().__init__(
            name,
            parent,
            uid,
            content
        )


        self.encoding = encoding


        self.size = (

            len(
                content.encode(encoding)
            )

            if content

            else 0
        )