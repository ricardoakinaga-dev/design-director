#!/usr/bin/env python3
"""Evaluate evidence packets for frontend quality gates.

The packet is intentionally evidence-first. A missing section or a claimed
PASS without evidence becomes BLOCKED, never an implicit PASS. This script
does not run a browser or accessibility tool; those systems may produce the
packet consumed here.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


STATUSES = {"PASS", "WARN", "FAIL", "NOT_RUN", "BLOCKED", "NOT_APPLICABLE"}
BLOCKING_STATUSES = {"FAIL", "BLOCKED", "NOT_RUN"}

GATE_CHECKS: dict[str, dict[str, tuple[str, ...]]] = {
    "accessibility": {
        "keyboard": ("keyboard",),
        "focus": ("focus", "focus_visibility"),
        "semantics": ("semantics", "semantic_html"),
        "names": ("names", "accessible_names", "labels"),
        "errors": ("errors", "error_recovery", "error_messages"),
        "non_color": ("non_color", "non_color_cues"),
        "reduced_motion": ("reduced_motion",),
        "touch_targets": ("touch_targets", "touch"),
        "zoom_reflow": ("zoom_reflow", "zoom", "reflow"),
        "contrast": ("contrast",),
    },
    "performance": {
        "lcp": ("lcp", "lcp_ms"),
        "cls": ("cls", "cls_score"),
        "responsive_images": ("responsive_images", "srcset"),
        "font_loading": ("font_loading", "fonts"),
        "oversized_media": ("oversized_media", "media_budget"),
    },
    "typography": {
        "heading_hierarchy": ("heading_hierarchy", "headings"),
        "measure": ("measure", "line_length"),
        "line_height": ("line_height", "line-height"),
        "fallback": ("fallback", "font_fallback"),
        "numeric_alignment": ("numeric_alignment", "numerals"),
        "mobile_scale": ("mobile_scale", "responsive_scale"),
    },
    "copy_stress": {
        "short_content": ("short_content", "short"),
        "long_content": ("long_content", "long"),
        "empty_content": ("empty_content", "empty"),
        "large_numbers": ("large_numbers", "large", "large_content"),
        "localized_content": ("localized_content", "localized", "localization"),
    },
}

DEFAULT_THRESHOLDS = {
    "lcp_good_ms": 2500.0,
    "cls_good": 0.10,
}


def _normalise_status(value: Any) -> str | None:
    if isinstance(value, bool):
        return "PASS" if value else "FAIL"
    if isinstance(value, str):
        status = value.strip().upper().replace("-", "_").replace(" ", "_")
        aliases = {
            "OK": "PASS",
            "PASSED": "PASS",
            "SUCCESS": "PASS",
            "WARNING": "WARN",
            "FAILED": "FAIL",
            "UNAVAILABLE": "NOT_RUN",
            "NOTRUN": "NOT_RUN",
            "N_A": "NOT_APPLICABLE",
            "NA": "NOT_APPLICABLE",
        }
        status = aliases.get(status, status)
        return status if status in STATUSES else None
    return None


def _has_evidence(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple)):
        return any(_has_evidence(item) for item in value)
    if isinstance(value, dict):
        for key in ("evidence", "artifact", "artifacts", "source", "observed", "observation", "note"):
            if key in value and _has_evidence(value[key]):
                return True
        return False
    return value is not None and not isinstance(value, bool)


def _evidence_is_available(value: Any, root: Path | None) -> bool:
    """Check evidence presence and, when requested, local path provenance."""

    if not _has_evidence(value):
        return False
    if root is None:
        return True
    if isinstance(value, str):
        candidate = value.strip()
        if not candidate:
            return False
        if candidate.startswith(("http://", "https://", "file://", "data:")):
            # Without a root this is a declared external reference. With a
            # root, local verification is requested and a remote URI cannot
            # silently satisfy a PASS gate.
            return root is None
        path = (root / Path(candidate)).resolve()
        try:
            path.relative_to(root.resolve())
        except ValueError:
            return False
        try:
            return path.is_file() and path.stat().st_size > 0
        except OSError:
            return False
    if isinstance(value, (list, tuple)):
        return any(_evidence_is_available(item, root) for item in value)
    if isinstance(value, dict):
        evidence_keys = ("evidence", "artifact", "artifacts", "source")
        present = [value[key] for key in evidence_keys if key in value]
        return any(_evidence_is_available(item, root) for item in present)
    return True


def _detail(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {"status": value}


def _status_with_metric(
    value: Any,
    check_id: str,
    thresholds: dict[str, float],
) -> tuple[str | None, dict[str, Any]]:
    detail = _detail(value)
    declared_status = _normalise_status(detail.get("status"))
    numeric_value: float | None = None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric_value = float(value)
    for key in ("value", "value_ms", "metric", "score"):
        if numeric_value is None and isinstance(detail.get(key), (int, float)) and not isinstance(detail.get(key), bool):
            numeric_value = float(detail[key])
    if numeric_value is None:
        if check_id in {"lcp", "cls"}:
            return None, detail
        if declared_status:
            return declared_status, detail
        return None, detail
    detail["value"] = numeric_value
    if numeric_value < 0 or not math.isfinite(numeric_value):
        detail["status"] = "FAIL"
        detail["reason"] = "metric must be a finite non-negative number"
        return "FAIL", detail
    if check_id == "lcp":
        detail["status"] = "PASS" if numeric_value <= thresholds["lcp_good_ms"] else "FAIL"
    elif check_id == "cls":
        detail["status"] = "PASS" if numeric_value <= thresholds["cls_good"] else "FAIL"
    else:
        detail["status"] = "BLOCKED"
        detail["reason"] = "non-metric checks require an explicit status object"
        return "BLOCKED", detail
    computed_status = _normalise_status(detail["status"])
    if declared_status and declared_status != computed_status:
        detail["declared_status"] = declared_status
        detail["status_conflict"] = True
    return computed_status, detail


def _lookup(section: dict[str, Any], aliases: tuple[str, ...]) -> tuple[str | None, Any]:
    for alias in aliases:
        if alias in section:
            return alias, section[alias]
    return None, None


def _critical_from(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if value.get("critical") is True or value.get("blocking") is True:
        return True
    severity = value.get("severity")
    return isinstance(severity, str) and severity.strip().lower() in {"critical", "blocker"}


def _section_status(section: Any) -> str | None:
    if not isinstance(section, dict):
        return _normalise_status(section)
    return _normalise_status(section.get("status"))


def _evaluate_gate(
    gate_name: str,
    raw_section: Any,
    thresholds: dict[str, float],
    root: Path | None,
) -> dict[str, Any]:
    required = GATE_CHECKS[gate_name]
    section = raw_section if isinstance(raw_section, dict) else {}
    explicit_status = _section_status(raw_section)
    if raw_section is None:
        explicit_status = "BLOCKED"
    checks: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    failures: list[str] = []
    warnings: list[str] = []
    evidence_missing: list[str] = []
    critical_blockers: list[dict[str, Any]] = []

    for check_id, aliases in required.items():
        if explicit_status == "NOT_APPLICABLE":
            checks[check_id] = {
                "status": "NOT_APPLICABLE",
                "reason": "section explicitly scoped out",
            }
            continue
        alias, raw_value = _lookup(section, aliases)
        if alias is None:
            status = explicit_status if explicit_status in {"NOT_RUN", "BLOCKED"} else "BLOCKED"
            detail: dict[str, Any] = {
                "status": status,
                "reason": "evidence section/check is absent",
            }
            missing.append(check_id)
        else:
            status, detail = _status_with_metric(raw_value, check_id, thresholds)
            if status is None:
                status = "BLOCKED"
                detail["reason"] = "check has no recognized status or metric"
                missing.append(check_id)
            elif status in {"PASS", "WARN", "FAIL"} and not _evidence_is_available(raw_value, root):
                evidence_missing.append(check_id)
                detail = {
                    **detail,
                    "status": "BLOCKED",
                    "reason": "a claimed result requires present evidence",
                }
                status = "BLOCKED"
            if status == "FAIL":
                failures.append(check_id)
            elif status == "WARN":
                warnings.append(check_id)
            if status in {"NOT_RUN", "BLOCKED"} and check_id not in missing:
                missing.append(check_id)
            if status == "FAIL" and _critical_from(detail):
                critical_blockers.append({"check": check_id, "detail": detail})
        checks[check_id] = {
            "status": status,
            **{key: value for key, value in detail.items() if key != "status"},
        }

    declared_blockers = section.get("critical_blockers", [])
    if isinstance(declared_blockers, list):
        for blocker in declared_blockers:
            if blocker:
                critical_blockers.append({"source": "section", "blocker": blocker})
    elif declared_blockers:
        critical_blockers.append({"source": "section", "blocker": declared_blockers})

    if critical_blockers or failures:
        status = "FAIL"
    elif missing or evidence_missing:
        status = "BLOCKED"
    elif warnings:
        status = "CONDITIONAL"
    elif explicit_status == "NOT_APPLICABLE":
        status = "NOT_APPLICABLE"
    else:
        status = "PASS"
    result: dict[str, Any] = {
        "gate": gate_name,
        "status": status,
        "checks": checks,
        "missing": missing,
        "evidence_missing": evidence_missing,
        "failures": failures,
        "warnings": warnings,
        "critical_blockers": critical_blockers,
    }
    if explicit_status == "NOT_APPLICABLE":
        result["applicability_evidence"] = section.get("evidence") or section.get("reason")
        if not _evidence_is_available(section, root):
            result["status"] = "BLOCKED"
            result["missing"] = ["applicability_evidence"]
            result["reason"] = "NOT_APPLICABLE requires a scoped rationale"
    return result


def evaluate(packet: dict[str, Any], root: Path | None = None) -> dict[str, Any]:
    if not isinstance(packet, dict):
        raise ValueError("frontend quality packet must be a JSON object")
    raw_evidence = packet.get("evidence", packet)
    if not isinstance(raw_evidence, dict):
        raise ValueError("packet field 'evidence' must be an object")
    raw_thresholds = packet.get("thresholds", {})
    thresholds = dict(DEFAULT_THRESHOLDS)
    if isinstance(raw_thresholds, dict):
        for key in thresholds:
            value = raw_thresholds.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
                thresholds[key] = float(value)

    gates = [
        _evaluate_gate(gate_name, raw_evidence.get(gate_name), thresholds, root)
        for gate_name in GATE_CHECKS
    ]
    packet_blockers = packet.get("critical_blockers", [])
    critical_blockers: list[Any] = []
    if isinstance(packet_blockers, list):
        critical_blockers.extend(blocker for blocker in packet_blockers if blocker)
    elif packet_blockers:
        critical_blockers.append(packet_blockers)
    for gate in gates:
        critical_blockers.extend(gate["critical_blockers"])

    statuses = {gate["status"] for gate in gates}
    if critical_blockers or "FAIL" in statuses:
        overall_status = "FAIL"
    elif "BLOCKED" in statuses:
        overall_status = "BLOCKED"
    elif "CONDITIONAL" in statuses:
        overall_status = "CONDITIONAL"
    elif statuses and statuses <= {"PASS", "NOT_APPLICABLE"}:
        overall_status = "PASS"
    else:
        overall_status = "BLOCKED"
    return {
        "producer": "quality_gates.py",
        "schema_version": 1,
        "status": overall_status,
        "pass": overall_status == "PASS",
        "thresholds": thresholds,
        "gates": gates,
        "critical_blockers": critical_blockers,
        "limitations": [
            "This evaluator consumes evidence; it does not launch a browser, inspect a screen reader, or measure Core Web Vitals itself.",
            "A PASS is only as trustworthy as the referenced screenshots, interactions, source reports, and test environment.",
            "Performance thresholds are defaults and should be overridden by a product's documented budget when applicable.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("packet", type=Path, help="frontend evidence packet JSON")
    parser.add_argument("--output", "--json-output", dest="output", type=Path)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--root", type=Path, help="repository root for local evidence path checks")
    args = parser.parse_args()
    try:
        packet = json.loads(args.packet.read_text(encoding="utf-8"))
        result = evaluate(packet, args.root.resolve() if args.root else None)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        parser.error(str(error))
    if args.format == "json":
        rendered = json.dumps(result, indent=2)
    else:
        rendered = "\n".join(
            [f"overall\t{result['status']}"]
            + [f"{gate['gate']}\t{gate['status']}" for gate in result["gates"]]
        )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
