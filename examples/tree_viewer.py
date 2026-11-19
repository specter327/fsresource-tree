#!/usr/bin/env python3
"""Interactively scan a directory and display its resources as an ASCII tree.

Run from the repository root after installing fsresource-tree:
    python examples/tree_viewer.py

The viewer only displays resource names and types; it does not read file
contents or modify the filesystem. Symbolic links are not followed by default.
"""

from __future__ import annotations

from pathlib import Path

from fsresourcetree import Directory, File, SymbolicLink, resource_from_path


def print_tree(directory: Directory, *, prefix: str = "") -> tuple[int, int]:
    """Print a directory and its descendants; return (directory_count, file_count)."""
    directories = 1
    files = 0
    children = sorted(
        directory.children,
        key=lambda resource: (
            not isinstance(resource, Directory),
            resource.name.casefold(),
        ),
    )
    for index, resource in enumerate(children):
        is_last = index == len(children) - 1
        connector = "└── " if is_last else "├── "
        if isinstance(resource, Directory):
            label = resource.name
        elif isinstance(resource, File):
            label = resource.filename()
        else:
            label = f"{resource.name} -> {resource.target}"
        print(f"{prefix}{connector}{label}")
        if isinstance(resource, Directory):
            child_directories, child_files = print_tree(
                resource,
                prefix=prefix + ("    " if is_last else "│   "),
            )
            directories += child_directories
            files += child_files
        elif isinstance(resource, File):
            files += 1
    return directories, files


def main() -> int:
    print("FSResource Tree — interactive directory explorer")
    raw_path = input("Directory path: ").strip()
    if not raw_path:
        print("No path supplied.")
        return 1

    root_path = Path(raw_path).expanduser()
    follow_root = input("Follow the selected root if it is a symbolic link? [y/N]: ").strip().lower()
    follow_root_symlink = follow_root in {"y", "yes"}
    root: Directory | None = None
    try:
        resource = resource_from_path(root_path, follow_symlinks=follow_root_symlink)
        if not isinstance(resource, Directory):
            print(f"Not a directory: {root_path}")
            return 1
        root = resource
        result = root.scan(
            recursive=True,
            on_error="skip",
            symlink_policy="skip",
        )
        print()
        print(f"{root.name}/")
        directory_count, file_count = print_tree(root)
        print()
        print(
            f"{directory_count} director{'y' if directory_count == 1 else 'ies'}, "
            f"{file_count} file{'s' if file_count != 1 else ''}"
        )
        if result.skipped:
            print(f"Skipped entries: {len(result.skipped)}")
            for path, reason in result.skipped[:10]:
                print(f"  - {path}: {reason}")
            if len(result.skipped) > 10:
                print(f"  ... and {len(result.skipped) - 10} more")
        return 0
    except (OSError, ValueError, TypeError) as error:
        print(f"Unable to explore {root_path}: {error}")
        return 1
    except Exception as error:
        print(f"Filesystem exploration failed: {error}")
        return 1
    finally:
        if root is not None:
            root.close_provider()


if __name__ == "__main__":
    raise SystemExit(main())
