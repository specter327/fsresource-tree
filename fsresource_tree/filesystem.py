from pathlib import Path

from .directory import Directory
from .file import File



def from_path(path):


    path = Path(path)


    root = Directory(
        path.name
    )


    _load(
        path,
        root
    )


    return root




def _load(
    path,
    node
):


    for item in path.iterdir():


        if item.is_dir():

            directory = Directory(
                item.name,
                node
            )


            _load(
                item,
                directory
            )


        else:

            File(
                item.name,
                node,
                content=item.read_text(
                    errors="ignore"
                )
            )