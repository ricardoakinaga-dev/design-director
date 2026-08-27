#!/usr/bin/env python3
"""Audit image assets with deterministic, standard-library parsers.

The default command remains compatible with the original helper:

    python audit_assets.py <asset-root> [--strict]

The auditor intentionally reports None when a format cannot be inspected
locally. It never guesses dimensions, alpha, or provenance from a filename.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
import xml.etree.ElementTree as ElementTree
import zlib
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable


IMAGE_EXTENSIONS = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
SAFE_NAME = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
SUSPICIOUS_NAME = re.compile(
    r"^(?:img|image|asset|artwork|final|final\d*|copy|untitled|screenshot)(?:[-_.\d]|$)"
)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024

Parser = Callable[[bytes], dict[str, Any] | None]


def _dimensions(width: int, height: int) -> tuple[int, int] | None:
    if width <= 0 or height <= 0:
        return None
    return width, height


def _png_info(data: bytes) -> dict[str, Any] | None:
    if len(data) < 8 or data[:8] != PNG_SIGNATURE:
        return None
    offset = 8
    header: tuple[int, int] | None = None
    png_properties: tuple[int, int] | None = None
    compressed = bytearray()
    saw_idat = False
    saw_end = False
    alpha = False
    saw_header = False
    palette_entries: int | None = None
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
            if offset != 8 or length != 13 or saw_header:
                return None
            width, height = struct.unpack(">II", chunk_data[:8])
            bit_depth = chunk_data[8]
            color_type = chunk_data[9]
            valid_bit_depths = {
                0: {1, 2, 4, 8, 16},
                2: {8, 16},
                3: {1, 2, 4, 8},
                4: {8, 16},
                6: {8, 16},
            }
            if color_type not in valid_bit_depths or bit_depth not in valid_bit_depths[color_type]:
                return None
            if chunk_data[10:] != b"\x00\x00\x00":
                return None
            header = _dimensions(width, height)
            if header is None:
                return None
            png_properties = (bit_depth, color_type)
            alpha = color_type in {4, 6}
            saw_header = True
        elif chunk_type == b"PLTE":
            if not saw_header or saw_idat or not chunk_data or len(chunk_data) % 3:
                return None
            palette_entries = len(chunk_data) // 3
            if png_properties is None or palette_entries > min(256, 2 ** png_properties[0]):
                return None
        elif chunk_type == b"tRNS":
            if not saw_header or saw_idat:
                return None
            alpha = True
        elif chunk_type == b"IDAT":
            if not saw_header:
                return None
            saw_idat = True
            compressed.extend(chunk_data)
        elif chunk_type == b"IEND":
            if length != 0 or not saw_header or not saw_idat:
                return None
            if chunk_end != len(data):
                return None
            saw_end = True
            break
        offset = chunk_end
    if not header or not compressed or not saw_end:
        return None
    if png_properties is None:
        return None
    bit_depth, color_type = png_properties
    if color_type == 3 and palette_entries is None:
        return None
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    row_bytes = (header[0] * channels * bit_depth + 7) // 8
    expected_payload = header[1] * (row_bytes + 1)
    try:
        decompressor = zlib.decompressobj()
        scanlines = decompressor.decompress(bytes(compressed)) + decompressor.flush()
        if not decompressor.eof or decompressor.unused_data or decompressor.unconsumed_tail:
            return None
        if len(scanlines) != expected_payload:
            return None
        if any(scanlines[row * (row_bytes + 1)] > 4 for row in range(header[1])):
            return None
    except zlib.error:
        return None
    return {
        "dimensions": header,
        "alpha": alpha,
        "alpha_note": "PNG color type/tRNS inspected locally",
        "dimension_note": "decoded locally",
        "parser": "png-pixel-stream",
    }


def png_dimensions(data: bytes) -> tuple[int, int] | None:
    """Keep the original helper API for callers importing this function."""

    info = _png_info(data)
    return info["dimensions"] if info else None


def _svg_info(data: bytes) -> dict[str, Any] | None:
    try:
        root = ElementTree.fromstring(data)
    except (ElementTree.ParseError, ValueError):
        return None
    if not root.tag.endswith("svg"):
        return None
    text = data.decode("utf-8", errors="replace")
    viewbox = re.search(
        r"\bviewBox\s*=\s*[\"']\s*([\d.+-]+)\s+([\d.+-]+)\s+([\d.+-]+)\s+([\d.+-]+)",
        text,
        re.IGNORECASE,
    )
    size: tuple[int, int] | None = None
    dimension_note = "SVG has no local pixel dimensions"
    if viewbox:
        try:
            size = _dimensions(round(float(viewbox.group(3))), round(float(viewbox.group(4))))
        except ValueError:
            size = None
        if size:
            dimension_note = "parsed from SVG viewBox locally"
    if size is None:
        width_match = re.search(
            r"\bwidth\s*=\s*[\"']\s*(\d+(?:\.\d+)?)\s*(?:px)?\s*[\"']",
            text,
            re.IGNORECASE,
        )
        height_match = re.search(
            r"\bheight\s*=\s*[\"']\s*(\d+(?:\.\d+)?)\s*(?:px)?\s*[\"']",
            text,
            re.IGNORECASE,
        )
        if width_match and height_match:
            size = _dimensions(round(float(width_match.group(1))), round(float(height_match.group(1))))
            if size:
                dimension_note = "parsed from SVG width/height locally"
    has_alpha = bool(
        re.search(
            r"(?:opacity|fill-opacity|stroke-opacity|stop-opacity|rgba\s*\()\s*[:=(]",
            text,
            re.IGNORECASE,
        )
    )
    return {
        "dimensions": size,
        "alpha": True if has_alpha else None,
        "alpha_note": (
            "explicit SVG opacity inspected locally"
            if has_alpha
            else "SVG alpha requires render inspection"
        ),
        "dimension_note": dimension_note,
        "parser": "svg-xml+viewBox",
    }


def svg_dimensions(data: bytes) -> tuple[int, int] | None:
    """Keep the original helper API for callers importing this function."""

    info = _svg_info(data)
    return info["dimensions"] if info else None


def _jpeg_info(data: bytes) -> dict[str, Any] | None:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    index = 2
    sof_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while index < len(data):
        if data[index] != 0xFF:
            return None
        while index < len(data) and data[index] == 0xFF:
            index += 1
        if index >= len(data):
            return None
        marker = data[index]
        index += 1
        if marker in {0xD8, 0xD9}:
            if marker == 0xD9:
                break
            continue
        if marker == 0xDA:
            # Entropy-coded data follows; a valid SOF before SOS is enough
            # for dimensions without parsing compressed scan data.
            break
        if marker == 0x00 or 0xD0 <= marker <= 0xD7:
            continue
        if index + 2 > len(data):
            return None
        length = struct.unpack(">H", data[index : index + 2])[0]
        if length < 2 or index + length > len(data):
            return None
        if marker in sof_markers:
            if length < 8:
                return None
            height, width, components = struct.unpack(">HHB", data[index + 3 : index + 8])
            size = _dimensions(width, height)
            if not size or components <= 0:
                return None
            return {
                "dimensions": size,
                "alpha": False,
                "alpha_note": "JPEG has no alpha channel",
                "dimension_note": "parsed from JPEG frame header locally",
                "parser": "jpeg-frame-header",
            }
        index += length
    return None


def _gif_info(data: bytes) -> dict[str, Any] | None:
    if len(data) < 13 or data[:6] not in {b"GIF87a", b"GIF89a"}:
        return None
    width, height = struct.unpack("<HH", data[6:10])
    size = _dimensions(width, height)
    if not size:
        return None
    packed = data[10]
    index = 13
    if packed & 0x80:
        table_size = 3 * (2 ** ((packed & 0x07) + 1))
        index += table_size
    if index > len(data):
        return None
    has_alpha = False
    saw_trailer = False

    def skip_sub_blocks(position: int) -> int | None:
        while position < len(data):
            block_size = data[position]
            position += 1
            if block_size == 0:
                return position
            position += block_size
            if position > len(data):
                return None
        return None

    while index < len(data):
        marker = data[index]
        index += 1
        if marker == 0x3B:
            saw_trailer = True
            break
        if marker == 0x21:
            if index >= len(data):
                return None
            label = data[index]
            index += 1
            if label == 0xF9:
                if index >= len(data) or data[index] != 4 or index + 6 > len(data):
                    return None
                has_alpha = bool(data[index + 1] & 0x01)
                index += 6
            else:
                index = skip_sub_blocks(index)
                if index is None:
                    return None
            continue
        if marker == 0x2C:
            if index + 9 > len(data):
                return None
            local_packed = data[index + 8]
            index += 9
            if local_packed & 0x80:
                table_size = 3 * (2 ** ((local_packed & 0x07) + 1))
                index += table_size
            if index >= len(data):
                return None
            index += 1  # LZW minimum code size
            index = skip_sub_blocks(index)
            if index is None:
                return None
            continue
        return None
    if not saw_trailer:
        return None
    return {
        "dimensions": size,
        "alpha": has_alpha,
        "alpha_note": "GIF graphic control extension inspected locally",
        "dimension_note": "parsed from GIF logical screen locally",
        "parser": "gif-header+blocks",
    }


def _webp_info(data: bytes) -> dict[str, Any] | None:
    if len(data) < 20 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    riff_size = struct.unpack("<I", data[4:8])[0]
    if riff_size + 8 > len(data):
        return None
    index = 12
    result: dict[str, Any] | None = None
    while index + 8 <= len(data):
        chunk_name = data[index : index + 4]
        chunk_size = struct.unpack("<I", data[index + 4 : index + 8])[0]
        payload_start = index + 8
        payload_end = payload_start + chunk_size
        if payload_end > len(data):
            return None
        payload = data[payload_start:payload_end]
        if chunk_name == b"VP8X" and len(payload) >= 10:
            width = 1 + int.from_bytes(payload[4:7], "little")
            height = 1 + int.from_bytes(payload[7:10], "little")
            size = _dimensions(width, height)
            if size:
                result = {
                    "dimensions": size,
                    "alpha": bool(payload[0] & 0x10),
                    "alpha_note": "WebP VP8X feature flags inspected locally",
                    "dimension_note": "parsed from WebP VP8X header locally",
                    "parser": "webp-vp8x",
                }
        elif chunk_name == b"VP8 " and len(payload) >= 10 and payload[3:6] == b"\x9d\x01\x2a":
            width, height = struct.unpack("<HH", payload[6:10])
            size = _dimensions(width & 0x3FFF, height & 0x3FFF)
            if size:
                result = {
                    "dimensions": size,
                    "alpha": False,
                    "alpha_note": "lossy WebP VP8 has no alpha channel",
                    "dimension_note": "parsed from WebP VP8 frame header locally",
                    "parser": "webp-vp8",
                }
        elif chunk_name == b"VP8L" and len(payload) >= 5 and payload[0] == 0x2F:
            bits = int.from_bytes(payload[1:5], "little")
            width = (bits & 0x3FFF) + 1
            height = ((bits >> 14) & 0x3FFF) + 1
            size = _dimensions(width, height)
            if size:
                result = {
                    "dimensions": size,
                    "alpha": None,
                    "alpha_note": "lossless WebP alpha requires pixel decode",
                    "dimension_note": "parsed from WebP VP8L header locally",
                    "parser": "webp-vp8l",
                }
        index = payload_end + (chunk_size & 1)
    return result


def _avif_info(data: bytes) -> dict[str, Any] | None:
    # AVIF is an ISO-BMFF container. This parser validates the ftyp brand and
    # reads standard image spatial extents (ispe) when present. Alpha remains
    # unknown because it requires item decoding.
    if len(data) < 16 or data[4:8] != b"ftyp":
        return None
    major_brand = data[8:12]
    compatible = [data[index : index + 4] for index in range(16, min(len(data), 64), 4)]
    if major_brand not in {b"avif", b"avis", b"mif1", b"heic"} and not any(
        brand in {b"avif", b"avis"} for brand in compatible
    ):
        return None
    marker = b"ispe"
    index = data.find(marker, 12)
    if index < 0 or index + 16 > len(data):
        return {
            "dimensions": None,
            "alpha": None,
            "alpha_note": "AVIF alpha requires item decode",
            "dimension_note": "valid AVIF brand; ispe dimensions not found",
            "parser": "avif-ftyp+ispe",
        }
    width, height = struct.unpack(">II", data[index + 8 : index + 16])
    return {
        "dimensions": _dimensions(width, height),
        "alpha": None,
        "alpha_note": "AVIF alpha requires item decode",
        "dimension_note": "parsed from AVIF ispe box locally",
        "parser": "avif-ftyp+ispe",
    }


def dimensions(path: Path, data: bytes) -> tuple[int, int] | None:
    readers: dict[str, Parser] = {
        ".avif": _avif_info,
        ".gif": _gif_info,
        ".jpeg": _jpeg_info,
        ".jpg": _jpeg_info,
        ".png": _png_info,
        ".svg": _svg_info,
        ".webp": _webp_info,
    }
    reader = readers.get(path.suffix.lower())
    parsed = reader(data) if reader else None
    return parsed["dimensions"] if parsed else None


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _normalise_manifest(path: Path | None, root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    if path is None:
        return {}, {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid asset manifest {path}: {error}") from error
    if not isinstance(payload, dict):
        raise ValueError("asset manifest must be a JSON object")
    raw_assets = payload.get("assets", [])
    entries: dict[str, dict[str, Any]] = {}
    if isinstance(raw_assets, list):
        iterable = raw_assets
    elif isinstance(raw_assets, dict):
        iterable = [
            {"path": key, **(value if isinstance(value, dict) else {})}
            for key, value in raw_assets.items()
        ]
    else:
        raise ValueError("asset manifest field 'assets' must be an array or object")
    for raw_entry in iterable:
        if not isinstance(raw_entry, dict) or not isinstance(raw_entry.get("path"), str):
            raise ValueError("each asset manifest entry requires a string path")
        manifest_path = Path(raw_entry["path"])
        key = (
            manifest_path.as_posix().lstrip("./")
            if not manifest_path.is_absolute()
            else _relative_path(manifest_path, root)
        )
        entries[key] = dict(raw_entry)
    return entries, payload


def _issue(record: dict[str, Any], code: str, severity: str, message: str) -> None:
    record.setdefault("issue_details", []).append(
        {"code": code, "severity": severity, "message": message}
    )
    record.setdefault("issues", []).append(message)


def _coerce_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def inspect(
    path: Path,
    manifest_entry: dict[str, Any] | None = None,
    root: Path | None = None,
    *,
    max_bytes: int | None = DEFAULT_MAX_BYTES,
    min_width: int = 0,
    min_height: int = 0,
) -> dict[str, Any]:
    """Inspect one asset; the original inspect(path) call remains valid."""

    root = root or path.parent
    data = path.read_bytes()
    extension = path.suffix.lower()
    parsers: dict[str, Parser] = {
        ".avif": _avif_info,
        ".gif": _gif_info,
        ".jpeg": _jpeg_info,
        ".jpg": _jpeg_info,
        ".png": _png_info,
        ".svg": _svg_info,
        ".webp": _webp_info,
    }
    parser = parsers.get(extension)
    parsed = parser(data) if parser and data else None
    size = parsed.get("dimensions") if parsed else None
    record: dict[str, Any] = {
        "path": _relative_path(path, root),
        "format": extension.lstrip("."),
        "detected_format": extension.lstrip(".") if parsed else None,
        "bytes": path.stat().st_size,
        "dimensions": list(size) if size else None,
        "aspect_ratio": round(size[0] / size[1], 4) if size else None,
        "alpha": parsed.get("alpha") if parsed else None,
        "alpha_note": parsed.get("alpha_note")
        if parsed
        else "format data is invalid or parser is unavailable",
        "dimension_note": parsed.get("dimension_note")
        if parsed
        else "use native image inspection for this format or repair the file",
        "inspection": parsed.get("parser") if parsed else "unknown",
        "sha256": hashlib.sha256(data).hexdigest(),
        "role": manifest_entry.get("role") if manifest_entry else None,
        "provenance": manifest_entry.get("provenance") if manifest_entry else None,
        "source": manifest_entry.get("source") if manifest_entry else None,
        "issues": [],
        "issue_details": [],
    }
    if not SAFE_NAME.fullmatch(path.name):
        _issue(record, "unsafe_name", "medium", "filename is not lowercase/hyphen-safe")
    if SUSPICIOUS_NAME.match(path.stem.lower()):
        _issue(record, "suspicious_name", "low", "filename is generic or likely an export placeholder")
    if not data:
        _issue(record, "empty_file", "high", "file is empty")
    if not parsed:
        _issue(record, "uninspectable_file", "high", "format parser could not validate this asset")
    if size is None:
        _issue(record, "unknown_dimensions", "medium", "dimensions require native image inspection")

    configured_max = max_bytes
    configured_min_width = min_width
    configured_min_height = min_height
    if manifest_entry:
        entry_max = _coerce_number(manifest_entry.get("max_bytes"))
        if entry_max is not None:
            configured_max = int(entry_max)
        entry_min_width = _coerce_number(manifest_entry.get("min_width"))
        entry_min_height = _coerce_number(manifest_entry.get("min_height"))
        if entry_min_width is not None:
            configured_min_width = int(entry_min_width)
        if entry_min_height is not None:
            configured_min_height = int(entry_min_height)
    record["max_bytes"] = configured_max
    record["minimum_dimensions"] = [configured_min_width, configured_min_height]
    if configured_max is not None and configured_max > 0 and record["bytes"] > configured_max:
        _issue(record, "oversized_file", "high", f"file is {record['bytes']} bytes; limit is {configured_max}")
    if size and configured_min_width and size[0] < configured_min_width:
        _issue(record, "under_resolution", "high", f"width {size[0]} is below required {configured_min_width}")
    if size and configured_min_height and size[1] < configured_min_height:
        _issue(record, "under_resolution", "high", f"height {size[1]} is below required {configured_min_height}")
    if manifest_entry:
        expected_format = manifest_entry.get("format")
        if isinstance(expected_format, str) and expected_format.strip():
            expected_formats = {item.strip().lower().lstrip(".") for item in expected_format.split(",")}
            if extension.lstrip(".") not in expected_formats:
                _issue(
                    record,
                    "format_mismatch",
                    "high",
                    f"format {extension.lstrip('.')!r} does not match manifest {sorted(expected_formats)!r}",
                )
        expected_dimensions = manifest_entry.get("dimensions")
        if isinstance(expected_dimensions, dict):
            expected_width = expected_dimensions.get("width")
            expected_height = expected_dimensions.get("height")
            if isinstance(expected_width, int) and isinstance(expected_height, int):
                record["declared_dimensions"] = [expected_width, expected_height]
                if size and tuple(size) != (expected_width, expected_height):
                    _issue(
                        record,
                        "dimension_mismatch",
                        "high",
                        f"dimensions {list(size)!r} do not match manifest {[expected_width, expected_height]!r}",
                    )
        expected_ratio = _coerce_number(
            manifest_entry.get("expected_aspect_ratio", manifest_entry.get("aspect_ratio"))
        )
        tolerance = _coerce_number(manifest_entry.get("aspect_tolerance"))
        if tolerance is None:
            tolerance = 0.03
        if expected_ratio and size:
            observed_ratio = size[0] / size[1]
            if abs(observed_ratio - expected_ratio) > tolerance:
                _issue(
                    record,
                    "aspect_ratio_mismatch",
                    "high",
                    f"aspect ratio {observed_ratio:.4f} differs from expected {expected_ratio:.4f} ± {tolerance:.4f}",
                )
        usage = manifest_entry.get("used")
        if usage is False:
            record["unused"] = True
            _issue(record, "unused_asset", "medium", "manifest marks this asset as unused")
        elif usage is True:
            record["unused"] = False
    if manifest_entry is not None:
        if not isinstance(manifest_entry.get("role"), str) or not manifest_entry.get("role", "").strip():
            _issue(record, "missing_role", "medium", "manifest entry does not declare an asset role")
        if not isinstance(manifest_entry.get("provenance"), str) or not manifest_entry.get("provenance", "").strip():
            _issue(record, "missing_provenance", "medium", "manifest entry does not declare asset provenance")
    return record


def _apply_manifest_usage(
    records: list[dict[str, Any]],
    manifest_entries: dict[str, dict[str, Any]],
    manifest: dict[str, Any],
) -> None:
    used_paths = {
        str(value).lstrip("./")
        for value in manifest.get("used_paths", [])
        if isinstance(value, str)
    }
    generated_paths = {
        str(value).lstrip("./")
        for value in manifest.get("generated_paths", [])
        if isinstance(value, str)
    }
    usage_map = manifest.get("usage", {})
    if isinstance(usage_map, dict):
        for key, value in usage_map.items():
            if isinstance(value, bool):
                entry = manifest_entries.get(str(key).lstrip("./"))
                if entry is not None:
                    entry["used"] = value
    if not used_paths and not generated_paths and not any(
        isinstance(entry.get("used"), bool) for entry in manifest_entries.values()
    ):
        return
    for record in records:
        path = record["path"]
        entry = manifest_entries.get(path)
        explicit_usage = entry.get("used") if entry else None
        if explicit_usage is False:
            record["unused"] = True
            _issue(record, "unused_asset", "medium", "manifest marks this asset as unused")
        elif explicit_usage is True:
            record["unused"] = False
        elif path in generated_paths and path not in used_paths:
            record["unused"] = True
            _issue(record, "unused_asset", "medium", "generated asset is not listed in manifest used_paths")
        elif path in used_paths:
            record["unused"] = False


def audit(root: Path, manifest_path: Path | None = None, **options: Any) -> list[dict[str, Any]]:
    manifest_entries, manifest = _normalise_manifest(manifest_path, root)
    records = [
        inspect(
            path,
            manifest_entries.get(_relative_path(path, root)),
            root,
            max_bytes=options.get("max_bytes", DEFAULT_MAX_BYTES),
            min_width=int(options.get("min_width", 0)),
            min_height=int(options.get("min_height", 0)),
        )
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    _apply_manifest_usage(records, manifest_entries, manifest)

    hashes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        hashes[record["sha256"]].append(record)
    for group in hashes.values():
        if len(group) < 2:
            continue
        paths = [record["path"] for record in group]
        for index, record in enumerate(group):
            record["duplicate_group"] = paths
            if index:
                record["duplicate_of"] = paths[0]
                _issue(record, "duplicate_content", "medium", f"asset content duplicates {paths[0]}")
    if manifest_path:
        record_paths = {record["path"] for record in records}
        for manifest_key, manifest_entry in manifest_entries.items():
            if manifest_key in record_paths or manifest_key.startswith(("http://", "https://", "file://", "data:")):
                continue
            missing_record: dict[str, Any] = {
                "path": manifest_key,
                "format": Path(manifest_key).suffix.lower().lstrip("."),
                "detected_format": None,
                "bytes": None,
                "dimensions": None,
                "aspect_ratio": None,
                "alpha": None,
                "alpha_note": "asset is missing; alpha is not observable",
                "dimension_note": "asset is missing; dimensions are not observable",
                "inspection": "missing",
                "sha256": None,
                "role": manifest_entry.get("role"),
                "provenance": manifest_entry.get("provenance"),
                "source": manifest_entry.get("source"),
                "issues": [],
                "issue_details": [],
            }
            _issue(missing_record, "missing_asset", "high", "manifest declares an asset that is not present")
            if not isinstance(manifest_entry.get("role"), str) or not manifest_entry.get("role", "").strip():
                _issue(missing_record, "missing_role", "medium", "manifest entry does not declare an asset role")
            if not isinstance(manifest_entry.get("provenance"), str) or not manifest_entry.get("provenance", "").strip():
                _issue(missing_record, "missing_provenance", "medium", "manifest entry does not declare asset provenance")
            records.append(missing_record)
        for record in records:
            if record["path"] not in manifest_entries:
                _issue(
                    record,
                    "missing_manifest_entry",
                    "medium",
                    "manifest does not declare role/provenance for this asset",
                )
    return sorted(records, key=lambda record: record["path"])


def _text_output(records: list[dict[str, Any]]) -> str:
    lines = ["path\tformat\tdimensions\tbytes\talpha\tissues"]
    for record in records:
        dimensions_value = (
            "x".join(str(value) for value in record["dimensions"])
            if record["dimensions"]
            else "unknown"
        )
        issues = "; ".join(record["issues"]) or "-"
        lines.append(
            f"{record['path']}\t{record['format']}\t{dimensions_value}\t"
            f"{record['bytes']}\t{record['alpha']}\t{issues}"
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--strict", action="store_true", help="fail when an asset has any reported issue")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="JSON manifest with role, provenance, usage, and per-asset limits",
    )
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=f"maximum file size; use 0 to disable the default {DEFAULT_MAX_BYTES} byte limit",
    )
    parser.add_argument("--min-width", type=int, default=0, help="minimum pixel width for every inspected asset")
    parser.add_argument("--min-height", type=int, default=0, help="minimum pixel height for every inspected asset")
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="stdout format; JSON remains the default for CLI compatibility",
    )
    parser.add_argument(
        "--output",
        "--json-output",
        dest="output",
        type=Path,
        help="also write the selected report to this path",
    )
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error(f"not a directory: {args.root}")
    if args.max_bytes < 0 or args.min_width < 0 or args.min_height < 0:
        parser.error("size limits cannot be negative")
    try:
        records = audit(
            args.root,
            args.manifest,
            max_bytes=None if args.max_bytes == 0 else args.max_bytes,
            min_width=args.min_width,
            min_height=args.min_height,
        )
    except ValueError as error:
        parser.error(str(error))
    payload = json.dumps(records, indent=2)
    rendered = payload if args.format == "json" else _text_output(records)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 1 if args.strict and any(record["issues"] for record in records) else 0


if __name__ == "__main__":
    sys.exit(main())
