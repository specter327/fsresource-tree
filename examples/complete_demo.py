#!/usr/bin/env python3
"""End-to-end, safe demonstration of the currently implemented fsresourcetree API.

Run from the repository root after installing the development versions of
resourcetree and fsresourcetree. All physical mutations are confined to a
TemporaryDirectory that is removed automatically when the program exits.

This example's scan() function is demonstration code, not a public library API.
The library itself currently provides path validation/materialization for one
entry at a time; it does not yet expose a public recursive scanner.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fsresourcetree import (
    Directory,
    FSResourceTree,
    File,
    resource_from_path,
    validate_path,
)
from fsresourcetree.operations import (
    create,
    delete,
    exists,
    find,
    path as logical_path,
    profile,
    walk,
)
from fsresourcetree.renderers import mermaid


def scan(directory: Directory, physical_path: Path) -> int:
    """Populate a Directory model from its physical children, without file I/O."""
    discovered = 0
    with os.scandir(physical_path) as entries:
        for entry in sorted(entries, key=lambda item: item.name.casefold()):
            entry_path = Path(entry.path)

            # Never follow symbolic links. Special entries are intentionally
            # excluded from this File/Directory-only model.
            if entry.is_symlink():
                print(f"  [SKIP symlink] {entry.name}")
                continue
            if not (entry.is_dir(follow_symlinks=False) or entry.is_file(follow_symlinks=False)):
                print(f"  [SKIP special entry] {entry.name}")
                continue

            resource = resource_from_path(entry_path, parent=directory)
            discovered += 1
            if isinstance(resource, Directory):
                discovered += scan(resource, entry_path)

    return discovered


def show_tree(root: Directory) -> None:
    for resource in walk(root):
        kind = "DIR " if isinstance(resource, Directory) else "FILE"
        print(f"  {kind} {logical_path(resource)}")


def main() -> None:
    print("=" * 72)
    print("FSRESOURCE-TREE — COMPLETE IMPLEMENTED-FEATURE DEMONSTRATION")
    print("=" * 72)

    # Fixture creation uses Python's standard library. fsresourcetree does
    # not read or write file contents; it only models entries and metadata.
    with tempfile.TemporaryDirectory(prefix="fsresourcetree-demo-") as temp:
        physical_root = Path(temp)
        (physical_root / "documents").mkdir()
        (physical_root / "reports" / "annual").mkdir(parents=True)
        (physical_root / "README.txt").write_text(
            "Fixture created by the demo using pathlib.\n", encoding="utf-8"
        )
        (physical_root / "documents" / "design.md").write_text(
            "# Design fixture\n", encoding="utf-8"
        )
        (physical_root / "reports" / "annual" / "summary.csv").write_text(
            "year,total\n2026,42\n", encoding="utf-8"
        )

        print("\n[1/9] Validate and materialize the physical root")
        assert validate_path(physical_root, expected_type=Directory) is Directory
        root = resource_from_path(physical_root)
        assert isinstance(root, Directory)
        print(f"  physical root: {physical_root}")
        print(f"  logical root:  {root.name!r} ({type(root).__name__})")

        print("\n[2/9] Discover physical descendants (scanner belongs to this demo)")
        discovered = scan(root, physical_root)
        print(f"  materialized descendants: {discovered}")

        print("\n[3/9] Build the specialized ResourceTree")
        tree = FSResourceTree(roots=[root], name="filesystem-demo")
        print(f"  tree: {tree!r}")
        print(f"  indexed resources: {len(tree)}")
        assert len(tree) == discovered + 1

        print("\n[4/9] Traverse, calculate logical paths and search")
        show_tree(root)
        summary = find(root, "summary")
        assert isinstance(summary, File)
        print(f"  exact-name lookup 'summary': {summary.filename()}")
        print(f"  logical path: {logical_path(summary)}")
        assert tree.get(summary.uid) is summary
        print(f"  indexed by UID: {tree.get(summary.uid) is summary}")

        print("\n[5/9] Inspect physical metadata (stat-style; no content access)")
        with root.filesystem_provider as provider:
            print(f"  provider capabilities: {provider.capabilities}")
            snapshot = profile(summary, provider=provider, update_cache=True)
            print(f"  cached profile: {summary.physical_profile is snapshot}")
            print(f"  profile: {snapshot.to_dict()}")
            assert snapshot.exists and snapshot.entry_type == "file"
            assert exists(summary, provider=provider)

            print("\n[6/9] Create physical resources through the provider")
            generated_dir = Directory("generated", parent=root)
            generated_file = File("hello", extension="txt", parent=generated_dir)
            created_directory = create(generated_dir, provider=provider, recursive_children=True)
            assert created_directory
            assert exists(generated_dir, provider=provider)
            assert exists(generated_file, provider=provider)
            generated_profile = generated_file.profile(provider=provider)
            print(f"  created directory: {provider.resolve(generated_dir)}")
            print(f"  created file:      {provider.resolve(generated_file)}")
            print(f"  generated profile: {generated_profile.to_dict()}")
            assert generated_profile.exists

            print("\n[7/9] Serialize and reconstruct the specialized model")
            json_value = tree.to_json(indent=2)
            json_restored = FSResourceTree.from_json(json_value)
            xml_value = tree.to_xml()
            xml_restored = FSResourceTree.from_xml(xml_value)
            assert len(json_restored) == len(tree) == len(xml_restored)
            assert isinstance(json_restored.roots[0], Directory)
            assert isinstance(xml_restored.roots[0], Directory)
            print(f"  JSON round-trip: {len(json_restored)} resources")
            print(f"  XML round-trip:  {len(xml_restored)} resources")
            print(f"  JSON characters: {len(json_value)}")
            print(f"  XML characters:  {len(xml_value)}")

            print("\n[8/9] Render the model as Mermaid")
            diagram = mermaid(root)
            print(diagram)

            print("\n[9/9] Delete the resources created by this demonstration")
            deleted_file = delete(generated_file, provider=provider)
            assert deleted_file
            assert not exists(generated_file, provider=provider)
            deleted_directory = delete(generated_dir, provider=provider)
            assert deleted_directory
            assert not exists(generated_dir, provider=provider)
            print("  generated file deleted")
            print("  generated directory deleted")

        print("\nAll demonstration steps completed.")
        print("The temporary physical filesystem will now be removed automatically.")


if __name__ == "__main__":
    main()
