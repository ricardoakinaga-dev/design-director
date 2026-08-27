#!/usr/bin/env python3
"""Audit a small, explicit set of design-token source formats.

This is a deterministic heuristic scanner, not a CSS/JavaScript compiler. It
understands common declarations in CSS/SCSS/JSON/JS/TS and reports what it can
prove from source text. Runtime styles, computed values, imports, and unusual
syntax remain outside its evidence boundary.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Iterable


SUPPORTED_EXTENSIONS = {".css", ".js", ".json", ".jsx", ".scss", ".ts", ".tsx"}
SKIP_DIRECTORIES = {
    ".git",
    ".next",
    ".turbo",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "out",
}
HEX_COLOR = re.compile(r"(?<![\w-])#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})(?![\w-])")
RGB_COLOR = re.compile(r"\b(?:rgb|hsl)a?\([^)]*\)", re.IGNORECASE)
MEASURE = re.compile(r"(?<![\w.])-?(?:\d+(?:\.\d+)?|\.\d+)(?:px|rem|em|%)(?![\w-])", re.IGNORECASE)
DECLARATION = re.compile(
    r"(?P<key>--[\w-]+|\$[\w-]+|[\"'][^\"']+[\"']|[\w.-]+)\s*(?::|=)\s*(?P<value>[^;{}]+)"
)
PROPERTY = re.compile(
    r"(?P<key>--[\w-]+|\$[\w-]+|[\"'][^\"']+[\"']|[\w.-]+)\s*:\s*(?P<value>[^;{}]+)"
)
TOKEN_WORDS = re.compile(
    r"(?:color|colour|space|spacing|gap|radius|round|shadow|font|type|tracking|leading|line-height|"
    r"weight|size|text|surface|border|motion|duration)",
    re.IGNORECASE,
)
TYPOGRAPHY_PROPERTY = re.compile(
    r"^(?:font(?:-family|-size|-weight|-style)?|line-height|letter-spacing|text-(?:size|style|weight))$",
    re.IGNORECASE,
)
CSS_PROPERTY_NAMES = {
    "accent-color",
    "background",
    "background-color",
    "border",
    "border-color",
    "border-radius",
    "border-style",
    "border-width",
    "bottom",
    "box-shadow",
    "color",
    "column-gap",
    "fill",
    "font-family",
    "font-size",
    "font-style",
    "font-weight",
    "gap",
    "grid-gap",
    "height",
    "inset",
    "left",
    "letter-spacing",
    "line-height",
    "margin",
    "outline",
    "outline-color",
    "padding",
    "right",
    "row-gap",
    "stroke",
    "text-shadow",
    "top",
    "width",
}
SPACING_PROPERTY = re.compile(
    r"^(?:margin|padding|gap|inset|top|right|bottom|left|width|height|column-gap|row-gap)$",
    re.IGNORECASE,
)
RADIUS_PROPERTY = re.compile(r"border-radius|radius", re.IGNORECASE)
SHADOW_PROPERTY = re.compile(r"box-shadow|text-shadow|shadow", re.IGNORECASE)
COLOR_PROPERTY = re.compile(
    r"^(?:color|background(?:-color)?|border(?:-[\w]+)?|outline(?:-color)?|fill|stroke|accent-color)$",
    re.IGNORECASE,
)

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def _strip_key(value: str) -> str:
    return value.strip().strip("\"'").strip()


def _is_token_key(key: str, extension: str = "") -> bool:
    normalized = _strip_key(key)
    if extension in {".css", ".scss"} and normalized.lower() in CSS_PROPERTY_NAMES:
        return False
    return normalized.startswith(("--", "$")) or bool(TOKEN_WORDS.search(normalized))


def _category_for(key: str, value: str) -> str | None:
    normalized = _strip_key(key).lower()
    value_lower = value.lower()
    if RADIUS_PROPERTY.search(normalized):
        return "radius"
    if SHADOW_PROPERTY.search(normalized):
        return "shadow"
    if TYPOGRAPHY_PROPERTY.fullmatch(normalized) or any(
        word in normalized for word in ("font", "type", "leading", "tracking")
    ):
        return "typography"
    if SPACING_PROPERTY.fullmatch(normalized) or any(
        word in normalized for word in ("space", "spacing", "gap", "margin", "padding")
    ):
        return "spacing"
    if "color" in normalized or normalized in {"fill", "stroke", "accent"}:
        return "color"
    if HEX_COLOR.search(value) or RGB_COLOR.search(value):
        return "color"
    if value_lower.startswith("var(") and TOKEN_WORDS.search(normalized):
        return "token-reference"
    return None


def _line_number(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _rel(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _rgb(value: str) -> tuple[int, int, int] | None:
    raw = value.lstrip("#")
    if len(raw) in {3, 4}:
        raw = "".join(char * 2 for char in raw[:3])
    elif len(raw) in {6, 8}:
        raw = raw[:6]
    else:
        return None
    try:
        return tuple(int(raw[index : index + 2], 16) for index in (0, 2, 4))
    except ValueError:
        return None


def _color_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> float:
    return math.sqrt(sum((one - two) ** 2 for one, two in zip(left, right)))


def _measure_to_px(value: str) -> float | None:
    match = re.fullmatch(r"(-?(?:\d+(?:\.\d+)?|\.\d+))(px|rem|em|%)", value.lower())
    if not match:
        return None
    amount = float(match.group(1))
    unit = match.group(2)
    if unit == "px":
        return amount
    if unit in {"rem", "em"}:
        return amount * 16
    return None


def _finding(
    code: str,
    severity: str,
    message: str,
    *,
    category: str | None = None,
    evidence: list[dict[str, Any]] | None = None,
    limitation: str | None = None,
) -> dict[str, Any]:
    finding: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "category": category,
        "message": message,
        "evidence": evidence or [],
    }
    if limitation:
        finding["limitation"] = limitation
    return finding


def _iter_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        if root.suffix.lower() in SUPPORTED_EXTENSIONS:
            yield root
        return
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue
        if any(part in SKIP_DIRECTORIES for part in path.parts):
            continue
        yield path


def _scan_source(path: Path, root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    relative = _rel(path, root)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return (
            {"path": relative, "extension": path.suffix.lower(), "declarations": []},
            [
                _finding(
                    "unreadable_source",
                    "high",
                    f"could not read supported source: {error}",
                    limitation="The scanner does not decode binary or non-UTF-8 source.",
                )
            ],
        )
    findings: list[dict[str, Any]] = []
    if "\x00" in text:
        findings.append(
            _finding(
                "binary_like_source",
                "high",
                "source contains NUL bytes and was not analyzed reliably",
                limitation="Only text source is supported.",
            )
        )
    if path.suffix.lower() == ".json":
        try:
            json.loads(text)
        except json.JSONDecodeError as error:
            findings.append(
                _finding(
                    "invalid_json",
                    "high",
                    f"JSON token source is invalid at line {error.lineno}: {error.msg}",
                )
            )

    declarations: list[dict[str, Any]] = []
    matcher = DECLARATION if path.suffix.lower() in {".json", ".js", ".jsx", ".ts", ".tsx"} else PROPERTY
    for match in matcher.finditer(text):
        key = _strip_key(match.group("key"))
        value = match.group("value").strip().rstrip(",")
        category = _category_for(key, value)
        if category is None:
            continue
        declaration = {
            "file": relative,
            "line": _line_number(text, match.start()),
            "key": key,
            "value": value,
            "category": category,
            "is_token": _is_token_key(key, path.suffix.lower()),
            "context": text[match.start() : text.find("\n", match.start()) if "\n" in text[match.start():] else len(text)].strip()[:240],
        }
        declarations.append(declaration)
    return {"path": relative, "extension": path.suffix.lower(), "declarations": declarations}, findings


def _add_unique(findings: list[dict[str, Any]], seen: set[tuple[Any, ...]], finding: dict[str, Any]) -> None:
    evidence = finding.get("evidence", [])
    first = evidence[0] if evidence else {}
    key = (
        finding["code"],
        finding.get("category"),
        first.get("file"),
        first.get("line"),
        first.get("value"),
        finding["message"],
    )
    if key not in seen:
        seen.add(key)
        findings.append(finding)


def audit(root: Path, near_color_distance: float = 10.0, spacing_base: float = 4.0) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for path in _iter_files(root):
        source, source_findings = _scan_source(path, root)
        sources.append(source)
        for finding in source_findings:
            _add_unique(findings, seen, finding)

    declarations = [declaration for source in sources for declaration in source["declarations"]]
    token_categories = {
        category
        for category in {declaration["category"] for declaration in declarations}
        if category != "token-reference"
        and any(declaration["category"] == category and declaration["is_token"] for declaration in declarations)
    }

    color_occurrences: list[dict[str, Any]] = []
    for declaration in declarations:
        for match in HEX_COLOR.finditer(declaration["value"]):
            color_occurrences.append(
                {
                    **declaration,
                    "value": match.group(0).lower(),
                    "rgb": _rgb(match.group(0)),
                }
            )
        for match in RGB_COLOR.finditer(declaration["value"]):
            color_occurrences.append(
                {
                    **declaration,
                    "value": match.group(0),
                    "rgb": None,
                }
            )
    normalized_colors: dict[str, list[dict[str, Any]]] = {}
    for occurrence in color_occurrences:
        if occurrence["rgb"] is None:
            continue
        normalized = "#%02x%02x%02x" % occurrence["rgb"]
        normalized_colors.setdefault(normalized, []).append(occurrence)
    for color, occurrences in normalized_colors.items():
        token_occurrences = [occurrence for occurrence in occurrences if occurrence["is_token"]]
        keys = {occurrence["key"] for occurrence in token_occurrences}
        if len(token_occurrences) > 1 and len(keys) > 1:
            _add_unique(
                findings,
                seen,
                _finding(
                    "duplicate_color",
                    "low",
                    f"multiple token declarations resolve to {color}",
                    category="color",
                    evidence=[
                        {
                            "file": occurrence["file"],
                            "line": occurrence["line"],
                            "key": occurrence["key"],
                            "value": occurrence["value"],
                        }
                        for occurrence in token_occurrences
                    ],
                ),
            )
    token_colors = {
        color: occurrences[0]["rgb"]
        for color, occurrences in normalized_colors.items()
        if any(occurrence["is_token"] for occurrence in occurrences)
    }
    for (left_color, left_rgb), (right_color, right_rgb) in itertools.combinations(token_colors.items(), 2):
        if left_rgb is None or right_rgb is None:
            continue
        distance = _color_distance(left_rgb, right_rgb)
        if 0 < distance <= near_color_distance:
            _add_unique(
                findings,
                seen,
                _finding(
                    "near_duplicate_color",
                    "medium",
                    f"token colors {left_color} and {right_color} are visually near-duplicates (distance {distance:.2f})",
                    category="color",
                    evidence=[
                        {"value": left_color, "rgb": left_rgb},
                        {"value": right_color, "rgb": right_rgb},
                    ],
                    limitation="Distance is Euclidean RGB, not perceptual color difference.",
                ),
            )

    raw_by_category: dict[str, list[dict[str, Any]]] = {}
    token_by_category: dict[str, list[dict[str, Any]]] = {}
    for declaration in declarations:
        # A component using var(--token) is a token consumer, not a bypass.
        # Keep the expression in the source inventory, but exclude it from
        # raw-value findings.
        is_concrete_value = not re.search(r"\bvar\s*\(|^\s*\$[\w-]+", declaration["value"])
        if not is_concrete_value:
            continue
        bucket = token_by_category if declaration["is_token"] else raw_by_category
        bucket.setdefault(declaration["category"], []).append(declaration)

    for category in sorted(token_categories):
        non_tokens = raw_by_category.get(category, [])
        if not non_tokens:
            continue
        if category == "color":
            evidence = [
                {
                    "file": occurrence["file"],
                    "line": occurrence["line"],
                    "key": occurrence["key"],
                    "value": occurrence["value"],
                }
                for occurrence in color_occurrences
                if not occurrence["is_token"]
            ]
        else:
            evidence = [
                {
                    "file": declaration["file"],
                    "line": declaration["line"],
                    "key": declaration["key"],
                    "value": declaration["value"],
                }
                for declaration in non_tokens[:12]
            ]
        if not evidence:
            continue
        _add_unique(
            findings,
            seen,
            _finding(
                "token_bypass",
                "high",
                f"raw {category} values bypass declared {category} tokens",
                category=category,
                evidence=evidence,
                limitation="Static matching cannot resolve every alias, import, or computed value.",
            ),
        )

    spacing_literals: list[dict[str, Any]] = []
    for declaration in raw_by_category.get("spacing", []):
        for match in MEASURE.finditer(declaration["value"]):
            if declaration["key"].lower() in {"border", "outline", "transform", "translate", "opacity", "z-index"}:
                continue
            spacing_literals.append({**declaration, "value": match.group(0).lower()})
    distinct_spacing = {entry["value"] for entry in spacing_literals}
    off_scale = [
        entry
        for entry in spacing_literals
        if (pixels := _measure_to_px(entry["value"])) is not None
        and spacing_base > 0
        and abs(pixels / spacing_base - round(pixels / spacing_base)) > 0.001
    ]
    if len(distinct_spacing) >= 4 and off_scale:
        _add_unique(
            findings,
            seen,
            _finding(
                "spacing_drift",
                "medium",
                f"{len(distinct_spacing)} raw spacing values include values off the {spacing_base:g}px base rhythm",
                category="spacing",
                evidence=[
                    {
                        "file": entry["file"],
                        "line": entry["line"],
                        "key": entry["key"],
                        "value": entry["value"],
                    }
                    for entry in off_scale[:12]
                ],
                limitation="The base rhythm is a configurable heuristic; product-specific scales may be intentional.",
            ),
        )

    radius_values = {
        match.group(0).lower()
        for declaration in raw_by_category.get("radius", [])
        for match in MEASURE.finditer(declaration["value"])
    }
    if len(radius_values) > 4:
        _add_unique(
            findings,
            seen,
            _finding(
                "radius_drift",
                "medium",
                f"radius values proliferate across {len(radius_values)} raw values",
                category="radius",
                evidence=[{"value": value} for value in sorted(radius_values)],
                limitation="The scanner cannot infer whether a radius is semantically justified by a component.",
            ),
        )

    shadow_values = {
        declaration["value"]
        for declaration in raw_by_category.get("shadow", [])
        if declaration["value"]
    }
    if len(shadow_values) > 3:
        _add_unique(
            findings,
            seen,
            _finding(
                "shadow_proliferation",
                "medium",
                f"raw shadow declarations contain {len(shadow_values)} distinct values",
                category="shadow",
                evidence=[{"value": value[:180]} for value in sorted(shadow_values)],
                limitation="This does not judge whether an individual shadow is visually purposeful.",
            ),
        )

    font_families = {
        declaration["value"].split(",")[0].strip().strip("\"'")
        for declaration in raw_by_category.get("typography", [])
        if declaration["key"].lower() == "font-family"
    }
    if len(font_families) > 3:
        _add_unique(
            findings,
            seen,
            _finding(
                "typography_drift",
                "medium",
                f"raw font-family declarations use {len(font_families)} primary families",
                category="typography",
                evidence=[{"value": value} for value in sorted(font_families)],
                limitation="A family count alone cannot prove that a pairing is inappropriate.",
            ),
        )
    raw_type_values = {
        (declaration["key"].lower(), declaration["value"])
        for declaration in raw_by_category.get("typography", [])
    }
    if len(raw_type_values) > 5:
        _add_unique(
            findings,
            seen,
            _finding(
                "typography_scale_drift",
                "medium",
                f"typography declarations contain {len(raw_type_values)} raw role/value combinations",
                category="typography",
                evidence=[
                    {"key": key, "value": value}
                    for key, value in sorted(raw_type_values)[:12]
                ],
                limitation="The scanner cannot compute rendered measure or fallback metrics.",
            ),
        )

    counts = Counter(finding["severity"] for finding in findings)
    summary = {severity: counts.get(severity, 0) for severity in SEVERITY_ORDER}
    return {
        "schema_version": 1,
        "root": str(root),
        "files_scanned": [source["path"] for source in sources],
        "findings": findings,
        "summary": summary,
        "limitations": [
            "Static source scan only; no browser cascade, computed style, or runtime import graph is evaluated.",
            "CSS/SCSS/JS/TS syntax is matched conservatively with regular expressions, not a full parser.",
            "Near-duplicate colors use Euclidean RGB distance, not perceptual Delta E.",
            "A finding is a review signal, not proof that a deliberate exception is wrong.",
        ],
    }


def _render(payload: dict[str, Any], output_format: str) -> str:
    if output_format == "json":
        return json.dumps(payload, indent=2)
    lines = ["severity\tcode\tcategory\tmessage"]
    for finding in payload["findings"]:
        lines.append(
            f"{finding['severity']}\t{finding['code']}\t{finding.get('category') or '-'}\t{finding['message']}"
        )
    if not payload["findings"]:
        lines.append("pass\t-\t-\tno static findings")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--strict", action="store_true", help="fail on high or critical findings")
    parser.add_argument(
        "--near-color-distance",
        type=float,
        default=10.0,
        help="maximum Euclidean RGB distance for near-duplicate colors",
    )
    parser.add_argument(
        "--spacing-base",
        type=float,
        default=4.0,
        help="base pixel rhythm used by the spacing drift heuristic",
    )
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--output", "--json-output", dest="output", type=Path)
    args = parser.parse_args()
    if not args.root.exists():
        parser.error(f"not found: {args.root}")
    if args.near_color_distance < 0 or args.spacing_base <= 0:
        parser.error("near-color-distance must be non-negative and spacing-base must be positive")
    payload = audit(args.root, args.near_color_distance, args.spacing_base)
    rendered = _render(payload, args.format)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    strict_failure = any(
        SEVERITY_ORDER.get(finding["severity"], 0) >= SEVERITY_ORDER["high"]
        for finding in payload["findings"]
    )
    return 1 if args.strict and strict_failure else 0


if __name__ == "__main__":
    sys.exit(main())
