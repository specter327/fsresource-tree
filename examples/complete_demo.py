#!/usr/bin/env python3
"""End-to-end demonstration of the public fsresourcetree API.

Run from the repository root after installing the project dependencies.
All physical mutations are confined to a TemporaryDirectory that is removed
automatically. Fixture file contents are created/read only by this example
using pathlib; fsresourcetree itself operates on entries and metadata.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fsresourcetree import (
    Directory,
    FSResourceTree,
    File,
    copy,
    move,
    rename,
    resource_from_path,
    validate_path,
)
from fsresourcetree.operations import exists, find, path as logical_path, profile, walk
from fsresourcetree.renderers import mermaid


def show_tree(root: Directory) -> None:
    for resource in walk(root):
        kind = "DIR " if isinstance(resource, Directory) else "FILE"
        print(f"  {kind} {logical_path(resource)}")


def main() -> None:
    print("=" * 72)
    print("FSRESOURCE-TREE — PUBLIC API END-TO-END DEMONSTRATION")
    print("=" * 72)

    with tempfile.TemporaryDirectory(prefix="fsresourcetree-demo-") as temporary:
        physical_root = Path(temporary)
        (physical_root / "documents").mkdir()
        (physical_root / "reports" / "annual").mkdir(parents=True)
        (physical_root / "README.txt").write_text("Fixture created by the demo.\n", encoding="utf-8")
        (physical_root / "documents" / "design.md").write_text("# Design fixture\n", encoding="utf-8")
        (physical_root / "reports" / "annual" / "summary.csv").write_text(
            "year,total\n2026,42\n", encoding="utf-8"
        )

        print("\n[1/10] Validate and materialize the physical root")
        assert validate_path(physical_root, expected_type=Directory) is Directory
        root = resource_from_path(physical_root)
        assert isinstance(root, Directory)
        print(f"  physical root: {physical_root}")
        print(f"  logical root:  {root.name!r}")

        try:
            with root.filesystem_provider as provider:
                print("\n[2/10] Discover physical descendants with the public scan() API")
                scan_result = root.scan(recursive=True)
                print(f"  newly materialized resources: {scan_result.count}")
                assert scan_result.count == 6
                assert not scan_result.skipped

                print("\n[3/10] Build and inspect the specialized ResourceTree index")
                tree = FSResourceTree(roots=[root], name="filesystem-demo")
                print(f"  indexed resources: {len(tree)}")
                assert len(tree) == scan_result.count + 1

                print("\n[4/10] Traverse, calculate logical paths and search")
                show_tree(root)
                summary = find(root, "summary")
                design = find(root, "design")
                documents = find(root, "documents")
                assert isinstance(summary, File)
                assert isinstance(design, File)
                assert isinstance(documents, Directory)
                assert tree.get(summary.uid) is summary
                print(f"  summary logical path: {logical_path(summary)}")
                print(f"  summary indexed by UID: {tree.get(summary.uid) is summary}")

                print("\n[5/10] Inspect physical metadata and effective access")
                snapshot = profile(summary, provider=provider, update_cache=True)
                assert snapshot.exists and snapshot.entry_type == "file"
                assert summary.physical_profile is snapshot
                assert exists(summary, provider=provider)
                print(f"  provider capabilities: {provider.capabilities}")
                print(f"  physical profile: {snapshot.to_dict()}")
                print(f"  readable by current process: {summary.readable()}")

                print("\n[6/10] Create a destination and exercise copy / rename / move")
                archive = Directory("archive", parent=root)
                archive.create()
                duplicate = copy(summary, archive, provider=provider, new_name="summary-copy")
                assert isinstance(duplicate, File)
                assert duplicate.uid != summary.uid
                assert exists(duplicate, provider=provider)
                rename(duplicate, "summary-renamed", provider=provider)
                assert duplicate.name == "summary-renamed"
                move(design, archive, provider=provider)
                assert design.parent is archive
                move(design, documents, provider=provider)
                assert design.parent is documents
                print(f"  copied file: {duplicate.filename()} (fresh UID)")
                print(f"  renamed file: {duplicate.filename()}")
                print("  moved design.md into archive and back")

                print("\n[7/10] Serialize and reconstruct the specialized model")
                json_value = tree.to_json(indent=2)
                json_restored = FSResourceTree.from_json(json_value)
                xml_value = tree.to_xml()
                xml_restored = FSResourceTree.from_xml(xml_value)
                assert len(json_restored) == len(tree) == len(xml_restored)
                assert isinstance(json_restored.roots[0], Directory)
                assert isinstance(xml_restored.roots[0], Directory)
                print(f"  JSON round-trip: {len(json_restored)} resources")
                print(f"  XML round-trip:  {len(xml_restored)} resources")

                print("\n[8/10] Render the model as Mermaid")
                print(mermaid(root))

                print("\n[9/10] Exercise the opt-in monitor lifecycle")
                monitor = root.enable_monitor(interval=0.25, recursive=False)
                assert root.monitor_enabled and monitor.enabled
                assert root.disable_monitor(timeout=2.0)
                assert not root.monitor_enabled
                print("  monitor started and stopped cleanly")

                print("\n[10/10] Remove only the resources created by this demonstration")
                duplicate.delete()
                assert not exists(duplicate, provider=provider)
                archive.delete()
                assert not exists(archive, provider=provider)
                print("  copied file and archive directory deleted")

        print("\nAll public API demonstration steps completed.")
        print("The temporary physical filesystem will now be removed automatically.")


if __name__ == "__main__":
    main()
