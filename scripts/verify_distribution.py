"""Install each built filesystem artifact with the pinned core in isolation."""

from __future__ import annotations

import argparse
import glob
import os
from pathlib import Path
import subprocess
import tempfile
import venv


def python_in(environment: Path) -> Path:
    executable = "python.exe" if os.name == "nt" else "python"
    scripts = "Scripts" if os.name == "nt" else "bin"
    return environment / scripts / executable


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-wheel", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()

    artifacts = sorted(glob.glob("dist/*.whl") + glob.glob("dist/*.tar.gz"))
    if len(artifacts) != 2:
        raise SystemExit(f"expected exactly one wheel and one sdist, got: {artifacts}")

    for artifact in artifacts:
        with tempfile.TemporaryDirectory(prefix="fsresource-distribution-smoke-") as temporary:
            root = Path(temporary)
            environment = root / "venv"
            venv.EnvBuilder(with_pip=True).create(environment)
            python = python_in(environment)
            subprocess.check_call([str(python), "-m", "pip", "install", args.core_wheel])
            subprocess.check_call([str(python), "-m", "pip", "install", "--no-deps", artifact])
            code = (
                "from importlib import metadata; import fsresourcetree as package; "
                f"assert metadata.version('fsresourcetree') == {args.version!r}; "
                "from fsresourcetree import Directory, File, FSResourceTree, FilesystemProvider; "
                "root = Directory('root'); File('sample', extension='txt', parent=root); "
                "tree = FSResourceTree(roots=[root]); "
                "assert isinstance(FSResourceTree.from_dict(tree.to_dict()), FSResourceTree); "
                "assert package.__file__ is not None and ('site-packages' in package.__file__ or 'dist-packages' in package.__file__); "
                "print(package.__file__)"
            )
            result = subprocess.run(
                [str(python), "-c", code],
                cwd=root,
                check=True,
                text=True,
                capture_output=True,
            )
            print(f"PASS {Path(artifact).name}: {result.stdout.strip()}")


if __name__ == "__main__":
    main()
