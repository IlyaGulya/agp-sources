#!/usr/bin/env python3
"""Discover stable AGP releases and add them to build.gradle."""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


METADATA_URL = (
    "https://dl.google.com/dl/android/maven2/"
    "com/android/tools/build/gradle/maven-metadata.xml"
)
STABLE_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
VERSION_LINE = re.compile(r'^(\s*)"(\d+\.\d+\.\d+)",(\s*)$', re.MULTILINE)


def version_key(version: str) -> tuple[int, int, int]:
    return tuple(int(part) for part in version.split("."))  # type: ignore[return-value]


def published_versions() -> set[str]:
    with urllib.request.urlopen(METADATA_URL, timeout=30) as response:
        root = ET.fromstring(response.read())
    return {
        node.text
        for node in root.findall("./versioning/versions/version")
        if node.text and STABLE_VERSION.fullmatch(node.text)
    }


def tracked_versions(repo: Path) -> set[str]:
    return {
        child.name
        for child in repo.iterdir()
        if child.is_dir() and STABLE_VERSION.fullmatch(child.name)
    }


def update_build_file(build_file: Path, versions: list[str]) -> None:
    content = build_file.read_text()
    matches = list(VERSION_LINE.finditer(content))
    if not matches:
        raise RuntimeError(f"Could not find agpVersions entries in {build_file}")

    indent = matches[-1].group(1)
    insertion = "".join(f'{indent}"{version}",\n' for version in versions)
    position = matches[-1].end()
    build_file.write_text(content[:position] + "\n" + insertion.rstrip("\n") + content[position:])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="discover without editing")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parent.parent
    tracked = tracked_versions(repo)
    if not tracked:
        print("No tracked stable AGP versions found", file=sys.stderr)
        return 1

    latest_tracked = max(tracked, key=version_key)
    new_versions = sorted(
        (
            version
            for version in published_versions()
            if version_key(version) > version_key(latest_tracked)
        ),
        key=version_key,
    )

    print(" ".join(new_versions))
    if new_versions and not args.check:
        update_build_file(repo / "build.gradle", new_versions)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
