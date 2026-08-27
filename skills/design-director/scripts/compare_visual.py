#!/usr/bin/env python3
"""Compare two native PNG captures without guessing from source code.

This is a small, dependency-free comparison primitive for hosts that already
captured screenshots.  It supports non-interlaced 8-bit PNGs with grayscale,
RGB, grayscale-alpha, and RGBA pixels.  Browser launch, route/state setup and
reference selection remain host responsibilities.  The output is evidence for
a ledger, not a design-quality score and not a substitute for a critic.
"""

from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path
from typing import Any


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


class PngError(ValueError):
    """Raised when a PNG cannot be decoded by this conservative comparator."""


def _paeth(left: int, above: int, upper_left: int) -> int:
    estimate = left + above - upper_left
    distance_left = abs(estimate - left)
    distance_above = abs(estimate - above)
    distance_upper_left = abs(estimate - upper_left)
    if distance_left <= distance_above and distance_left <= distance_upper_left:
        return left
    if distance_above <= distance_upper_left:
        return above
    return upper_left


def _unfilter(scanlines: bytes, width: int, height: int, bytes_per_pixel: int) -> bytes:
    stride = width * bytes_per_pixel
    expected = height * (stride + 1)
    if len(scanlines) != expected:
        raise PngError("PNG scanline payload has an unexpected length")
    row_size = stride + 1
    if all(scanlines[row * row_size] == 0 for row in range(height)):
        return b"".join(
            scanlines[row * row_size + 1 : (row + 1) * row_size]
            for row in range(height)
        )
    output = bytearray(height * stride)
    previous = bytearray(stride)
    cursor = 0
    for row_index in range(height):
        filter_type = scanlines[cursor]
        cursor += 1
        encoded = scanlines[cursor : cursor + stride]
        cursor += stride
        row = bytearray(stride)
        for index, value in enumerate(encoded):
            left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            above = previous[index]
            upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            if filter_type == 0:
                reconstructed = value
            elif filter_type == 1:
                reconstructed = value + left
            elif filter_type == 2:
                reconstructed = value + above
            elif filter_type == 3:
                reconstructed = value + ((left + above) // 2)
            elif filter_type == 4:
                reconstructed = value + _paeth(left, above, upper_left)
            else:
                raise PngError(f"unsupported PNG filter type {filter_type}")
            row[index] = reconstructed & 0xFF
        start = row_index * stride
        output[start : start + stride] = row
        previous = row
    return bytes(output)


@lru_cache(maxsize=16)
def _decode_png_cached(path_string: str, content_sha256: str) -> tuple[int, int, bytes]:
    """Decode a file keyed by content identity, not mutable filesystem metadata."""

    path = Path(path_string)
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise PngError("file is not a PNG")
    cursor = len(PNG_SIGNATURE)
    header: tuple[int, int, int, int, int, int, int] | None = None
    idat: list[bytes] = []
    saw_end = False
    while cursor < len(data):
        if cursor + 12 > len(data):
            raise PngError("PNG chunk is truncated")
        length = struct.unpack(">I", data[cursor : cursor + 4])[0]
        chunk_type = data[cursor + 4 : cursor + 8]
        end = cursor + 12 + length
        if end > len(data):
            raise PngError("PNG chunk payload is truncated")
        payload = data[cursor + 8 : cursor + 8 + length]
        expected_crc = struct.unpack(">I", data[cursor + 8 + length : end])[0]
        if zlib.crc32(chunk_type + payload) & 0xFFFFFFFF != expected_crc:
            raise PngError("PNG chunk CRC is invalid")
        if chunk_type == b"IHDR":
            if len(payload) != 13 or header is not None:
                raise PngError("PNG IHDR is invalid")
            header = struct.unpack(">IIBBBBB", payload)
        elif chunk_type == b"IDAT":
            idat.append(payload)
        elif chunk_type == b"IEND":
            if length != 0 or end != len(data):
                raise PngError("PNG IEND is invalid or not final")
            saw_end = True
            break
        cursor = end
    if header is None or not saw_end or not idat:
        raise PngError("PNG has no IHDR")
    width, height, bit_depth, color_type, compression, filter_method, interlace = header
    if width < 1 or height < 1:
        raise PngError("PNG dimensions must be positive")
    if bit_depth != 8 or compression != 0 or filter_method != 0 or interlace != 0:
        raise PngError("only non-interlaced 8-bit PNGs are supported")
    channels_by_type = {0: 1, 2: 3, 4: 2, 6: 4}
    channels = channels_by_type.get(color_type)
    if channels is None:
        raise PngError(f"unsupported PNG color type {color_type}")
    raw = _unfilter(zlib.decompress(b"".join(idat)), width, height, channels)
    if color_type == 6:
        return width, height, raw
    rgba = bytearray(width * height * 4)
    output_cursor = 0
    for index in range(0, len(raw), channels):
        if color_type == 0:
            red = green = blue = raw[index]
            alpha = 255
        elif color_type == 2:
            red, green, blue = raw[index : index + 3]
            alpha = 255
        elif color_type == 4:
            red = green = blue = raw[index]
            alpha = raw[index + 1]
        else:
            red, green, blue, alpha = raw[index : index + 4]
        rgba[output_cursor : output_cursor + 4] = bytes((red, green, blue, alpha))
        output_cursor += 4
    return width, height, bytes(rgba)


def decode_png(path: Path) -> tuple[int, int, bytes]:
    """Decode a PNG once per immutable local file identity within a run."""

    data = path.read_bytes()
    content_sha256 = hashlib.sha256(data).hexdigest()
    return _decode_png_cached(str(path.resolve()), content_sha256)


def compare_pngs(
    reference: Path,
    actual: Path,
    *,
    pixel_threshold: int = 8,
    max_mean_error: float = 0.02,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "reference": str(reference),
        "actual": str(actual),
        "method": "native-png-rgba-absolute-error",
        "pixel_threshold": pixel_threshold,
        "max_mean_error": max_mean_error,
    }
    try:
        reference_width, reference_height, reference_pixels = decode_png(reference)
        actual_width, actual_height, actual_pixels = decode_png(actual)
    except (OSError, PngError, zlib.error) as error:
        result.update({"status": "BLOCKED", "error": str(error)})
        return result
    result["reference_dimensions"] = [reference_width, reference_height]
    result["actual_dimensions"] = [actual_width, actual_height]
    if (reference_width, reference_height) != (actual_width, actual_height):
        result.update(
            {
                "status": "FAIL",
                "reason": "native screenshot dimensions differ",
                "changed_pixel_ratio": 1.0,
                "mean_absolute_error": 1.0,
                "pixel_similarity": 0.0,
            }
        )
        return result
    differences = 0
    total_error = 0
    maximum_error = 0
    for offset in range(0, len(reference_pixels), 4):
        pixel_errors = [
            abs(reference_pixels[offset + channel] - actual_pixels[offset + channel])
            for channel in range(4)
        ]
        total_error += sum(pixel_errors)
        maximum_error = max(maximum_error, max(pixel_errors))
        if max(pixel_errors) > pixel_threshold:
            differences += 1
    channel_count = len(reference_pixels)
    mean_error = total_error / (channel_count * 255) if channel_count else 1.0
    pixel_count = reference_width * reference_height
    changed_ratio = differences / pixel_count if pixel_count else 1.0
    result.update(
        {
            "status": "PASS" if mean_error <= max_mean_error else "DIFF",
            "changed_pixel_ratio": round(changed_ratio, 6),
            "mean_absolute_error": round(mean_error, 6),
            "maximum_channel_error": maximum_error,
            "pixel_similarity": round(max(0.0, 1.0 - mean_error) * 100, 2),
        }
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("actual", type=Path)
    parser.add_argument("--pixel-threshold", type=int, default=8)
    parser.add_argument("--max-mean-error", type=float, default=0.02)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)
    if not 0 <= args.pixel_threshold <= 255:
        parser.error("--pixel-threshold must be between 0 and 255")
    if not 0 <= args.max_mean_error <= 1:
        parser.error("--max-mean-error must be between 0 and 1")
    result = compare_pngs(
        args.reference,
        args.actual,
        pixel_threshold=args.pixel_threshold,
        max_mean_error=args.max_mean_error,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result.get("status") == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
