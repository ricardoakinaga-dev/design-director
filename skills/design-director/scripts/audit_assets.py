#!/usr/bin/env python3
"""Inspect image names, sizes, and lightweight dimensions without third-party packages."""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import xml.etree.ElementTree as ElementTree
import zlib
from pathlib import Path


IMAGE_EXTENSIONS = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_dimensions(data: bytes) -> tuple[int, int] | None:
    if len(data) < 8 or data[:8] != PNG_SIGNATURE:
        return None
    offset = 8
    header: tuple[int, int] | None = None
    compressed = bytearray()
    saw_end = False
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            return None
        chunk_type = data[offset + 4 : offset + 8]
        chunk_data = data[offset + 8 : offset + 8 + length]
        expected_crc = struct.unpack(">I", data[offset + 8 + length : chunk_end])[0]
        if zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF != expected_crc:
            return None
        if chunk_type == b"IHDR":
            if offset != 8 or length != 13:
                return None
            width, height = struct.unpack(">II", chunk_data[:8])
            header = (width, height) if width and height else None
        elif chunk_type == b"IDAT":
            compressed.extend(chunk_data)
        elif chunk_type == b"IEND":
            if length != 0:
                return None
            saw_end = True
            break
        offset = chunk_end
    if not header or not compressed or not saw_end:
        return None
    try:
        zlib.decompress(bytes(compressed))
    except zlib.error:
        return None
    return header


def svg_dimensions(data: bytes) -> tuple[int, int] | None:
    try:
        root = ElementTree.fromstring(data)
    except ElementTree.ParseError:
        return None
    if not root.tag.endswith("svg"):
        return None
    text = data.decode("utf-8", errors="replace")
    match = re.search(
        r"\bviewBox\s*=\s*[\"']\s*[\d.+-]+\s+[\d.+-]+\s+([\d.+-]+)\s+([\d.+-]+)",
        text,
    )
    return (round(float(match.group(1))), round(float(match.group(2)))) if match else None


def dimensions(path: Path, data: bytes) -> tuple[int, int] | None:
    readers = {".png": png_dimensions, ".svg": svg_dimensions}
    reader = readers.get(path.suffix.lower())
    return reader(data) if reader else None


def inspect(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    dimensions_value = dimensions(path, data)
    issue_candidates = [
        (not SAFE_NAME.fullmatch(path.name), "filename is not lowercase/hyphen-safe"),
        (not data, "file is empty"),
        (dimensions_value is None, "dimensions require native image inspection"),
    ]
    return {
        "path": str(path),
        "format": path.suffix.lower().lstrip("."),
        "bytes": path.stat().st_size,
        "dimensions": list(dimensions_value) if dimensions_value else None,
        "dimension_note": "decoded locally" if dimensions_value else "use native image inspection for this format",
        "issues": [message for condition, message in issue_candidates if condition],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--strict", action="store_true", help="fail when an asset has a naming or file issue")
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error(f"not a directory: {args.root}")
    records = [
        inspect(path)
        for path in sorted(args.root.rglob("*"))
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    print(json.dumps(records, indent=2))
    return 1 if args.strict and any(record["issues"] for record in records) else 0


if __name__ == "__main__":
    sys.exit(main())
