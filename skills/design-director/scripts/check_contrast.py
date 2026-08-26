#!/usr/bin/env python3
"""Check a WCAG relative-luminance contrast ratio using only the standard library."""

from __future__ import annotations

import argparse
import json
import re
import sys


HEX = re.compile(r"^#?([0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")


def parse_hex(value: str) -> tuple[int, int, int]:
    match = HEX.fullmatch(value.strip())
    if not match:
        raise argparse.ArgumentTypeError(f"invalid color {value!r}; use #RRGGBB")
    raw = match.group(1)
    if len(raw) == 3:
        raw = "".join(char * 2 for char in raw)
    return tuple(int(raw[index : index + 2], 16) for index in (0, 2, 4))


def channel(value: int) -> float:
    normalized = value / 255
    return normalized / 12.92 if normalized <= 0.04045 else ((normalized + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[int, int, int]) -> float:
    red, green, blue = (channel(value) for value in rgb)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--foreground", required=True, type=parse_hex)
    parser.add_argument("--background", required=True, type=parse_hex)
    parser.add_argument(
        "--threshold",
        type=float,
        default=4.5,
        help="minimum ratio; WCAG normal text defaults to 4.5",
    )
    args = parser.parse_args()

    foreground = luminance(args.foreground)
    background = luminance(args.background)
    lighter, darker = max(foreground, background), min(foreground, background)
    ratio = (lighter + 0.05) / (darker + 0.05)
    result = {
        "foreground": "#%02X%02X%02X" % args.foreground,
        "background": "#%02X%02X%02X" % args.background,
        "ratio": round(ratio, 2),
        "threshold": args.threshold,
        "pass": ratio >= args.threshold,
    }
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
