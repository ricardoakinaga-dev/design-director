#!/usr/bin/env python3
"""Score a visual benchmark run from declared evidence, not imagined pixels.

The scorer is deliberately conservative.  It computes a weighted normalized
mean only over ``applicable_dimensions`` (or all supplied dimensions when that
field is omitted), derives evidence confidence from the artifact/render/
inspection/critic chain, and applies quality gates independently of the mean.
It never trusts a run's declared ``overall`` or ``final_decision``.  A local
filesystem root is required to promote render/evidence confidence beyond a
blocked state; use ``--root`` explicitly in automation.  It decodes native PNG
evidence and validates its chain, but does not perform semantic computer vision,
so a PASS means that the declared review packet satisfies the contract, not
that this script has judged visual excellence.

The public CLI is ``score RUN.json [--benchmark BENCHMARK.json] [--root ROOT]``.
Exit codes are 0 for PASS/AAA CANDIDATE, 1 for a valid but failing or blocked
run, and 2 for invalid JSON/contracts.  ``validate`` is also available as a
small convenience wrapper around :mod:`benchmark_validate`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import zlib
from pathlib import Path
from typing import Any, Iterable

from audit_assets import inspect as inspect_asset
from compare_visual import PngError, decode_png
from quality_gates import GATE_CHECKS
from benchmark_validate import (
    APPROVAL_VERDICTS,
    PASS_VERDICTS,
    _benchmark_observation_matrix,
    _benchmark_region_ids,
    _benchmark_viewport_for_width,
    _independent_critic_is_qualified,
    _latest_record_id,
    _region_applies_to,
    _region_id,
    _parse_timestamp,
    _viewport_dpr,
    _viewport_height,
    _viewport_width,
    _dump,
    load_json,
    validate,
    validate_benchmark,
    validate_run,
)


SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "polish": 4}
CONFIDENCE_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
FRONTEND_REPORT_GATES = {"accessibility", "performance", "typography", "copy_stress"}
UI_CATEGORIES = {
    "banner",
    "banners",
    "landing-page",
    "landing-pages",
    "dashboard",
    "dashboards",
    "mobile",
    "mobile-flows",
    "reconstruction",
    "screenshot-reconstruction",
    "product-brand",
    "product-ads",
    "game-ui",
}
GATE_ALIASES = {
    "anti-slop": "anti_slop",
    "anti_slop": "anti_slop",
    "asset-acceptance": "asset_acceptance",
    "asset_acceptance": "asset_acceptance",
    "critical-findings": "critical_findings",
    "critical_findings": "critical_findings",
    "fidelity-ledger": "coverage",
    "independent-critic": "independent-critique",
    "independent_critic": "independent-critique",
    "native-asset-inspection": "inspection",
    "no-critical-findings": "critical_findings",
    "rendered-artifact": "render",
    "responsive-qa": "responsive",
    "state-matrix": "coverage",
    "viewport-matrix": "coverage",
}
DEFAULT_THRESHOLD = {
    "overall_min": 90,
    "aaa_min": 95,
    "evidence_confidence_min": "HIGH",
    "require_independent_critic": True,
    "block_critical": True,
    "block_high": True,
    "required_gates": [],
}
LIMITATION = (
    "Scores validate declared evidence and reviewer observations; this scorer "
    "does not perform semantic computer vision or infer visual quality from code."
)
RENDER_IMAGE_FORMATS = {"png"}
KNOWN_FILE_FORMATS = RENDER_IMAGE_FORMATS | {"avif", "gif", "jpeg", "jpg", "svg", "webp", "json", "markdown", "md", "html", "css", "component", "atlas"}


def _format_extensions(value: Any) -> set[str]:
    """Extract supported extension tokens from a human-readable format label."""

    if not isinstance(value, str):
        return set()
    lowered = value.lower()
    return {
        token
        for token in KNOWN_FILE_FORMATS
        if token in lowered.replace("+", " ").replace("/", " ").replace("-", " ")
    }


def _path_exists(root: Path | None, path: Any) -> bool | None:
    if not isinstance(path, str) or not path:
        return False
    if path.startswith(("http://", "https://", "file://", "data:")):
        return None
    if root is None:
        return None
    candidate = (root / Path(path)).resolve()
    try:
        return candidate.is_file() and candidate.stat().st_size > 0
    except OSError:
        return False


def _render_observable(
    root: Path | None,
    render: dict[str, Any],
    expected_viewport: Any | None = None,
) -> tuple[bool | None, str]:
    """Check that a declared render is a non-empty, locally inspectable artifact."""

    path = render.get("path")
    if isinstance(path, str) and path.startswith(("http://", "https://", "file://", "data:")):
        return None, "render URI cannot be locally decoded by this scorer"
    if root is None:
        return None, "filesystem root was not supplied"
    if not isinstance(path, str) or not path:
        return False, "render path is missing"
    candidate = (root / Path(path)).resolve()
    if not candidate.is_file():
        return False, "render file does not exist"
    if candidate.stat().st_size == 0:
        return False, "render file is empty"
    render_format = str(render.get("format", "")).lower()
    if render_format not in RENDER_IMAGE_FORMATS:
        return False, f"render format {render_format!r} is not a locally inspectable visual image"
    if render_format in RENDER_IMAGE_FORMATS:
        extension = candidate.suffix.lower().lstrip(".")
        compatible = {render_format}
        if render_format == "jpeg":
            compatible.add("jpg")
        if extension not in compatible:
            return False, f"render format {render_format!r} does not match file extension {extension!r}"
        try:
            decoded_width, decoded_height, _pixels = decode_png(candidate)
        except (OSError, PngError, ValueError, zlib.error) as error:
            return False, f"render image is not locally decodable as PNG: {error}"
        inspection = inspect_asset(candidate, root=root, max_bytes=None)
        dimensions = inspection.get("dimensions")
        if tuple(dimensions or ()) != (decoded_width, decoded_height):
            return False, "render image dimensions could not be confirmed by the native PNG decoder"
        declared_hash = render.get("sha256")
        if isinstance(declared_hash, str):
            actual_hash = hashlib.sha256(candidate.read_bytes()).hexdigest()
            if declared_hash.lower() != actual_hash:
                return False, "render sha256 does not match the local file"
        viewport = render.get("viewport") or expected_viewport
        expected_width = _viewport_width(viewport)
        expected_height = _viewport_height(viewport)
        if expected_width is not None and expected_height is not None:
            render_viewport = render.get("viewport")
            expected_dpr = _viewport_dpr(expected_viewport)
            if (
                isinstance(render_viewport, dict)
                and "dpr" in render_viewport
                and _viewport_dpr(render_viewport) != expected_dpr
            ):
                return False, f"render dpr does not match benchmark dpr {expected_dpr:g}"
            dpr = expected_dpr
            physical_width = round(expected_width * dpr)
            physical_height = round(expected_height * dpr)
            if tuple(dimensions) != (physical_width, physical_height):
                return False, (
                    f"render dimensions {dimensions!r} do not match declared viewport "
                    f"{expected_width}x{expected_height} at dpr {dpr:g} "
                    f"({physical_width}x{physical_height} physical pixels)"
                )
    return True, "render artifact is non-empty and observable"


def _gate(status: str, reason: str, evidence: Iterable[str] = ()) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "evidence": sorted(str(item) for item in evidence),
    }


def _findings_from_critique(critique: dict[str, Any], source: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    grouped = critique.get("findings", {})
    if isinstance(grouped, dict):
        for severity in ("critical", "high", "medium", "low", "polish"):
            values = grouped.get(severity, [])
            if isinstance(values, list):
                for index, finding in enumerate(values):
                    if isinstance(finding, dict):
                        item = dict(finding)
                        item.setdefault("severity", severity)
                        item["source"] = source
                        item.setdefault("id", f"{source}-{severity}-{index + 1}")
                        findings.append(item)
    violations = critique.get("constraint_violations", [])
    if isinstance(violations, list):
        for index, finding in enumerate(violations):
            if isinstance(finding, dict):
                item = dict(finding)
                item.setdefault("severity", "critical")
                item["source"] = source
                item.setdefault("id", f"{source}-constraint-{index + 1}")
                findings.append(item)
    return findings


def _findings_from_ledger(run: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for index, entry in enumerate(run.get("ledger", [])):
        if not isinstance(entry, dict):
            continue
        item = {
            "id": entry.get("id", f"ledger-{index + 1}"),
            "severity": entry.get("severity", "medium"),
            "description": entry.get("observed", ""),
            "location": entry.get("region", ""),
            "status": entry.get("status"),
            "source": "ledger",
        }
        findings.append(item)
    return findings


def _findings_from_inspections(run: dict[str, Any]) -> list[dict[str, Any]]:
    """Carry unresolved findings from the visual inspection boundary into the gate."""

    findings: list[dict[str, Any]] = []
    for index, inspection in enumerate(run.get("inspections", [])):
        if not isinstance(inspection, dict):
            continue
        raw_findings = inspection.get("findings", [])
        if not isinstance(raw_findings, list):
            continue
        for finding_index, finding in enumerate(raw_findings):
            if not isinstance(finding, dict):
                continue
            item = dict(finding)
            item.setdefault("id", f"inspection-{index + 1}-finding-{finding_index + 1}")
            item.setdefault("severity", "medium")
            item["source"] = f"inspection-{index + 1}"
            findings.append(item)
    return findings


def _is_resolved(finding: dict[str, Any]) -> bool:
    status = finding.get("status")
    severity = finding.get("severity")
    if severity == "critical":
        return status == "fixed"
    if severity == "high":
        return status in {"fixed", "accepted"}
    return status in {"fixed", "accepted"}


def _blockers(run: dict[str, Any]) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    for index, critique in enumerate(run.get("critiques", [])):
        if isinstance(critique, dict):
            collected.extend(_findings_from_critique(critique, f"critique-{index + 1}"))
    collected.extend(_findings_from_inspections(run))
    collected.extend(_findings_from_ledger(run))
    blockers: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for finding in collected:
        severity = finding.get("severity")
        if severity not in {"critical", "high"} or _is_resolved(finding):
            continue
        key = (str(finding.get("source")), str(finding.get("id")), str(finding.get("description")))
        if key in seen:
            continue
        seen.add(key)
        blockers.append(
            {
                "id": str(finding.get("id")),
                "severity": severity,
                "description": str(finding.get("description", "")),
                "location": str(finding.get("location", "")),
                "source": str(finding.get("source", "")),
                "status": finding.get("status"),
            }
        )
    return sorted(
        blockers,
        key=lambda item: (
            SEVERITY_ORDER.get(str(item["severity"]), 99),
            item["source"],
            item["id"],
            item["description"],
        ),
    )


def _latest_score(run: dict[str, Any]) -> dict[str, Any] | None:
    scores = run.get("scores", [])
    if not isinstance(scores, list):
        return None
    for score in reversed(scores):
        if isinstance(score, dict):
            return score
    return None


def _weighted_score(score_record: dict[str, Any] | None) -> dict[str, Any]:
    if not score_record:
        return {
            "overall": None,
            "applicable_dimensions": [],
            "dimension_scores": {},
            "weights": {},
            "declared_overall": None,
            "declared_overall_matches": None,
        }
    dimensions = score_record.get("dimensions", {})
    dimensions = dimensions if isinstance(dimensions, dict) else {}
    declared_applicable = score_record.get("applicable_dimensions")
    if isinstance(declared_applicable, list) and declared_applicable:
        applicable = [name for name in declared_applicable if name in dimensions]
    else:
        applicable = list(dimensions)
    applicable = sorted(set(str(name) for name in applicable))
    weights_payload = score_record.get("weights", {})
    weights = {
        name: float(weights_payload.get(name, 1))
        for name in applicable
        if isinstance(weights_payload, dict)
        and isinstance(weights_payload.get(name, 1), (int, float))
        and not isinstance(weights_payload.get(name, 1), bool)
    }
    for name in applicable:
        weights.setdefault(name, 1.0)
    numerator = sum(float(dimensions[name]) * weights[name] for name in applicable)
    denominator = sum(weights.values())
    overall = round((numerator / denominator) * 10, 2) if denominator else None
    declared_overall = score_record.get("overall")
    matches = None
    if isinstance(declared_overall, (int, float)) and not isinstance(declared_overall, bool) and overall is not None:
        matches = abs(float(declared_overall) - overall) <= 0.01
    return {
        "overall": overall,
        "applicable_dimensions": applicable,
        "dimension_scores": {name: dimensions[name] for name in applicable},
        "weights": {name: weights[name] for name in applicable},
        "declared_overall": declared_overall if isinstance(declared_overall, (int, float)) else None,
        "declared_overall_matches": matches,
    }


def _region_scores(run: dict[str, Any], score_record: dict[str, Any] | None) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    if score_record and isinstance(score_record.get("regions"), list):
        values.extend(item for item in score_record["regions"] if isinstance(item, dict))
    if not values:
        values.extend(
            {
                "region": entry.get("region"),
                "score": entry.get("score"),
                "viewport": entry.get("viewport"),
                "state": entry.get("state"),
                "evidence": entry.get("evidence", []),
            }
            for entry in run.get("ledger", [])
            if isinstance(entry, dict) and isinstance(entry.get("score"), (int, float))
        )
    normalized: list[dict[str, Any]] = []
    for value in values:
        if not isinstance(value.get("region"), str) or not isinstance(value.get("score"), (int, float)):
            continue
        viewport = value.get("viewport")
        if isinstance(viewport, dict):
            viewport_value: Any = viewport.get("width")
        else:
            viewport_value = viewport
        normalized.append(
            {
                "region": value["region"],
                "render_id": value.get("render_id"),
                "score": round(float(value["score"]), 2),
                "viewport": viewport_value,
                "state": value.get("state"),
                "evidence": sorted(value.get("evidence", [])) if isinstance(value.get("evidence"), list) else [],
            }
        )
    return sorted(
        normalized,
        key=lambda item: (
            item["region"],
            item["viewport"] if isinstance(item["viewport"], int) else -1,
            item["state"] or "",
        ),
    )


def _benchmark_matrix(benchmark: dict[str, Any] | None) -> tuple[set[int], set[str]]:
    if not benchmark:
        return set(), set()
    observations = _benchmark_observation_matrix(benchmark)
    widths = {width for width, _state, _viewport, _state_record in observations}
    states = {state for _width, state, _viewport, _state_record in observations}
    return widths, states


def _artifact_completeness_gate(
    run: dict[str, Any],
    benchmark: dict[str, Any] | None,
    root: Path | None,
) -> dict[str, Any]:
    if benchmark is None:
        return _gate("not-applicable", "no benchmark contract was supplied")
    expected = [
        item for item in benchmark.get("expected_artifacts", [])
        if isinstance(item, dict) and item.get("required", True) is not False
    ]
    actual = {
        item.get("id"): item
        for item in run.get("artifacts", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    missing = [item.get("id") for item in expected if item.get("id") not in actual]
    incomplete = [
        item.get("id")
        for item in expected
        if item.get("id") in actual and actual[item.get("id")].get("status") != "produced"
    ]
    unverified: list[str] = []
    content_errors: list[str] = []
    if root is None:
        unverified = [str(item.get("id")) for item in expected if item.get("id") in actual]
    else:
        for item in expected:
            artifact = actual.get(item.get("id"))
            if not isinstance(artifact, dict):
                continue
            path = artifact.get("path")
            if not _path_exists(root, path):
                incomplete.append(str(item.get("id")))
                continue
            candidate = (root / Path(path)).resolve() if isinstance(path, str) else None
            if candidate is not None and candidate.stat().st_size == 0:
                content_errors.append(f"{item.get('id')} is empty")
            expected_format = str(item.get("format", "")).lower()
            if candidate is not None and expected_format:
                allowed_extensions = _format_extensions(expected_format)
                if allowed_extensions:
                    extension = candidate.suffix.lower().lstrip(".")
                    aliases = {
                        "markdown": {"markdown", "md"},
                        "component": {"component", "html", "css", "js", "jsx", "ts", "tsx", "vue", "svelte"},
                    }
                    accepted_extensions = set().union(
                        *(aliases.get(token, {token}) for token in allowed_extensions)
                    )
                    if extension not in accepted_extensions:
                        content_errors.append(
                            f"{item.get('id')} extension {extension!r} does not match {expected_format!r}"
                        )
            if candidate is not None and candidate.suffix.lower() == ".json":
                try:
                    structured_payload = json.loads(candidate.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                    content_errors.append(f"{item.get('id')} contains invalid JSON: {error}")
                else:
                    structured_kind = {
                        "ledger": "ledger",
                        "critique": "critic",
                    }.get(str(item.get("kind", "")).lower())
                    if structured_kind:
                        content_errors.extend(
                            f"{item.get('id')}: {error}"
                            for error in validate(structured_kind, structured_payload, root)
                        )
            declared_hash = artifact.get("sha256")
            if candidate is not None and isinstance(declared_hash, str):
                digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
                if digest != declared_hash.lower():
                    content_errors.append(f"{item.get('id')} sha256 does not match its file")
    if missing or incomplete or content_errors:
        reasons: list[str] = []
        if missing:
            reasons.append(f"missing required artifacts: {', '.join(sorted(str(item) for item in missing))}")
        if incomplete:
            reasons.append(f"required artifacts are not produced or not found: {', '.join(sorted(set(incomplete)))}")
        if content_errors:
            reasons.extend(content_errors)
        return _gate("fail", "; ".join(reasons))
    if unverified:
        return _gate("blocked", "artifact paths were not checked because filesystem root was not supplied")
    return _gate(
        "pass",
        "all required benchmark artifacts are bound and produced",
        [str(actual[item.get("id")].get("path")) for item in expected],
    )


def _latest_render_ids_by_pair(run: dict[str, Any]) -> dict[tuple[int, str], str]:
    """Return the current render for each viewport/state pair.

    Render arrays are append-ordered.  Keeping this binding explicit prevents
    a passing ledger entry from an earlier iteration from satisfying coverage
    after a newer render exists for the same viewport and state.
    """

    latest: dict[tuple[int, str], str] = {}
    for render in run.get("renders", []):
        if not isinstance(render, dict):
            continue
        render_id = render.get("id")
        width = _viewport_width(render.get("viewport"))
        state = render.get("state")
        if isinstance(render_id, str) and isinstance(width, int) and isinstance(state, str):
            latest[(width, state)] = render_id
    return latest


def _region_observation_keys(
    run: dict[str, Any],
    score_record: dict[str, Any] | None,
    root: Path | None,
) -> tuple[set[tuple[str, int, str]], list[str]]:
    observed: dict[tuple[str, int, str], bool] = {}
    latest_render_ids = _latest_render_ids_by_pair(run)
    values: list[dict[str, Any]] = []
    if score_record and isinstance(score_record.get("regions"), list):
        values.extend(item for item in score_record["regions"] if isinstance(item, dict))
    for entry in run.get("ledger", []):
        if isinstance(entry, dict):
            values.append(entry)
    for value in values:
        region = value.get("region")
        viewport = value.get("viewport")
        width = _viewport_width(viewport)
        state = value.get("state")
        evidence = value.get("evidence")
        if isinstance(region, str) and isinstance(width, int) and isinstance(state, str):
            current_render_id = latest_render_ids.get((width, state))
            if value.get("render_id") != current_render_id:
                continue
            status = value.get("status")
            if status not in {"not-run", "blocked"}:
                key = (region, width, state)
                if root is None:
                    evidence_available = bool(evidence)
                elif isinstance(evidence, list):
                    evidence_available = any(_path_exists(root, item) is True for item in evidence)
                else:
                    evidence_available = False
                observed[key] = observed.get(key, False) or evidence_available
    keys = {key for key, has_evidence in observed.items() if has_evidence}
    missing_evidence = [
        f"{region}/{width}px/{state}"
        for (region, width, state), has_evidence in observed.items()
        if not has_evidence
    ]
    return keys, sorted(set(missing_evidence))


def _coverage_gate(
    run: dict[str, Any],
    benchmark: dict[str, Any] | None,
    score_record: dict[str, Any] | None,
    root: Path | None,
) -> dict[str, Any]:
    if benchmark is None:
        return _gate("not-applicable", "no benchmark contract was supplied")
    matrix = _benchmark_observation_matrix(benchmark)
    expected_pairs = {(width, state_id) for width, state_id, _viewport, _state in matrix}
    renders = [item for item in run.get("renders", []) if isinstance(item, dict)]
    observed_pairs = {
        (_viewport_width(item.get("viewport")), item.get("state"))
        for item in renders
    }
    missing_pairs = sorted(
        expected_pairs - observed_pairs,
        key=lambda pair: (pair[0] or -1, pair[1]),
    )
    region_keys, missing_evidence = _region_observation_keys(run, score_record, root)
    benchmark_regions = [
        region for region in benchmark.get("regions", [])
        if _region_id(region) in _benchmark_region_ids(benchmark)
    ]
    expected_regions: set[tuple[str, int, str]] = set()
    for width, state_id, viewport, state in matrix:
        for region in benchmark_regions:
            region_id = _region_id(region)
            if region_id and _region_applies_to(region, viewport, state):
                expected_regions.add((region_id, width, state_id))
    missing_regions = sorted(
        expected_regions - region_keys,
        key=lambda item: (item[1], item[2], item[0]),
    )
    if missing_pairs or missing_regions or missing_evidence:
        evidence = [
            *[f"viewport/state {width}px/{state}" for width, state in missing_pairs],
            *[f"region {region}/{width}px/{state}" for region, width, state in missing_regions],
            *[f"missing region evidence {item}" for item in missing_evidence],
        ]
        return _gate("blocked", "benchmark observation matrix is incomplete", evidence)
    return _gate(
        "pass",
        "all required viewport/state pairs and applicable semantic regions are observed",
        [f"{region}/{width}px/{state}" for region, width, state in sorted(expected_regions, key=lambda item: (item[1], item[2], item[0]))],
    )


def _canonical_gate_name(name: Any) -> str:
    raw = str(name).strip().lower()
    return GATE_ALIASES.get(raw, raw)


def _load_quality_report(report: Any, root: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    if isinstance(report, dict):
        return report, None
    if isinstance(report, str) and root is not None:
        path = (root / Path(report)).resolve()
        try:
            path.relative_to(root.resolve())
            return json.loads(path.read_text(encoding="utf-8")), None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
            return None, f"quality report could not be read: {error}"
    return None, "a quality report object or local quality report path is required"


def _quality_report_gate(
    run_gate: dict[str, Any],
    name: str,
    root: Path | None,
) -> dict[str, Any]:
    report, error = _load_quality_report(run_gate.get("report"), root)
    if error or not isinstance(report, dict):
        return _gate("blocked", error or "quality report is invalid")
    report_thresholds = report.get("thresholds", {}) if isinstance(report.get("thresholds"), dict) else {}
    lcp_good_ms = report_thresholds.get("lcp_good_ms", 2500.0)
    cls_good = report_thresholds.get("cls_good", 0.10)
    if not isinstance(lcp_good_ms, (int, float)) or isinstance(lcp_good_ms, bool) or lcp_good_ms <= 0 or not math.isfinite(float(lcp_good_ms)):
        lcp_good_ms = 2500.0
    if not isinstance(cls_good, (int, float)) or isinstance(cls_good, bool) or cls_good <= 0 or not math.isfinite(float(cls_good)):
        cls_good = 0.10
    if report.get("producer") not in {"quality_gates.py", "quality-gates"}:
        return _gate("blocked", "quality report producer is not quality_gates.py")
    if report.get("status") not in {"PASS", "pass"} or report.get("pass") is not True:
        return _gate("fail", f"quality report for {name} is not PASS")
    if isinstance(report.get("gates"), list):
        matching = [
            item
            for item in report["gates"]
            if isinstance(item, dict) and item.get("gate") in {name, name.replace("_", "-")}
        ]
        if len(matching) != 1:
            return _gate("blocked", f"quality report has no unique {name} gate")
        report = matching[0]
    elif report.get("gate") != name:
        return _gate("blocked", f"quality report is for {report.get('gate')!r}, not {name!r}")
    checks = report.get("checks")
    if not isinstance(checks, dict) or not checks:
        return _gate("blocked", f"quality report for {name} has no check results")
    required_checks = set(GATE_CHECKS.get(name, {}))
    missing_checks = sorted(required_checks - set(checks))
    if missing_checks:
        return _gate(
            "blocked",
            f"quality report for {name} is missing required checks: {', '.join(missing_checks)}",
        )
    non_pass = [
        check_id
        for check_id, detail in checks.items()
        if not isinstance(detail, dict) or detail.get("status") not in {"PASS", "pass"}
    ]
    if non_pass:
        return _gate("fail", f"quality report has non-PASS checks: {', '.join(sorted(str(item) for item in non_pass))}")
    evidence_missing = []
    for check_id in sorted(required_checks):
        detail = checks.get(check_id)
        if not isinstance(detail, dict):
            evidence_missing.append(check_id)
            continue
        evidence = detail.get("evidence")
        evidence_values = [evidence] if isinstance(evidence, str) else evidence if isinstance(evidence, list) else []
        evidence_available = bool(evidence_values) if root is None else any(
            _path_exists(root, item) is True for item in evidence_values
        )
        if not evidence_available:
            evidence_missing.append(check_id)
    if evidence_missing:
        return _gate(
            "blocked",
            "quality report checks require declared and locally available evidence: "
            + ", ".join(evidence_missing),
        )
    if name == "performance":
        metric_limits = {"lcp": float(lcp_good_ms), "cls": float(cls_good)}
        for metric_name, limit in metric_limits.items():
            detail = checks.get(metric_name)
            if not isinstance(detail, dict):
                return _gate("blocked", f"performance report is missing computed {metric_name} metric")
            value = detail.get("value", detail.get("value_ms"))
            if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0 or not math.isfinite(float(value)):
                return _gate("fail", f"performance report has invalid {metric_name} metric")
            expected_status = "PASS" if float(value) <= limit else "FAIL"
            declared_status = str(detail.get("status", "")).upper()
            if declared_status != expected_status:
                return _gate(
                    "fail",
                    f"performance report {metric_name} status does not match its metric ({value:g} vs {limit:g})",
                )
    return _gate("pass", f"{name} is backed by a computed quality-gates report", [str(run_gate.get("report"))])


def _declared_gate(run: dict[str, Any], name: str, root: Path | None = None) -> dict[str, Any] | None:
    gates = run.get("gates", {})
    if not isinstance(gates, dict) or not isinstance(gates.get(name), dict):
        return None
    gate = gates[name]
    if name in FRONTEND_REPORT_GATES and str(gate.get("status", "")).lower() == "pass":
        return _quality_report_gate(gate, name, root)
    return _gate(
        str(gate.get("status", "blocked")),
        str(gate.get("notes", "declared gate")),
        gate.get("evidence", []) if isinstance(gate.get("evidence"), list) else [],
    )


def _compute_gates(
    run: dict[str, Any],
    benchmark: dict[str, Any] | None,
    root: Path | None,
    score_record: dict[str, Any] | None,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    gates: dict[str, dict[str, Any]] = {}
    limitations: list[str] = []
    execution = run.get("execution")
    execution_status = execution.get("status") if isinstance(execution, dict) else None
    if execution_status == "complete":
        gates["execution"] = _gate("pass", "execution status is complete", ["execution.status"])
    else:
        gates["execution"] = _gate(
            "blocked",
            f"execution status {execution_status!r} is not complete",
        )
        limitations.append("The run is not eligible for visual approval until execution status is complete.")
    renders = [item for item in run.get("renders", []) if isinstance(item, dict)]
    render_paths = [item.get("path") for item in renders]
    if not renders:
        gates["render"] = _gate("blocked", "no render records were supplied")
    elif root is None:
        gates["render"] = _gate("blocked", "filesystem root was not supplied; render existence is unverified")
        limitations.append("Render paths were declared but not checked because no --root was supplied.")
    else:
        render_checks = [
            _render_observable(
                root,
                item,
                _benchmark_viewport_for_width(benchmark, _viewport_width(item.get("viewport"))),
            )
            for item in renders
        ]
        if all(status is True for status, _reason in render_checks):
            gates["render"] = _gate("pass", "all declared renders are observable", [str(path) for path in render_paths])
        else:
            reasons = sorted({reason for status, reason in render_checks if status is not True})
            has_unobservable = any(status is False for status, _reason in render_checks)
            gates["render"] = _gate(
                "fail" if has_unobservable else "blocked",
                "; ".join(reasons) or "one or more renders are not observable",
            )

    inspections = [item for item in run.get("inspections", []) if isinstance(item, dict)]
    passing_inspections = [item for item in inspections if item.get("status") == "pass"]
    latest_render_id = _latest_record_id(run, "renders")
    latest_inspection_id = _latest_record_id(run, "inspections")
    passing_by_render = {
        item.get("render_id"): item
        for item in passing_inspections
        if isinstance(item.get("render_id"), str)
    }
    if not inspections:
        gates["inspection"] = _gate("blocked", "no inspection record was supplied")
    elif latest_render_id not in passing_by_render:
        latest_status = inspections[-1].get("status")
        gates["inspection"] = _gate(
            "fail" if latest_status == "fail" else "blocked",
            "the latest render does not have a passing inspection",
        )
    elif len(passing_by_render) < len({item.get("id") for item in renders}):
        missing_render_ids = sorted(
            set(item.get("id") for item in renders if isinstance(item.get("id"), str)) - set(passing_by_render)
        )
        gates["inspection"] = _gate(
            "blocked",
            "one or more renders do not have a passing inspection",
            missing_render_ids,
        )
    elif inspections[-1].get("status") != "pass" or inspections[-1].get("render_id") != latest_render_id:
        gates["inspection"] = _gate(
            "fail" if inspections[-1].get("status") == "fail" else "blocked",
            "the latest inspection is not a passing inspection of the latest render",
        )
    else:
        evidence = [
            path
            for item in passing_inspections
            for path in item.get("evidence", [])
            if isinstance(path, str)
        ]
        if root is None:
            gates["inspection"] = _gate("blocked", "inspection evidence existence is unverified")
            limitations.append("Inspection evidence was declared but not checked because no --root was supplied.")
        elif evidence and all(_path_exists(root, path) for path in evidence):
            gates["inspection"] = _gate("pass", "a passing inspection has existing evidence", evidence)
        else:
            gates["inspection"] = _gate("fail", "a passing inspection has missing or empty evidence")
    latest_inspection = inspections[-1] if inspections else None

    critiques = [item for item in run.get("critiques", []) if isinstance(item, dict)]
    latest_critic = critiques[-1] if critiques else None
    if latest_critic is None or not _independent_critic_is_qualified(latest_critic):
        gates["independent-critique"] = _gate(
            "blocked",
            "the latest critique is not an auditable blinded independent result",
        )
    else:
        latest = latest_critic
        verdict = latest.get("verdict")
        missing = latest.get("evidence_missing", [])
        if latest.get("inspection_id") != latest_inspection_id or gates.get("inspection", {}).get("status") != "pass":
            gates["independent-critique"] = _gate(
                "blocked",
                "independent critic is not linked to the latest passing inspection",
            )
        elif missing:
            gates["independent-critique"] = _gate("blocked", "independent critic reports missing evidence", missing)
        elif verdict == "FAIL":
            gates["independent-critique"] = _gate("fail", "independent critic verdict is FAIL")
        elif verdict == "PASS":
            gates["independent-critique"] = _gate("pass", f"independent critic verdict is {verdict}")
        else:
            gates["independent-critique"] = _gate(
                "blocked",
                f"independent critic verdict is not an approval: {verdict}",
            )

    if score_record is None:
        gates["score"] = _gate("blocked", "no score record was supplied")
    elif latest_inspection_id is None or score_record.get("inspection_id") != latest_inspection_id:
        gates["score"] = _gate("blocked", "latest score is not linked to the latest inspection")
    elif gates.get("inspection", {}).get("status") != "pass":
        gates["score"] = _gate("blocked", "latest score is not backed by a passing current inspection")
    else:
        gates["score"] = _gate("pass", "latest score is linked to the latest passing inspection")

    if benchmark:
        gates["artifact_completeness"] = _artifact_completeness_gate(run, benchmark, root)
        gates["coverage"] = _coverage_gate(run, benchmark, score_record, root)
        expected_widths, _expected_states = _benchmark_matrix(benchmark)
        if len(expected_widths) > 1:
            gates["responsive"] = _declared_gate(run, "responsive", root) or _gate(
                "blocked",
                "multiple viewports require an explicit responsive gate",
            )
        else:
            gates["responsive"] = _declared_gate(run, "responsive", root) or _gate(
                "not-applicable",
                "benchmark declares one viewport",
            )
        reference_paths = [
            item.get("path")
            for item in benchmark.get("references", [])
            if isinstance(item, dict) and item.get("path")
        ]
        if not reference_paths:
            gates["reference"] = _gate("not-applicable", "benchmark has no local references")
        elif root is None:
            gates["reference"] = _gate("blocked", "reference existence is unverified")
        elif all(_path_exists(root, path) for path in reference_paths):
            gates["reference"] = _gate("pass", "all local references exist", [str(path) for path in reference_paths])
        else:
            gates["reference"] = _gate("fail", "one or more local references are missing")
    else:
        gates["artifact_completeness"] = _gate("not-applicable", "no benchmark contract was supplied")
        gates["coverage"] = _gate("not-applicable", "no benchmark contract was supplied")
        gates["responsive"] = _gate("not-applicable", "no benchmark contract was supplied")
        gates["reference"] = _gate("not-applicable", "no benchmark contract was supplied")

    for gate_name in (
        "identity",
        "accessibility",
        "performance",
        "anti_slop",
        "asset_acceptance",
        "typography",
        "copy_stress",
    ):
        gates[gate_name] = _declared_gate(run, gate_name, root) or _gate(
            "blocked",
            f"{gate_name} gate was not supplied",
        )
    critical_count = sum(item.get("severity") == "critical" for item in _blockers(run))
    gates["critical_findings"] = _gate(
        "pass" if critical_count == 0 else "fail",
        "no unresolved critical findings" if critical_count == 0 else f"{critical_count} unresolved critical finding(s)",
    )
    return gates, limitations


def _evidence_confidence(gates: dict[str, dict[str, Any]]) -> str:
    artifact_pass = gates.get("artifact_completeness", {}).get("status") == "pass"
    execution_pass = gates.get("execution", {}).get("status") == "pass"
    render_pass = gates.get("render", {}).get("status") == "pass"
    inspection_pass = gates.get("inspection", {}).get("status") == "pass"
    critic_pass = gates.get("independent-critique", {}).get("status") == "pass"
    score_pass = gates.get("score", {}).get("status") == "pass"
    coverage_status = gates.get("coverage", {}).get("status")
    reference_status = gates.get("reference", {}).get("status")
    if execution_pass and artifact_pass and render_pass and inspection_pass and score_pass and critic_pass and coverage_status in {"pass", "not-applicable"} and reference_status in {"pass", "not-applicable"}:
        return "HIGH"
    if render_pass and inspection_pass:
        return "MEDIUM"
    return "LOW"


def _aaa_requirements(
    run: dict[str, Any],
    benchmark: dict[str, Any] | None,
    overall: float | None,
    evidence_confidence: str,
    blockers: list[dict[str, Any]],
    gates: dict[str, dict[str, Any]],
    threshold: dict[str, Any],
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    aaa_min = threshold.get("aaa_min", 95)
    if overall is None or overall < aaa_min:
        reasons.append(f"overall score is below AAA minimum {aaa_min}")
    if any(item.get("severity") == "critical" for item in blockers):
        reasons.append("critical blocker remains")
    if any(item.get("severity") == "high" for item in blockers):
        reasons.append("high blocker remains")
    if evidence_confidence != "HIGH":
        reasons.append("evidence confidence is not HIGH")
    if gates.get("execution", {}).get("status") != "pass":
        reasons.append("execution is not complete")
    if gates.get("independent-critique", {}).get("status") != "pass":
        reasons.append("independent critique did not pass its evidence gate")
    if gates.get("score", {}).get("status") != "pass":
        reasons.append("score is not linked to the latest passing inspection")
    if gates.get("artifact_completeness", {}).get("status") != "pass":
        reasons.append("required benchmark artifacts are not complete")
    if gates.get("coverage", {}).get("status") != "pass":
        reasons.append("viewport/state/region coverage is incomplete")
    if gates.get("anti_slop", {}).get("status") != "pass":
        reasons.append("anti-slop gate is not PASS")
    if benchmark and len(_benchmark_matrix(benchmark)[0]) > 1 and gates.get("responsive", {}).get("status") != "pass":
        reasons.append("responsive QA was not completed")
    identity_required = bool(
        benchmark
        and (
            benchmark.get("references")
            or benchmark.get("preservation_rules", {}).get("immutable")
            or benchmark.get("preservation_rules", {}).get("high_sensitivity")
        )
    )
    if identity_required and gates.get("identity", {}).get("status") != "pass":
        reasons.append("identity gate is not PASS")
    accessibility_required = bool(
        benchmark
        and (
            benchmark.get("category") in UI_CATEGORIES
            or any(item.get("kind") == "ui" for item in benchmark.get("expected_artifacts", []) if isinstance(item, dict))
        )
    )
    if accessibility_required and gates.get("accessibility", {}).get("status") != "pass":
        reasons.append("accessibility gate is not PASS")
    return not reasons, reasons


def score_run(
    run: dict[str, Any],
    benchmark: dict[str, Any] | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    validation_errors = validate_run(run, root, benchmark, enforce_final=False)
    if validation_errors:
        return {
            "status": "invalid",
            "benchmark_id": run.get("benchmark_id") if isinstance(run, dict) else None,
            "run_id": run.get("run_id") if isinstance(run, dict) else None,
            "errors": validation_errors,
            "limitations": [LIMITATION],
        }

    threshold = dict(DEFAULT_THRESHOLD)
    if benchmark and isinstance(benchmark.get("quality_threshold"), dict):
        threshold.update(benchmark["quality_threshold"])
    score_record = _latest_score(run)
    weighted = _weighted_score(score_record)
    gates, limitations = _compute_gates(run, benchmark, root, score_record)
    evidence_confidence = _evidence_confidence(gates)
    blockers = _blockers(run)
    overall = weighted["overall"]
    if overall is None:
        quality_band = "UNSCORED"
    elif overall < 70:
        quality_band = "FAIL"
    elif overall < 80:
        quality_band = "MAJOR REVISION"
    elif overall < 90:
        quality_band = "POLISH REQUIRED"
    elif overall < 95:
        quality_band = "PASS"
    else:
        quality_band = "AAA CANDIDATE"

    required_confidence = str(threshold.get("evidence_confidence_min", "HIGH"))
    confidence_gate = CONFIDENCE_ORDER.get(evidence_confidence, 0) >= CONFIDENCE_ORDER.get(required_confidence, 2)
    required_gates = threshold.get("required_gates", [])
    required_gates = required_gates if isinstance(required_gates, list) else []
    gate_failures: list[str] = []
    if weighted["declared_overall_matches"] is False:
        gate_failures.append("score record overall does not match the computed score")
    for gate_name in required_gates:
        canonical_name = _canonical_gate_name(gate_name)
        if canonical_name == "critical_findings":
            status = "pass" if not any(item.get("severity") == "critical" for item in blockers) else "fail"
        else:
            status = gates.get(canonical_name, {}).get("status")
        if status != "pass":
            gate_failures.append(f"required gate {gate_name} is {status or 'missing'}")
    if not confidence_gate:
        gate_failures.append(
            f"evidence confidence {evidence_confidence} is below required {required_confidence}"
        )
    if threshold.get("require_independent_critic", True) and gates.get("independent-critique", {}).get("status") != "pass":
        gate_failures.append("independent critic evidence is required")
    if gates.get("execution", {}).get("status") != "pass":
        gate_failures.append("execution status is not complete")
    if gates.get("render", {}).get("status") != "pass":
        gate_failures.append("render evidence is not verified")
    if gates.get("inspection", {}).get("status") != "pass":
        gate_failures.append("passing inspection evidence is not verified")
    if gates.get("score", {}).get("status") != "pass":
        gate_failures.append("score is not verified against the latest inspection")
    if benchmark is not None:
        for gate_name in ("artifact_completeness", "coverage"):
            if gates.get(gate_name, {}).get("status") != "pass":
                gate_failures.append(f"{gate_name.replace('_', ' ')} gate is not PASS")
        if benchmark.get("references") and gates.get("reference", {}).get("status") != "pass":
            gate_failures.append("reference evidence is not verified")
    else:
        gate_failures.append("benchmark contract is required for visual approval")

    human_override = run.get("human_override")
    override_requested = isinstance(human_override, dict) and human_override.get("accepted_below_threshold") is True
    hard_blockers = any(item["severity"] in {"critical", "high"} for item in blockers)
    if override_requested and not gate_failures and not hard_blockers and overall is not None:
        decision = "CONDITIONAL PASS"
    elif blockers and any(item["severity"] == "critical" for item in blockers):
        decision = "FAIL"
    elif gate_failures:
        decision = "BLOCKED"
    elif blockers and threshold.get("block_high", True) and any(item["severity"] == "high" for item in blockers):
        decision = "FAIL"
    elif overall is None:
        decision = "BLOCKED"
    elif overall < 70:
        decision = "FAIL"
    elif overall < 80:
        decision = "FAIL"
    elif overall < 90:
        decision = "FAIL"
    elif overall < float(threshold.get("overall_min", 90)):
        decision = "FAIL"
    else:
        aaa_candidate, aaa_reasons = _aaa_requirements(
            run,
            benchmark,
            overall,
            evidence_confidence,
            blockers,
            gates,
            threshold,
        )
        decision = "AAA CANDIDATE" if aaa_candidate else "PASS"

    aaa_candidate, aaa_blockers = _aaa_requirements(
        run,
        benchmark,
        overall,
        evidence_confidence,
        blockers,
        gates,
        threshold,
    )
    if override_requested:
        aaa_candidate = False
        aaa_blockers = [*aaa_blockers, "human override prevents AAA classification"]
    final_record = run.get("final_decision") if isinstance(run.get("final_decision"), dict) else {}
    declared_final = final_record.get("verdict")
    final_consistency_failures: list[str] = []
    declared_final_score = final_record.get("score")
    approval_decision = decision in APPROVAL_VERDICTS
    numeric_final_score = isinstance(declared_final_score, (int, float)) and not isinstance(declared_final_score, bool)
    if approval_decision and not numeric_final_score:
        final_consistency_failures.append("an approval decision requires an explicit final score")
    elif numeric_final_score:
        if overall is None or abs(float(declared_final_score) - float(overall)) > 0.01:
            final_consistency_failures.append("final decision score does not match the computed score")
    declared_final_confidence = final_record.get("evidence_confidence")
    if approval_decision and not isinstance(declared_final_confidence, str):
        final_consistency_failures.append("an approval decision requires explicit evidence confidence")
    elif isinstance(declared_final_confidence, str) and declared_final_confidence != evidence_confidence:
        final_consistency_failures.append("final decision evidence confidence does not match computed confidence")
    approved_by = str(final_record.get("approved_by", "")).strip()
    if approval_decision and not approved_by:
        final_consistency_failures.append("an approval decision requires an explicit approved_by")
    if approval_decision:
        for field in ("decided_at", "evidence", "render_ids", "inspection_id", "score_id", "critique_id"):
            value = final_record.get(field)
            if field in {"evidence", "render_ids"}:
                present = isinstance(value, list) and bool(value)
            else:
                present = isinstance(value, str) and bool(value.strip())
            if not present:
                final_consistency_failures.append(f"approval requires final_decision.{field}")
        final_time = _parse_timestamp(final_record.get("decided_at"))
        if final_time is None:
            final_consistency_failures.append("approval requires a timezone-aware final decision timestamp")
        latest_render_id = _latest_record_id(run, "renders")
        latest_inspection_id = _latest_record_id(run, "inspections")
        latest_score_id = _latest_record_id(run, "scores")
        latest_critique_id = _latest_record_id(run, "critiques")
        if final_record.get("inspection_id") != latest_inspection_id:
            final_consistency_failures.append("final decision must bind the latest inspection")
        if final_record.get("score_id") != latest_score_id:
            final_consistency_failures.append("final decision must bind the latest score")
        if final_record.get("critique_id") != latest_critique_id:
            final_consistency_failures.append("final decision must bind the latest critique")
        declared_render_ids = final_record.get("render_ids")
        actual_render_ids = {
            item.get("id")
            for item in run.get("renders", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if isinstance(declared_render_ids, list):
            if set(declared_render_ids) != actual_render_ids:
                final_consistency_failures.append("final decision render_ids must include exactly every run render")
            if latest_render_id and latest_render_id not in declared_render_ids:
                final_consistency_failures.append("final decision must include the latest render")
        final_evidence = final_record.get("evidence")
        latest_render = next(
            (item for item in reversed(run.get("renders", [])) if isinstance(item, dict)),
            None,
        )
        if isinstance(final_evidence, list) and isinstance(latest_render, dict):
            latest_render_path = latest_render.get("path")
            if isinstance(latest_render_path, str) and latest_render_path not in final_evidence:
                final_consistency_failures.append("final decision evidence must include the latest render path")
        latest_score = _latest_score(run)
        latest_critique = next(
            (item for item in reversed(run.get("critiques", [])) if isinstance(item, dict)),
            None,
        )
        latest_score_time = _parse_timestamp(latest_score.get("scored_at")) if isinstance(latest_score, dict) else None
        latest_critique_time = _parse_timestamp(latest_critique.get("created_at")) if isinstance(latest_critique, dict) else None
        if final_time and latest_score_time and final_time < latest_score_time:
            final_consistency_failures.append("final decision timestamp cannot precede the latest score")
        if final_time and latest_critique_time and final_time < latest_critique_time:
            final_consistency_failures.append("final decision timestamp cannot precede the latest critique")
    latest_critic = run.get("critiques", [])[-1] if isinstance(run.get("critiques"), list) and run.get("critiques") else None
    if decision in {"PASS", "AAA CANDIDATE"} and isinstance(latest_critic, dict):
        reviewer_id = str(latest_critic.get("reviewer_id", "")).strip()
        if reviewer_id and approved_by != reviewer_id:
            final_consistency_failures.append("PASS approval must be signed by the latest independent critic")
    if decision == "CONDITIONAL PASS" and override_requested:
        owner = str(human_override.get("owner", "")).strip() if isinstance(human_override, dict) else ""
        if owner and approved_by != owner:
            final_consistency_failures.append("conditional approval must be signed by the human override owner")
    if final_consistency_failures:
        gate_failures.extend(final_consistency_failures)
        if decision in {"PASS", "AAA CANDIDATE", "CONDITIONAL PASS"}:
            decision = "BLOCKED"
            aaa_candidate = False
            aaa_blockers = [*aaa_blockers, *final_consistency_failures]
    if decision in {"PASS", "AAA CANDIDATE", "CONDITIONAL PASS"} and declared_final != decision:
        gate_failures.append(
            f"final decision declaration {declared_final or 'missing'} does not match computed {decision}"
        )
        decision = "BLOCKED"
        aaa_candidate = False
        aaa_blockers = [*aaa_blockers, "final decision declaration does not match computed decision"]
    regions = _region_scores(run, score_record)
    largest_gap = None
    if regions:
        largest_gap = min(
            regions,
            key=lambda item: (item["score"], item["region"], item.get("viewport") or -1, item.get("state") or ""),
        )
    return {
        "status": "scored",
        "benchmark_id": run.get("benchmark_id"),
        "run_id": run.get("run_id"),
        "decision": decision,
        "declared_final_decision": declared_final,
        "decision_matches_declaration": declared_final == decision,
        "overall": overall,
        "quality_band": quality_band,
        "applicable_dimensions": weighted["applicable_dimensions"],
        "dimension_scores": weighted["dimension_scores"],
        "weights": weighted["weights"],
        "declared_overall": weighted["declared_overall"],
        "declared_overall_matches": weighted["declared_overall_matches"],
        "evidence_confidence": evidence_confidence,
        "gates": gates,
        "blockers": blockers,
        "gate_failures": sorted(set(gate_failures)),
        "region_scores": regions,
        "largest_region_gap": largest_gap,
        "iteration_budget": run.get("iteration_budget"),
        "stop_reason": run.get("final_decision", {}).get("stop_reason") if isinstance(run.get("final_decision"), dict) else None,
        "human_override_applied": override_requested,
        "aaa_candidate": aaa_candidate,
        "aaa_blockers": sorted(set(aaa_blockers)),
        "limitations": [LIMITATION, *sorted(set(limitations))],
    }


def _load_contract(path: Path, kind: str, root: Path | None) -> tuple[Any | None, list[str]]:
    payload, errors = load_json(path)
    if errors:
        return None, errors
    validation_errors = validate(kind, payload, root)
    return (payload, validation_errors) if not validation_errors else (None, validation_errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    score_parser = subparsers.add_parser("score", help="score a validated benchmark run")
    score_parser.add_argument("run", type=Path)
    score_parser.add_argument("--benchmark", type=Path)
    score_parser.add_argument("--root", type=Path, help="repository root for evidence file checks (default: cwd)")
    score_parser.add_argument("--pretty", action="store_true")

    validate_parser = subparsers.add_parser("validate", help="validate a contract JSON")
    validate_parser.add_argument("path", type=Path)
    validate_parser.add_argument("--kind", choices=("benchmark", "run", "critic", "ledger"), default="benchmark")
    validate_parser.add_argument("--root", type=Path)
    validate_parser.add_argument("--pretty", action="store_true")

    args = parser.parse_args(argv)
    root = args.root.resolve() if args.root else Path.cwd().resolve()
    if args.command == "validate":
        payload, load_errors = load_json(args.path)
        errors = load_errors or validate(args.kind, payload, root)
        result = {"kind": args.kind, "path": str(args.path), "valid": not errors}
        if errors:
            result["errors"] = errors
        print(_dump(result, args.pretty))
        return 0 if not errors else 2

    run, run_errors = load_json(args.run)
    benchmark = None
    benchmark_errors: list[str] = []
    if args.benchmark:
        benchmark, benchmark_errors = _load_contract(args.benchmark, "benchmark", root)
    if run_errors or benchmark_errors or not isinstance(run, dict):
        errors = [*run_errors, *benchmark_errors]
        if not isinstance(run, dict) and not run_errors:
            errors.append("run: top-level JSON value must be an object")
        result = {
            "status": "invalid",
            "benchmark_id": run.get("benchmark_id") if isinstance(run, dict) else None,
            "run_id": run.get("run_id") if isinstance(run, dict) else None,
            "errors": sorted(set(errors)),
            "limitations": [LIMITATION],
        }
        print(_dump(result, args.pretty))
        return 2

    result = score_run(run, benchmark, root)
    print(_dump(result, args.pretty))
    if result.get("status") == "invalid":
        return 2
    return 0 if result.get("decision") in {"PASS", "AAA CANDIDATE"} else 1


if __name__ == "__main__":
    sys.exit(main())
