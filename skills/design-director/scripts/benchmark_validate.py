#!/usr/bin/env python3
"""Validate the machine-readable visual benchmark contracts.

The repository intentionally has no third-party JSON Schema dependency.  This
module implements the small JSON Schema 2020-12 subset used by the four local
schemas (types, required fields, properties, refs, enums, bounds, patterns,
and one/any-of), then applies semantic checks that JSON Schema cannot express:
unique IDs, repository-relative paths, pipeline references, viewport/state
links, and evidence requirements for approval.

Paths in benchmark, run, and evidence records are repository-relative.  Pass
``--root`` when filesystem existence should be checked; omitting it performs
contract-only validation, which is useful before an executor has produced
artifacts.  A run can be structurally valid and still be BLOCKED by the
scorer when renders, evidence, or an independent critic are absent.  This is
deliberate: the validator never infers pixel quality from source code.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import re
import sys
import zlib
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from compare_visual import PngError, decode_png


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_ROOT = REPOSITORY_ROOT / "benchmarks" / "schema"
SCHEMA_FILES = {
    "benchmark": SCHEMA_ROOT / "benchmark.schema.json",
    "run": SCHEMA_ROOT / "run.schema.json",
    "critic": SCHEMA_ROOT / "critic.schema.json",
    "ledger": SCHEMA_ROOT / "ledger.schema.json",
}

BENCHMARK_REQUIRED_FIELDS = (
    "id",
    "category",
    "brief",
    "inputs",
    "references",
    "constraints",
    "viewports",
    "states",
    "regions",
    "expected_artifacts",
    "preservation_rules",
    "quality_threshold",
    "iteration_budget",
)
LOCAL_PATH_FIELDS = ("path",)
URI_PREFIXES = ("http://", "https://", "file://", "data:")
SCREENSHOT_FORMATS = {"png"}
CRITICAL_SEVERITIES = {"critical", "high"}
KNOWN_CATEGORIES = {
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
KNOWN_PROVENANCE = {
    "source",
    "generated",
    "edited",
    "user-supplied",
    "repository-existing",
    "licensed",
    "unknown",
}
GOLDEN_BENCHMARK_IDS = {
    "B01-premium-banner",
    "B02-saas-landing",
    "B03-operational-dashboard",
    "B04-mobile-flow",
    "B05-screenshot-reconstruction",
    "B06-product-brand-identity",
    "B07-game-ui-asset-family",
}
KNOWN_STATES = {
    "default",
    "hover",
    "focus",
    "active",
    "disabled",
    "loading",
    "empty",
    "error",
    "success",
    "long-content",
    "short-content",
    "keyboard-open-mobile",
}
PASS_VERDICTS = {"PASS", "AAA CANDIDATE"}
APPROVAL_VERDICTS = PASS_VERDICTS | {"CONDITIONAL PASS"}


def _is_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if isinstance(value, float):
        return math.isfinite(value)
    return True


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _type_matches(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return _is_number(value)
    if expected == "integer":
        return _is_integer(value)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def _pointer_get(document: dict[str, Any], pointer: str) -> Any:
    value: Any = document
    for component in pointer.removeprefix("#/").split("/"):
        component = component.replace("~1", "/").replace("~0", "~")
        value = value[component]
    return value


def _schema_validate(
    value: Any,
    schema: dict[str, Any],
    location: str,
    root_schema: dict[str, Any],
) -> list[str]:
    """Return deterministic errors for the schema subset used in this repo."""

    if "$ref" in schema:
        return _schema_validate(
            value,
            _pointer_get(root_schema, schema["$ref"]),
            location,
            root_schema,
        )

    errors: list[str] = []
    if "const" in schema and value != schema["const"]:
        errors.append(f"{location}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{location}: must be one of {schema['enum']!r}")

    if "oneOf" in schema:
        valid_branches = sum(
            not _schema_validate(value, branch, location, root_schema)
            for branch in schema["oneOf"]
        )
        if valid_branches != 1:
            errors.append(f"{location}: must match exactly one schema alternative")
    if "anyOf" in schema:
        if not any(not _schema_validate(value, branch, location, root_schema) for branch in schema["anyOf"]):
            errors.append(f"{location}: must match at least one schema alternative")

    expected_type = schema.get("type")
    if expected_type is not None:
        expected_types = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_type_matches(value, type_name) for type_name in expected_types):
            return errors + [f"{location}: expected type {expected_type!r}"]

    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                errors.append(f"{location}: missing required field {required!r}")
        properties = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, item in value.items():
            child_location = f"{location}.{key}" if location else key
            if key in properties:
                errors.extend(_schema_validate(item, properties[key], child_location, root_schema))
            elif additional is False:
                errors.append(f"{child_location}: unexpected field")
            elif isinstance(additional, dict):
                errors.extend(_schema_validate(item, additional, child_location, root_schema))
        min_properties = schema.get("minProperties")
        if min_properties is not None and len(value) < min_properties:
            errors.append(f"{location}: must contain at least {min_properties} properties")

    if isinstance(value, list):
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            errors.append(f"{location}: must contain at least {min_items} items")
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            errors.append(f"{location}: items must be unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                errors.extend(_schema_validate(item, item_schema, f"{location}[{index}]", root_schema))

    if isinstance(value, str):
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            errors.append(f"{location}: must contain at least {min_length} characters")
        pattern = schema.get("pattern")
        if pattern and re.search(pattern, value) is None:
            errors.append(f"{location}: does not match required pattern {pattern!r}")

    if _is_number(value):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{location}: must be >= {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{location}: must be <= {schema['maximum']}")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            errors.append(f"{location}: must be > {schema['exclusiveMinimum']}")
        if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
            errors.append(f"{location}: must be < {schema['exclusiveMaximum']}")
    return errors


def _load_schema(kind: str) -> tuple[dict[str, Any] | None, list[str]]:
    path = SCHEMA_FILES[kind]
    try:
        schema = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        return None, [f"schema {path} cannot be read: {error}"]
    except json.JSONDecodeError as error:
        return None, [f"schema {path} is invalid JSON: {error}"]
    if not isinstance(schema, dict):
        return None, [f"schema {path} must be a JSON object"]
    return schema, []


def load_json(path: Path) -> tuple[Any | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except OSError as error:
        return None, [f"{path}: cannot be read: {error}"]
    except json.JSONDecodeError as error:
        return None, [f"{path}: invalid JSON: {error}"]


def _relative_path_error(raw_path: Any, location: str) -> str | None:
    if not isinstance(raw_path, str) or not raw_path:
        return f"{location}: path must be a non-empty string"
    normalized = raw_path.replace("\\", "/")
    if normalized.startswith(("/", "~")) or re.match(r"^[A-Za-z]:[\\/]", raw_path):
        return f"{location}: path must be repository-relative"
    if normalized.startswith(URI_PREFIXES):
        return None
    parts = PurePosixPath(normalized).parts
    if ".." in parts:
        return f"{location}: path must not escape the repository root"
    return None


def _check_path(
    raw_path: Any,
    location: str,
    root: Path | None,
    *,
    require_file: bool = True,
) -> list[str]:
    error = _relative_path_error(raw_path, location)
    if error:
        return [error]
    if root is None or not isinstance(raw_path, str) or raw_path.startswith(URI_PREFIXES):
        return []
    root = root.resolve()
    candidate = (root / Path(raw_path)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return [f"{location}: path resolves outside the repository root"]
    if require_file and not candidate.is_file():
        return [f"{location}: file does not exist at {raw_path!r}"]
    return []


def _check_evidence(
    evidence: Iterable[Any],
    location: str,
    root: Path | None,
    *,
    allow_empty: bool = True,
) -> list[str]:
    evidence_list = list(evidence) if isinstance(evidence, list) else []
    if not allow_empty and not evidence_list:
        return [f"{location}: evidence is required"]
    errors: list[str] = []
    for index, item in enumerate(evidence_list):
        if not isinstance(item, str):
            errors.append(f"{location}[{index}]: evidence must be a path or URI string")
            continue
        if item.startswith(URI_PREFIXES):
            continue
        errors.extend(_check_path(item, f"{location}[{index}]", root))
    return errors


def _file_sha256(raw_path: Any, root: Path | None) -> str | None:
    if root is None or not isinstance(raw_path, str) or raw_path.startswith(URI_PREFIXES):
        return None
    candidate = (root.resolve() / Path(raw_path)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    try:
        return hashlib.sha256(candidate.read_bytes()).hexdigest()
    except OSError:
        return None


def _visual_evidence_errors(
    evidence: Any,
    location: str,
    root: Path | None,
    *,
    required_render_path: str | None = None,
) -> list[str]:
    """Require region evidence to name an inspectable raster, not source HTML."""

    if not isinstance(evidence, list):
        return [f"{location}: evidence must be a list of visual paths"]
    errors: list[str] = []
    visual_found = False
    render_path_found = required_render_path is None
    for index, item in enumerate(evidence):
        if not isinstance(item, str) or not item.strip():
            continue
        if item.startswith(URI_PREFIXES):
            continue
        if required_render_path is not None and item == required_render_path:
            render_path_found = True
        extension = Path(item).suffix.lower().lstrip(".")
        if extension not in SCREENSHOT_FORMATS:
            continue
        if root is None:
            visual_found = True
            continue
        candidate = (root / Path(item)).resolve()
        path_errors = _check_path(item, f"{location}[{index}]", root)
        if path_errors:
            errors.extend(path_errors)
            continue
        try:
            decoded_width, decoded_height, _pixels = decode_png(candidate)
        except (OSError, PngError, ValueError, zlib.error) as error:
            errors.append(f"{location}[{index}]: raster evidence is not locally decodable: {error}")
            continue
        if decoded_width < 1 or decoded_height < 1:
            errors.append(f"{location}[{index}]: raster evidence has invalid dimensions")
            continue
        visual_found = True
    if not visual_found:
        errors.append(f"{location}: at least one locally inspectable raster evidence path is required")
    if not render_path_found:
        errors.append(f"{location}: evidence must include the current render path {required_render_path!r}")
    return errors


def _render_identity(
    render: dict[str, Any],
    root: Path | None,
    location: str,
) -> tuple[str | None, list[str]]:
    """Return a render content identity and verify any declared digest."""

    declared = render.get("sha256")
    actual = _file_sha256(render.get("path"), root)
    errors: list[str] = []
    if isinstance(declared, str) and actual is not None and declared.lower() != actual:
        errors.append(f"{location}.sha256: does not match the render file")
    return actual or (declared.lower() if isinstance(declared, str) else None), errors


def _unique_errors(values: Iterable[Any], location: str) -> list[str]:
    seen: set[str] = set()
    errors: list[str] = []
    for index, value in enumerate(values):
        key = json.dumps(value, sort_keys=True, ensure_ascii=False)
        if key in seen:
            errors.append(f"{location}[{index}]: duplicate identifier/value {value!r}")
        seen.add(key)
    return errors


def _viewport_width(viewport: Any) -> int | None:
    if _is_integer(viewport):
        return viewport
    if isinstance(viewport, dict) and _is_integer(viewport.get("width")):
        return viewport["width"]
    return None


def _viewport_height(viewport: Any) -> int | None:
    if isinstance(viewport, dict) and _is_integer(viewport.get("height")):
        return viewport["height"]
    return None


def _viewport_dpr(viewport: Any) -> float:
    if isinstance(viewport, dict) and _is_number(viewport.get("dpr")):
        return float(viewport["dpr"])
    return 1.0


def _viewport_selectors(viewport: Any) -> set[str | int]:
    selectors: set[str | int] = set()
    width = _viewport_width(viewport)
    if width is not None:
        selectors.add(width)
    if isinstance(viewport, dict):
        for key in ("id", "name", "label"):
            value = viewport.get(key)
            if isinstance(value, str) and value:
                selectors.add(value)
    return selectors


def _selector_matches_viewport(selector: Any, viewport: Any) -> bool:
    if isinstance(selector, dict):
        selector_values = _viewport_selectors(selector)
    elif isinstance(selector, (str, int)) and not isinstance(selector, bool):
        selector_values = {selector}
    else:
        return False
    return bool(selector_values & _viewport_selectors(viewport))


def _viewport_label(viewport: Any) -> str:
    if isinstance(viewport, dict):
        for key in ("id", "name", "label"):
            if isinstance(viewport.get(key), str) and viewport[key]:
                return viewport[key]
    width = _viewport_width(viewport)
    return f"{width}px" if width is not None else str(viewport)


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _state_id(state: Any) -> str | None:
    if isinstance(state, str):
        return state
    if isinstance(state, dict) and isinstance(state.get("id"), str):
        return state["id"]
    return None


def _required_viewports(benchmark: dict[str, Any] | None) -> list[Any]:
    if not benchmark or not isinstance(benchmark.get("viewports"), list):
        return []
    return [
        viewport
        for viewport in benchmark["viewports"]
        if not isinstance(viewport, dict) or viewport.get("required", True) is not False
    ]


def _required_states(benchmark: dict[str, Any] | None) -> list[Any]:
    if not benchmark or not isinstance(benchmark.get("states"), list):
        return []
    return [
        state
        for state in benchmark["states"]
        if not isinstance(state, dict) or state.get("required", True) is not False
    ]


def _state_applies_to_viewport(state: Any, viewport: Any) -> bool:
    if not isinstance(state, dict) or not isinstance(state.get("viewports"), list):
        return True
    return any(_selector_matches_viewport(selector, viewport) for selector in state["viewports"])


def _region_id(region: Any) -> str | None:
    if isinstance(region, str):
        return region
    if isinstance(region, dict) and isinstance(region.get("id"), str):
        return region["id"]
    return None


def _region_required(region: Any) -> bool:
    return not isinstance(region, dict) or region.get("required", True) is not False


def _region_applies_to(region: Any, viewport: Any, state: Any) -> bool:
    if not _region_required(region):
        return False
    if not isinstance(region, dict):
        return True
    if isinstance(region.get("viewports"), list) and not any(
        _selector_matches_viewport(selector, viewport) for selector in region["viewports"]
    ):
        return False
    state_id = _state_id(state)
    if isinstance(region.get("states"), list) and state_id not in region["states"]:
        return False
    return True


def _benchmark_region_ids(benchmark: dict[str, Any] | None) -> set[str]:
    if not benchmark or not isinstance(benchmark.get("regions"), list):
        return set()
    return {
        region_id
        for region in benchmark["regions"]
        if _region_required(region) and (region_id := _region_id(region)) is not None
    }


def _benchmark_observation_matrix(
    benchmark: dict[str, Any] | None,
) -> list[tuple[int, str, Any, Any]]:
    """Return required (viewport width, state id, viewport, state) tuples."""

    observations: list[tuple[int, str, Any, Any]] = []
    for viewport in _required_viewports(benchmark):
        width = _viewport_width(viewport)
        if width is None:
            continue
        for state in _required_states(benchmark):
            state_id = _state_id(state)
            if state_id and _state_applies_to_viewport(state, viewport):
                observations.append((width, state_id, viewport, state))
    return observations


def _iteration_budget_limit(benchmark: dict[str, Any] | None) -> int | None:
    if not benchmark:
        return None
    budget = benchmark.get("iteration_budget")
    if _is_integer(budget):
        return budget
    if isinstance(budget, dict):
        value = budget.get("max_cycles", budget.get("max_iterations"))
        return value if _is_integer(value) else None
    return None


def _independent_critic_is_qualified(critic: dict[str, Any]) -> bool:
    packet = critic.get("blind_packet")
    provenance = critic.get("reviewer_provenance")
    return bool(
        critic.get("independent")
        and critic.get("blinded")
        and critic.get("independence") == "INDEPENDENT"
        and isinstance(packet, dict)
        and packet.get("builder_rationale_withheld") is True
        and packet.get("self_score_withheld") is True
        and isinstance(provenance, dict)
        and provenance.get("rationale_received") is False
        and provenance.get("self_score_received") is False
        and isinstance(provenance.get("process"), str)
        and bool(provenance.get("process").strip())
        and isinstance(provenance.get("builder_id"), str)
        and bool(provenance.get("builder_id").strip())
        and provenance.get("builder_id") != critic.get("reviewer_id")
        and isinstance(provenance.get("packet_digest"), str)
        and provenance.get("packet_digest") == hashlib.sha256(
            json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        and {
            "request",
            "constraints",
            "references",
            "artifact",
            "acceptance_criteria",
        }.issubset(set(provenance.get("context_shared", [])))
    )


def _latest_record_id(payload: dict[str, Any], collection_name: str) -> str | None:
    """Return the last valid record id; run arrays are append-ordered evidence."""

    collection = payload.get(collection_name, [])
    if not isinstance(collection, list):
        return None
    for item in reversed(collection):
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            return item["id"]
    return None


def _critic_artifact_binding_errors(
    critique: dict[str, Any],
    artifacts: dict[str, dict[str, Any]],
    renders: dict[str, dict[str, Any]],
    location: str,
) -> list[str]:
    """Ensure a passing blind packet names this run's artifact surface."""

    packet = critique.get("blind_packet")
    if not isinstance(packet, dict) or not isinstance(packet.get("artifact"), list):
        return []
    bound = {
        value
        for record in [*artifacts.values(), *renders.values()]
        for value in (record.get("id"), record.get("path"))
        if isinstance(value, str)
    }
    if not any(isinstance(value, str) and value in bound for value in packet["artifact"]):
        return [
            f"{location}.blind_packet.artifact: PASS critique must name at least one artifact or render from this run"
        ]
    return []


def _base_errors(payload: Any, kind: str) -> list[str]:
    schema, errors = _load_schema(kind)
    if schema is None:
        return errors
    return errors + _schema_validate(payload, schema, "$", schema)


def _validate_benchmark_semantics(payload: dict[str, Any], root: Path | None) -> list[str]:
    errors: list[str] = []
    if payload.get("category") not in KNOWN_CATEGORIES:
        errors.append("$.category: unsupported benchmark category")
    for field in BENCHMARK_REQUIRED_FIELDS:
        if field not in payload:
            errors.append(f"$: missing operational benchmark field {field!r}")

    inputs = payload.get("inputs", [])
    if isinstance(inputs, list):
        errors.extend(_unique_errors([item.get("id") for item in inputs if isinstance(item, dict) and item.get("id") is not None], "$.inputs"))
        for index, item in enumerate(inputs):
            if not isinstance(item, dict):
                continue
            if "path" in item:
                errors.extend(_check_path(item["path"], f"$.inputs[{index}].path", root))
            source = item.get("source")
            if isinstance(source, dict) and "path" in source:
                errors.extend(_check_path(source["path"], f"$.inputs[{index}].source.path", root))

    references = payload.get("references", [])
    if isinstance(references, list):
        errors.extend(_unique_errors([item.get("id") for item in references if isinstance(item, dict)], "$.references"))
        for index, item in enumerate(references):
            if isinstance(item, dict) and "path" in item:
                errors.extend(_check_path(item["path"], f"$.references[{index}].path", root))
            if isinstance(item, dict) and item.get("provenance") not in KNOWN_PROVENANCE:
                errors.append(f"$.references[{index}].provenance: unsupported provenance")

    viewports = payload.get("viewports", [])
    if isinstance(viewports, list):
        widths = [_viewport_width(item) for item in viewports]
        if None in widths:
            errors.append("$.viewports: every viewport must expose an integer width")
        else:
            errors.extend(_unique_errors(widths, "$.viewports"))

    states = payload.get("states", [])
    if isinstance(states, list):
        state_ids = [_state_id(item) for item in states]
        if None in state_ids:
            errors.append("$.states: every state must expose a string id")
        else:
            errors.extend(_unique_errors(state_ids, "$.states"))
            # The common states above are useful vocabulary, but a benchmark
            # must be able to name domain-specific states (for example
            # ``keyboard-open`` or ``selected-route``).  The schema enforces
            # the slug shape; do not reject valid extensions here.

    regions = payload.get("regions", [])
    region_ids: set[str] = set()
    if isinstance(regions, list):
        region_values = [
            _region_id(region)
            for region in regions
            if _region_id(region) is not None
        ]
        region_ids = set(region_values)
        errors.extend(_unique_errors(region_values, "$.regions"))
        known_state_ids = {
            state_id for state in states if (state_id := _state_id(state)) is not None
        }
        known_viewports = [
            viewport for viewport in viewports if _viewport_width(viewport) is not None
        ]
        for index, region in enumerate(regions):
            if not isinstance(region, dict):
                continue
            for state_id in region.get("states", []):
                if state_id not in known_state_ids:
                    errors.append(f"$.regions[{index}].states: unknown state {state_id!r}")
            for selector in region.get("viewports", []):
                if not any(_selector_matches_viewport(selector, viewport) for viewport in known_viewports):
                    errors.append(
                        f"$.regions[{index}].viewports: unknown viewport selector {selector!r}"
                    )

    known_viewports = [
        viewport for viewport in viewports if _viewport_width(viewport) is not None
    ]
    for index, state in enumerate(states):
        if not isinstance(state, dict):
            continue
        for selector in state.get("viewports", []):
            if not any(_selector_matches_viewport(selector, viewport) for viewport in known_viewports):
                errors.append(
                    f"$.states[{index}].viewports: unknown viewport selector {selector!r}"
                )

    artifacts = payload.get("expected_artifacts", [])
    if isinstance(artifacts, list):
        errors.extend(_unique_errors([item.get("id") for item in artifacts if isinstance(item, dict)], "$.expected_artifacts"))
        for index, artifact in enumerate(artifacts):
            if not isinstance(artifact, dict):
                continue
            for region_id in artifact.get("regions", []):
                if region_ids and region_id not in region_ids:
                    errors.append(
                        f"$.expected_artifacts[{index}].regions: unknown region {region_id!r}"
                    )

    budget = payload.get("iteration_budget")
    if _is_integer(budget):
        if not 1 <= budget <= 4:
            errors.append("$.iteration_budget: must be an integer between 1 and 4")
    elif isinstance(budget, dict):
        cycles = budget.get("max_cycles", budget.get("max_iterations"))
        if not _is_integer(cycles) or not 1 <= cycles <= 4:
            errors.append("$.iteration_budget: max_cycles/max_iterations must be an integer between 1 and 4")
    else:
        errors.append("$.iteration_budget: must be an integer or an object with a bounded cycle count")

    threshold = payload.get("quality_threshold")
    if isinstance(threshold, dict):
        minimum = threshold.get("overall_min")
        if _is_number(minimum) and minimum < 70:
            errors.append("$.quality_threshold.overall_min: must be at least 70 for a quality gate")
        confidence = threshold.get("evidence_confidence_min")
        if confidence not in {"LOW", "MEDIUM", "HIGH"}:
            errors.append("$.quality_threshold.evidence_confidence_min: invalid confidence")
    return errors


def validate_benchmark(payload: Any, root: Path | None = None) -> list[str]:
    errors = _base_errors(payload, "benchmark")
    if isinstance(payload, dict):
        errors.extend(_validate_benchmark_semantics(payload, root))
    return sorted(set(errors))


def _finding_group_errors(findings: Any, location: str) -> list[str]:
    if not isinstance(findings, dict):
        return []
    errors: list[str] = []
    for severity in ("critical", "high", "medium", "low", "polish"):
        group = findings.get(severity, [])
        if not isinstance(group, list):
            continue
        for index, finding in enumerate(group):
            if isinstance(finding, dict) and finding.get("severity") != severity:
                errors.append(
                    f"{location}.{severity}[{index}].severity: must match its finding group"
                )
    return errors


def _finding_evidence_errors(
    findings: Any,
    location: str,
    root: Path | None,
) -> list[str]:
    """Require every material finding to be locatable and evidence-backed."""

    if not isinstance(findings, dict):
        return []
    errors: list[str] = []
    for severity in ("critical", "high", "medium", "low", "polish"):
        group = findings.get(severity, [])
        if not isinstance(group, list):
            continue
        for index, finding in enumerate(group):
            if not isinstance(finding, dict):
                continue
            finding_location = f"{location}.{severity}[{index}]"
            status = finding.get("status")
            evidence = finding.get("evidence", [])
            errors.extend(
                _check_evidence(
                    evidence,
                    f"{finding_location}.evidence",
                    root,
                    allow_empty=status in {"not-run", "blocked"},
                )
            )
            if status in {"fixed", "accepted"} and not evidence:
                errors.append(f"{finding_location}.evidence: fixed/accepted findings require evidence")
            if status not in {"not-run", "blocked"} and not evidence:
                errors.append(f"{finding_location}.evidence: material findings require evidence")
    return errors


def _validate_ledger_entries(
    entries: Any,
    root: Path | None,
    location: str,
    schema: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(entries, list):
        return errors
    entry_schema = schema.get("$defs", {}).get("entry") or schema.get("$defs", {}).get("ledger-entry")
    if isinstance(entry_schema, dict):
        for index, entry in enumerate(entries):
            errors.extend(_schema_validate(entry, entry_schema, f"{location}[{index}]", schema))
    errors.extend(_unique_errors([item.get("id") for item in entries if isinstance(item, dict)], location))
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        entry_location = f"{location}[{index}]"
        status = entry.get("status")
        evidence = entry.get("evidence", [])
        errors.extend(
            _check_evidence(
                evidence,
                f"{entry_location}.evidence",
                root,
                allow_empty=status in {"not-run", "blocked"},
            )
        )
        if status in {"fixed", "accepted"} and not evidence:
            errors.append(f"{entry_location}.evidence: fixed/accepted entries require evidence")
        viewport = entry.get("viewport")
        if _viewport_width(viewport) is None:
            errors.append(f"{entry_location}.viewport: width is required")
    return errors


def _run_schema() -> tuple[dict[str, Any] | None, list[str]]:
    return _load_schema("run")


def _benchmark_viewport_for_width(benchmark: dict[str, Any] | None, width: Any) -> Any | None:
    for viewport in _required_viewports(benchmark):
        if _viewport_width(viewport) == width:
            return viewport
    return None


def _benchmark_state_ids(benchmark: dict[str, Any] | None) -> set[str]:
    return {
        state_id
        for state in (benchmark.get("states", []) if benchmark else [])
        if (state_id := _state_id(state)) is not None
    }


def _validate_region_observations(
    observations: Any,
    benchmark: dict[str, Any] | None,
    location: str,
    root: Path | None,
    renders: dict[str, dict[str, Any]] | None = None,
) -> list[str]:
    errors: list[str] = []
    if not isinstance(observations, list) or benchmark is None:
        return errors
    known_regions = _benchmark_region_ids(benchmark)
    seen: set[tuple[str, int, str]] = set()
    for index, observation in enumerate(observations):
        if not isinstance(observation, dict):
            continue
        region_id = observation.get("region")
        if known_regions and region_id not in known_regions:
            errors.append(f"{location}[{index}].region: unknown benchmark region {region_id!r}")
        render_id = observation.get("render_id")
        viewport = observation.get("viewport")
        width = _viewport_width(viewport)
        state_id = observation.get("state")
        if not isinstance(render_id, str) or not render_id:
            errors.append(f"{location}[{index}].render_id: region observations require a render id")
        elif renders is not None:
            render = renders.get(render_id)
            if render is None:
                errors.append(f"{location}[{index}].render_id: unknown render {render_id!r}")
            else:
                if width is not None and _viewport_width(render.get("viewport")) != width:
                    errors.append(f"{location}[{index}].viewport: does not match render {render_id!r}")
                if (
                    _viewport_height(viewport) is not None
                    and _viewport_height(render.get("viewport")) != _viewport_height(viewport)
                ):
                    errors.append(f"{location}[{index}].viewport: height does not match render {render_id!r}")
                if (
                    isinstance(viewport, dict)
                    and "dpr" in viewport
                    and _viewport_dpr(viewport) != _viewport_dpr(render.get("viewport"))
                ):
                    errors.append(f"{location}[{index}].viewport: dpr does not match render {render_id!r}")
                if isinstance(state_id, str) and render.get("state") != state_id:
                    errors.append(f"{location}[{index}].state: does not match render {render_id!r}")
        if width is None or _viewport_height(viewport) is None:
            errors.append(f"{location}[{index}].viewport: region observations require width and height")
        if not isinstance(state_id, str) or not state_id:
            errors.append(f"{location}[{index}].state: region observations require a state id")
        if isinstance(region_id, str) and width is not None and isinstance(state_id, str):
            key = (region_id, width, state_id)
            if key in seen:
                errors.append(f"{location}[{index}]: duplicate region/viewport/state observation {key!r}")
            seen.add(key)
        errors.extend(
            _check_evidence(
                observation.get("evidence", []),
                f"{location}[{index}].evidence",
                root,
                allow_empty=False,
            )
        )
        errors.extend(
            _visual_evidence_errors(
                observation.get("evidence", []),
                f"{location}[{index}].evidence",
                root,
                required_render_path=(
                    renders.get(render_id, {}).get("path")
                    if renders is not None and isinstance(renders.get(render_id), dict)
                    else None
                ),
            )
        )
    return errors


def _validate_run_semantics(
    payload: dict[str, Any],
    root: Path | None,
    benchmark: dict[str, Any] | None,
    *,
    enforce_final: bool,
) -> list[str]:
    errors: list[str] = []
    schema, schema_errors = _run_schema()
    if schema is None:
        return schema_errors

    if benchmark is not None and payload.get("benchmark_id") != benchmark.get("id"):
        errors.append("$.benchmark_id: does not match the supplied benchmark")

    for collection_name in ("artifacts", "renders", "inspections", "scores", "critiques", "iterations"):
        collection = payload.get(collection_name, [])
        if isinstance(collection, list):
            errors.extend(
                _unique_errors(
                    [item.get("id") for item in collection if isinstance(item, dict)],
                    f"$.{collection_name}",
                )
            )

    artifacts = {
        item.get("id"): item
        for item in payload.get("artifacts", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }

    expected_artifacts = {
        item.get("id"): item
        for item in (benchmark.get("expected_artifacts", []) if benchmark else [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    expected_render_ids = {
        artifact_id
        for artifact_id, expected in expected_artifacts.items()
        if expected.get("kind") in {"render", "screenshot"}
    }
    renders = {
        item.get("id"): item
        for item in payload.get("renders", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    inspections = {
        item.get("id"): item
        for item in payload.get("inspections", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    latest_render_id = _latest_record_id(payload, "renders")
    latest_inspection_id = _latest_record_id(payload, "inspections")

    execution = payload.get("execution")
    execution_start = _parse_timestamp(execution.get("started_at")) if isinstance(execution, dict) else None
    execution_end = _parse_timestamp(execution.get("completed_at")) if isinstance(execution, dict) else None
    if isinstance(execution, dict):
        for field in ("started_at", "completed_at"):
            if _parse_timestamp(execution.get(field)) is None:
                errors.append(f"$.execution.{field}: must be an ISO-8601 timestamp with timezone")
        if execution_start and execution_end and execution_end < execution_start:
            errors.append("$.execution.completed_at: must not precede started_at")
        errors.extend(_check_evidence(execution.get("evidence", []), "$.execution.evidence", root))
        declared_artifacts = execution.get("artifact_ids", [])
        if isinstance(declared_artifacts, list):
            unknown_execution_artifacts = sorted(
                str(artifact_id) for artifact_id in declared_artifacts if artifact_id not in artifacts
            )
            if unknown_execution_artifacts:
                errors.append(
                    "$.execution.artifact_ids: unknown artifact(s): "
                    + ", ".join(unknown_execution_artifacts)
                )

    for index, artifact in enumerate(payload.get("artifacts", [])):
        if isinstance(artifact, dict):
            status = artifact.get("status")
            errors.extend(
                _check_path(
                    artifact.get("path"),
                    f"$.artifacts[{index}].path",
                    root,
                    require_file=status not in {"missing", "blocked"},
                )
            )
            expected = expected_artifacts.get(artifact.get("id"))
            if isinstance(expected, dict) and artifact.get("kind") != expected.get("kind"):
                errors.append(
                    f"$.artifacts[{index}].kind: {artifact.get('kind')!r} does not match benchmark expectation {expected.get('kind')!r}"
                )
            if (
                isinstance(expected, dict)
                and isinstance(expected.get("path"), str)
                and artifact.get("path") != expected.get("path")
            ):
                errors.append(
                    f"$.artifacts[{index}].path: does not match benchmark path {expected.get('path')!r}"
                )
            if status == "produced":
                declared_hash = artifact.get("sha256")
                if not isinstance(declared_hash, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", declared_hash):
                    errors.append(
                        f"$.artifacts[{index}].sha256: produced artifacts require a SHA-256 digest"
                    )
                else:
                    actual_hash = _file_sha256(artifact.get("path"), root)
                    if actual_hash is not None and declared_hash.lower() != actual_hash:
                        errors.append(
                            f"$.artifacts[{index}].sha256: does not match the artifact file"
                        )

    for index, render in enumerate(payload.get("renders", [])):
        if not isinstance(render, dict):
            continue
        render_location = f"$.renders[{index}]"
        artifact_id = render.get("artifact_id")
        if artifact_id not in artifacts:
            errors.append(f"{render_location}.artifact_id: unknown artifact {artifact_id!r}")
        elif expected_render_ids and artifact_id not in expected_render_ids:
            errors.append(
                f"{render_location}.artifact_id: render must bind to an expected render artifact"
            )
        errors.extend(_check_path(render.get("path"), f"{render_location}.path", root))
        errors.extend(
            _check_evidence(
                render.get("evidence", []),
                f"{render_location}.evidence",
                root,
            )
        )
        _render_digest, digest_errors = _render_identity(render, root, render_location)
        errors.extend(digest_errors)
        if _parse_timestamp(render.get("captured_at")) is None:
            errors.append(f"{render_location}.captured_at: must be an ISO-8601 timestamp with timezone")
        if (
            isinstance(execution, dict)
            and execution.get("status") == "complete"
            and isinstance(execution.get("evidence"), list)
            and render.get("path") not in execution.get("evidence", [])
        ):
            errors.append(
                f"{render_location}.path: complete execution evidence must include the current render path"
            )
        if benchmark is not None:
            width = _viewport_width(render.get("viewport"))
            expected_viewport = _benchmark_viewport_for_width(benchmark, width)
            if expected_viewport is None:
                errors.append(f"{render_location}.viewport: width {width!r} is not declared by the benchmark")
            elif (
                _viewport_height(render.get("viewport")) is not None
                and _viewport_height(expected_viewport) is not None
                and _viewport_height(render.get("viewport")) != _viewport_height(expected_viewport)
            ):
                errors.append(
                    f"{render_location}.viewport.height: does not match benchmark height {_viewport_height(expected_viewport)}"
                )
            if (
                expected_viewport is not None
                and isinstance(render.get("viewport"), dict)
                and "dpr" in render["viewport"]
                and _viewport_dpr(render["viewport"]) != _viewport_dpr(expected_viewport)
            ):
                errors.append(
                    f"{render_location}.viewport.dpr: does not match benchmark dpr {_viewport_dpr(expected_viewport):g}"
                )
            if render.get("state") not in _benchmark_state_ids(benchmark):
                errors.append(f"{render_location}.state: is not declared by the benchmark")

    for index, inspection in enumerate(payload.get("inspections", [])):
        if not isinstance(inspection, dict):
            continue
        location = f"$.inspections[{index}]"
        inspection_render = renders.get(inspection.get("render_id"))
        if inspection_render is None:
            errors.append(f"{location}.render_id: unknown render {inspection.get('render_id')!r}")
        errors.extend(_check_evidence(inspection.get("evidence", []), f"{location}.evidence", root))
        errors.extend(
            _visual_evidence_errors(
                inspection.get("evidence", []),
                f"{location}.evidence",
                root,
                required_render_path=(
                    inspection_render.get("path")
                    if isinstance(inspection_render, dict) and isinstance(inspection_render.get("path"), str)
                    else None
                ),
            )
        )
        inspection_time = _parse_timestamp(inspection.get("inspected_at"))
        if inspection_time is None:
            errors.append(f"{location}.inspected_at: must be an ISO-8601 timestamp with timezone")
        render_time = _parse_timestamp(inspection_render.get("captured_at")) if isinstance(inspection_render, dict) else None
        if render_time and inspection_time and inspection_time < render_time:
            errors.append(f"{location}.inspected_at: cannot precede its render capture")
        if execution_start and inspection_time and inspection_time < execution_start:
            errors.append(f"{location}.inspected_at: cannot precede execution start")
        if execution_end and inspection_time and inspection_time > execution_end:
            errors.append(f"{location}.inspected_at: cannot follow execution completion")
        findings = inspection.get("findings", [])
        if isinstance(findings, list):
            for finding_index, finding in enumerate(findings):
                if not isinstance(finding, dict):
                    continue
                finding_location = f"{location}.findings[{finding_index}]"
                status = finding.get("status")
                evidence = finding.get("evidence", [])
                errors.extend(
                    _check_evidence(
                        evidence,
                        f"{finding_location}.evidence",
                        root,
                        allow_empty=status in {"not-run", "blocked"},
                    )
                )
                if status in {"fixed", "accepted"} and not evidence:
                    errors.append(f"{finding_location}.evidence: fixed/accepted findings require evidence")
                if status not in {"not-run", "blocked"} and not evidence:
                    errors.append(f"{finding_location}.evidence: material findings require evidence")

    score_times_by_inspection: dict[str, list[datetime]] = {}
    for index, score in enumerate(payload.get("scores", [])):
        if not isinstance(score, dict):
            continue
        location = f"$.scores[{index}]"
        if score.get("inspection_id") not in inspections:
            errors.append(f"{location}.inspection_id: unknown inspection {score.get('inspection_id')!r}")
        elif inspections[score.get("inspection_id")].get("status") != "pass":
            errors.append(f"{location}.inspection_id: score must link to a passing inspection")
        dimensions = score.get("dimensions", {})
        applicable = score.get("applicable_dimensions", list(dimensions) if isinstance(dimensions, dict) else [])
        if isinstance(dimensions, dict) and isinstance(applicable, list):
            missing = sorted(set(applicable) - set(dimensions))
            if missing:
                errors.append(f"{location}: applicable dimensions missing scores: {', '.join(missing)}")
            weights = score.get("weights", {})
            if isinstance(weights, dict):
                for dimension in applicable:
                    if dimension in weights and (not _is_number(weights[dimension]) or weights[dimension] <= 0):
                        errors.append(f"{location}.weights.{dimension}: must be > 0")
        errors.extend(
            _validate_region_observations(
                score.get("regions"),
                benchmark,
                f"{location}.regions",
                root,
                renders,
            )
        )
        score_time = _parse_timestamp(score.get("scored_at"))
        if score_time is None:
            errors.append(f"{location}.scored_at: must be an ISO-8601 timestamp with timezone")
        score_inspection = inspections.get(score.get("inspection_id"))
        inspection_time = _parse_timestamp(score_inspection.get("inspected_at")) if isinstance(score_inspection, dict) else None
        if inspection_time and score_time and score_time < inspection_time:
            errors.append(f"{location}.scored_at: cannot precede its inspection")
        if execution_start and score_time and score_time < execution_start:
            errors.append(f"{location}.scored_at: cannot precede execution start")
        if execution_end and score_time and score_time > execution_end:
            errors.append(f"{location}.scored_at: cannot follow execution completion")
        if score_time and isinstance(score.get("inspection_id"), str):
            score_times_by_inspection.setdefault(score["inspection_id"], []).append(score_time)

    for index, critique in enumerate(payload.get("critiques", [])):
        if not isinstance(critique, dict):
            continue
        location = f"$.critiques[{index}]"
        if critique.get("inspection_id") not in inspections:
            errors.append(f"{location}.inspection_id: unknown inspection {critique.get('inspection_id')!r}")
        elif critique.get("verdict") in PASS_VERDICTS and inspections[critique.get("inspection_id")].get("status") != "pass":
            errors.append(f"{location}.inspection_id: approval critique must link to a passing inspection")
        errors.extend(_finding_group_errors(critique.get("findings"), f"{location}.findings"))
        errors.extend(_finding_evidence_errors(critique.get("findings"), f"{location}.findings", root))
        errors.extend(_finding_evidence_errors({"critical": critique.get("constraint_violations", [])}, f"{location}.constraint_violations", root))
        errors.extend(
            _validate_region_observations(
                critique.get("region_scores"),
                benchmark,
                f"{location}.region_scores",
                root,
                renders,
            )
        )
        critique_time = _parse_timestamp(critique.get("created_at"))
        if critique_time is None:
            errors.append(f"{location}.created_at: must be an ISO-8601 timestamp with timezone")
        critique_inspection = inspections.get(critique.get("inspection_id"))
        inspection_time = _parse_timestamp(critique_inspection.get("inspected_at")) if isinstance(critique_inspection, dict) else None
        if inspection_time and critique_time and critique_time < inspection_time:
            errors.append(f"{location}.created_at: cannot precede its inspection")
        if execution_start and critique_time and critique_time < execution_start:
            errors.append(f"{location}.created_at: cannot precede execution start")
        if execution_end and critique_time and critique_time > execution_end:
            errors.append(f"{location}.created_at: cannot follow execution completion")
        linked_score_times = score_times_by_inspection.get(str(critique.get("inspection_id")), [])
        if linked_score_times and critique_time and critique_time < max(linked_score_times):
            errors.append(f"{location}.created_at: cannot precede the score for its inspection")
        if critique.get("verdict") in PASS_VERDICTS:
            if not critique.get("independent"):
                errors.append(f"{location}: PASS critique must be independent")
            if not critique.get("blinded"):
                errors.append(f"{location}: PASS critique must be blinded")
            if critique.get("independence") != "INDEPENDENT":
                errors.append(f"{location}: PASS critique must declare INDEPENDENT independence")
            if not _independent_critic_is_qualified(critique):
                errors.append(f"{location}: PASS critique must include an auditable blind packet and reviewer provenance")
            errors.extend(_critic_artifact_binding_errors(critique, artifacts, renders, location))
            if critique.get("evidence_missing"):
                errors.append(f"{location}: PASS critique cannot declare missing evidence")
            if critique.get("evidence_quality") in {"LOW", "NONE"}:
                errors.append(f"{location}: PASS critique requires non-trivial evidence quality")

    for index, iteration in enumerate(payload.get("iterations", [])):
        if not isinstance(iteration, dict):
            continue
        location = f"$.iterations[{index}]"
        if iteration.get("before_render_id") not in renders:
            errors.append(f"{location}.before_render_id: unknown render")
        after_id = iteration.get("after_render_id")
        if iteration.get("action") != "stop" and after_id not in renders:
            errors.append(f"{location}.after_render_id: edit/regenerate iterations require a new render")
        action = iteration.get("action")
        if action in {"edit", "regenerate"}:
            if after_id == iteration.get("before_render_id"):
                errors.append(f"{location}: material iterations require a distinct after render")
            before_render = renders.get(iteration.get("before_render_id"))
            after_render = renders.get(after_id)
            if isinstance(before_render, dict) and isinstance(after_render, dict):
                before_identity, before_identity_errors = _render_identity(
                    before_render,
                    root,
                    f"{location}.before_render",
                )
                after_identity, after_identity_errors = _render_identity(
                    after_render,
                    root,
                    f"{location}.after_render",
                )
                errors.extend(before_identity_errors)
                errors.extend(after_identity_errors)
                if before_render.get("path") == after_render.get("path"):
                    errors.append(f"{location}: material iterations require a new render path")
                if before_identity and after_identity and before_identity == after_identity:
                    errors.append(f"{location}: before and after renders have identical content")
                elif before_identity is None or after_identity is None:
                    errors.append(
                        f"{location}: material iterations require verifiable render content identity"
                    )
                before_captured = _parse_timestamp(before_render.get("captured_at"))
                after_captured = _parse_timestamp(after_render.get("captured_at"))
                if before_captured and after_captured and after_captured <= before_captured:
                    errors.append(f"{location}: after render must be captured after before render")
            if not isinstance(iteration.get("correction_brief"), str) or not iteration.get("correction_brief", "").strip():
                errors.append(f"{location}.correction_brief: material iterations require a correction brief")
            if not _is_number(iteration.get("score_before")) or not _is_number(iteration.get("score_after")):
                errors.append(f"{location}: material iterations require score_before and score_after")
            errors.extend(_check_evidence(iteration.get("evidence", []), f"{location}.evidence", root, allow_empty=False))
            after_inspections = [
                inspection
                for inspection in payload.get("inspections", [])
                if isinstance(inspection, dict) and inspection.get("render_id") == after_id
            ]
            if not after_inspections:
                errors.append(f"{location}: material iterations require a fresh inspection of the after render")
            after_inspection_ids = {
                inspection.get("id")
                for inspection in after_inspections
                if isinstance(inspection.get("id"), str)
            }
            if not any(
                isinstance(score, dict) and score.get("inspection_id") in after_inspection_ids
                for score in payload.get("scores", [])
            ):
                errors.append(f"{location}: material iterations require a score linked to the after inspection")
            if not any(
                isinstance(critique, dict) and critique.get("inspection_id") in after_inspection_ids
                for critique in payload.get("critiques", [])
            ):
                errors.append(f"{location}: material iterations require a fresh critique linked to the after inspection")
        elif action == "stop" and not isinstance(iteration.get("stop_reason"), str):
            errors.append(f"{location}.stop_reason: stop iterations require an explicit stop reason")

    budget_record = payload.get("iteration_budget")
    if isinstance(budget_record, dict):
        max_cycles = budget_record.get("max_cycles")
        cycles_used = budget_record.get("cycles_used")
        remaining_cycles = budget_record.get("remaining_cycles")
        actual_cycles = sum(
            1
            for item in payload.get("iterations", [])
            if isinstance(item, dict) and item.get("action") in {"edit", "regenerate"}
        )
        benchmark_limit = _iteration_budget_limit(benchmark)
        if benchmark_limit is not None and max_cycles != benchmark_limit:
            errors.append(
                f"$.iteration_budget.max_cycles: {max_cycles!r} does not match benchmark budget {benchmark_limit}"
            )
        if cycles_used != actual_cycles:
            errors.append(
                f"$.iteration_budget.cycles_used: {cycles_used!r} does not match {actual_cycles} material iteration(s)"
            )
        if _is_integer(max_cycles) and _is_integer(cycles_used) and _is_integer(remaining_cycles):
            if cycles_used > max_cycles:
                errors.append("$.iteration_budget: cycles_used exceeds max_cycles")
            if remaining_cycles != max_cycles - cycles_used:
                errors.append("$.iteration_budget.remaining_cycles: must equal max_cycles - cycles_used")

    errors.extend(_validate_ledger_entries(payload.get("ledger", []), root, "$.ledger", schema))
    for index, entry in enumerate(payload.get("ledger", [])):
        if not isinstance(entry, dict):
            continue
        location = f"$.ledger[{index}]"
        render_id = entry.get("render_id")
        render = renders.get(render_id)
        if render is None:
            errors.append(f"{location}.render_id: unknown render {render_id!r}")
            continue
        if _viewport_width(entry.get("viewport")) != _viewport_width(render.get("viewport")):
            errors.append(f"{location}.viewport: does not match its render viewport")
        if entry.get("state") != render.get("state"):
            errors.append(f"{location}.state: does not match its render state")
        errors.extend(
            _visual_evidence_errors(
                entry.get("evidence", []),
                f"{location}.evidence",
                root,
                required_render_path=render.get("path") if isinstance(render.get("path"), str) else None,
            )
        )

    gates = payload.get("gates", {})
    if isinstance(gates, dict):
        for gate_name, gate in gates.items():
            if isinstance(gate, dict) and gate.get("status") == "pass":
                errors.extend(_check_evidence(gate.get("evidence", []), f"$.gates.{gate_name}.evidence", root))
                if not gate.get("evidence"):
                    errors.append(f"$.gates.{gate_name}.evidence: PASS gates require evidence")

    final_decision = payload.get("final_decision", {})
    verdict = final_decision.get("verdict") if isinstance(final_decision, dict) else None
    if isinstance(final_decision, dict):
        requested_verdict = final_decision.get("requested_verdict")
        if isinstance(requested_verdict, str) and requested_verdict != verdict:
            errors.append("$.final_decision.requested_verdict: does not match verdict")
        decided_at = _parse_timestamp(final_decision.get("decided_at"))
        if "decided_at" in final_decision and decided_at is None:
            errors.append("$.final_decision.decided_at: must be an ISO-8601 timestamp with timezone")
        final_evidence = final_decision.get("evidence")
        if "evidence" in final_decision:
            errors.extend(_check_evidence(final_evidence, "$.final_decision.evidence", root))
        if decided_at and execution_start and decided_at < execution_start:
            errors.append("$.final_decision.decided_at: cannot precede execution start")
        if (
            decided_at
            and isinstance(execution, dict)
            and execution.get("status") == "complete"
            and execution_end
            and decided_at < execution_end
        ):
            errors.append("$.final_decision.decided_at: cannot precede execution completion")
    override = payload.get("human_override")
    if isinstance(override, dict):
        if verdict == "AAA CANDIDATE":
            errors.append("$.human_override: an overridden result cannot be AAA CANDIDATE")
        requested_verdict = override.get("requested_verdict")
        if isinstance(requested_verdict, str) and requested_verdict != verdict:
            errors.append("$.human_override.requested_verdict: does not match final decision verdict")
        if (
            override.get("accepted_below_threshold")
            and isinstance(final_decision, dict)
            and final_decision.get("stop_reason") != "human-override"
        ):
            errors.append("$.final_decision.stop_reason: human override requires human-override")
        errors.extend(
            _check_evidence(
                override.get("compensating_evidence", []),
                "$.human_override.compensating_evidence",
                root,
                allow_empty=False,
            )
        )

    if enforce_final and verdict in APPROVAL_VERDICTS:
        required_final_fields = (
            "decided_at",
            "evidence",
            "render_ids",
            "inspection_id",
            "score_id",
            "critique_id",
        )
        for field in required_final_fields:
            value = final_decision.get(field) if isinstance(final_decision, dict) else None
            if field == "evidence":
                present = isinstance(value, list) and bool(value)
            elif field == "render_ids":
                present = isinstance(value, list) and bool(value)
            else:
                present = isinstance(value, str) and bool(value.strip())
            if not present:
                errors.append(f"$.final_decision.{field}: approval decisions require this binding")
        if isinstance(final_decision, dict):
            final_render_ids = final_decision.get("render_ids", [])
            render_id_set = {
                item.get("id")
                for item in payload.get("renders", [])
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            }
            if isinstance(final_render_ids, list):
                unknown = sorted(set(final_render_ids) - render_id_set)
                missing = sorted(render_id_set - set(final_render_ids))
                if unknown:
                    errors.append("$.final_decision.render_ids: contains unknown render IDs: " + ", ".join(unknown))
                if missing:
                    errors.append("$.final_decision.render_ids: must include every run render: " + ", ".join(missing))
            latest_score_id = _latest_record_id(payload, "scores")
            latest_critique_id = _latest_record_id(payload, "critiques")
            if final_decision.get("inspection_id") != latest_inspection_id:
                errors.append("$.final_decision.inspection_id: must bind the latest inspection")
            if final_decision.get("score_id") != latest_score_id:
                errors.append("$.final_decision.score_id: must bind the latest score")
            if final_decision.get("critique_id") != latest_critique_id:
                errors.append("$.final_decision.critique_id: must bind the latest critique")
            final_time = _parse_timestamp(final_decision.get("decided_at"))
            latest_score = next(
                (item for item in reversed(payload.get("scores", [])) if isinstance(item, dict)),
                None,
            )
            latest_critique = next(
                (item for item in reversed(payload.get("critiques", [])) if isinstance(item, dict)),
                None,
            )
            latest_score_time = _parse_timestamp(latest_score.get("scored_at")) if isinstance(latest_score, dict) else None
            latest_critique_time = _parse_timestamp(latest_critique.get("created_at")) if isinstance(latest_critique, dict) else None
            if final_time and latest_score_time and final_time < latest_score_time:
                errors.append("$.final_decision.decided_at: cannot precede the latest score")
            if final_time and latest_critique_time and final_time < latest_critique_time:
                errors.append("$.final_decision.decided_at: cannot precede the latest critique")
            if not isinstance(final_decision.get("approved_by"), str) or not final_decision.get("approved_by", "").strip():
                errors.append("$.final_decision.approved_by: approval decisions require an explicit approver")
    if enforce_final and isinstance(benchmark, dict) and verdict in PASS_VERDICTS:
        if payload.get("execution", {}).get("status") != "complete":
            errors.append("$.final_decision: PASS requires execution.status=complete")
        required_ids = {
            artifact_id
            for artifact_id, expected in expected_artifacts.items()
            if expected.get("required", True) is not False
        }
        missing_ids = sorted(required_ids - set(artifacts))
        if missing_ids:
            errors.append(f"$.final_decision: missing required benchmark artifacts: {', '.join(missing_ids)}")
        blocked_ids = sorted(
            artifact_id
            for artifact_id in required_ids
            if artifact_id in artifacts and artifacts[artifact_id].get("status") != "produced"
        )
        if blocked_ids:
            errors.append(f"$.final_decision: required artifacts are not produced: {', '.join(blocked_ids)}")
    if enforce_final and verdict in PASS_VERDICTS:
        if not payload.get("renders"):
            errors.append("$.final_decision: PASS requires at least one render")
        if not payload.get("inspections"):
            errors.append("$.final_decision: PASS requires at least one inspection")
        if not payload.get("scores"):
            errors.append("$.final_decision: PASS requires at least one score")
        independent = [
            item
            for item in payload.get("critiques", [])
            if isinstance(item, dict) and item.get("verdict") == "PASS"
            and _independent_critic_is_qualified(item)
        ]
        if not independent:
            errors.append("$.final_decision: PASS requires an independent, blinded critic")
        latest_render = renders.get(latest_render_id)
        latest_inspection = inspections.get(latest_inspection_id)
        if not isinstance(latest_render, dict) or not isinstance(latest_inspection, dict):
            errors.append("$.final_decision: PASS requires a current render and inspection chain")
        else:
            passing_render_ids = {
                inspection.get("render_id")
                for inspection in payload.get("inspections", [])
                if isinstance(inspection, dict) and inspection.get("status") == "pass"
            }
            missing_render_inspections = sorted(
                set(renders) - passing_render_ids
            )
            if missing_render_inspections:
                errors.append(
                    "$.final_decision: every render requires a passing inspection; missing "
                    + ", ".join(missing_render_inspections)
                )
            if latest_inspection.get("status") != "pass":
                errors.append("$.final_decision: latest inspection must pass")
            if latest_inspection.get("render_id") != latest_render_id:
                errors.append("$.final_decision: latest inspection must inspect the latest render")
            score_records = payload.get("scores", [])
            latest_score = score_records[-1] if isinstance(score_records, list) and score_records else None
            if not isinstance(latest_score, dict) or latest_score.get("inspection_id") != latest_inspection_id:
                errors.append("$.final_decision: latest score must link to the latest inspection")
            if not any(
                critique.get("inspection_id") == latest_inspection_id
                for critique in independent
            ):
                errors.append("$.final_decision: independent critic must inspect the latest inspection")
        if not any(
            isinstance(render, dict)
            and (render.get("evidence") or render.get("path"))
            for render in payload.get("renders", [])
        ):
            errors.append("$.final_decision: PASS requires render evidence")
        for index, critique in enumerate(independent):
            if critique.get("evidence_missing"):
                errors.append(f"$.critiques: independent critic {index} has missing evidence")

    return errors


def validate_run(
    payload: Any,
    root: Path | None = None,
    benchmark: dict[str, Any] | None = None,
    *,
    enforce_final: bool = True,
) -> list[str]:
    errors = _base_errors(payload, "run")
    if isinstance(payload, dict):
        errors.extend(_validate_run_semantics(payload, root, benchmark, enforce_final=enforce_final))
    return sorted(set(errors))


def _validate_critic_semantics(payload: dict[str, Any], root: Path | None = None) -> list[str]:
    errors = _finding_group_errors(payload.get("findings"), "$.findings")
    errors.extend(_finding_evidence_errors(payload.get("findings"), "$.findings", root))
    errors.extend(_finding_evidence_errors({"critical": payload.get("constraint_violations", [])}, "$.constraint_violations", root))
    if payload.get("verdict") in PASS_VERDICTS:
        if not payload.get("independent"):
            errors.append("$: PASS critic result must be independent")
        if not payload.get("blinded"):
            errors.append("$: PASS critic result must be blinded")
        if payload.get("independence") != "INDEPENDENT":
            errors.append("$: PASS critic result must declare INDEPENDENT independence")
        if not _independent_critic_is_qualified(payload):
            errors.append("$: PASS critic result must include an auditable blind packet and reviewer provenance")
        if payload.get("evidence_missing"):
            errors.append("$: PASS critic result cannot declare missing evidence")
        if payload.get("evidence_quality") in {"LOW", "NONE"}:
            errors.append("$: PASS critic result requires non-trivial evidence quality")
    return errors


def validate_critic(payload: Any, root: Path | None = None) -> list[str]:
    errors = _base_errors(payload, "critic")
    if isinstance(payload, dict):
        errors.extend(_validate_critic_semantics(payload, root))
        if isinstance(payload.get("evidence_missing"), list) and payload.get("verdict") in PASS_VERDICTS:
            errors.extend(_check_evidence(payload.get("evidence_missing", []), "$.evidence_missing", root))
    return sorted(set(errors))


def validate_ledger(payload: Any, root: Path | None = None) -> list[str]:
    errors = _base_errors(payload, "ledger")
    if isinstance(payload, dict):
        schema, schema_errors = _load_schema("ledger")
        errors.extend(schema_errors)
        if schema is not None:
            errors.extend(_validate_ledger_entries(payload.get("entries", []), root, "$.entries", schema))
    return sorted(set(errors))


def infer_kind(payload: Any) -> str:
    if isinstance(payload, dict):
        if "final_decision" in payload:
            return "run"
        if "entries" in payload and "benchmark_id" in payload:
            return "ledger"
        if "findings" in payload and "independent" in payload:
            return "critic"
    return "benchmark"


def validate(kind: str, payload: Any, root: Path | None = None) -> list[str]:
    if kind == "benchmark":
        return validate_benchmark(payload, root)
    if kind == "run":
        return validate_run(payload, root)
    if kind == "critic":
        return validate_critic(payload, root)
    if kind == "ledger":
        return validate_ledger(payload, root)
    raise ValueError(f"unknown contract kind: {kind}")


def validate_benchmark_directory(path: Path, root: Path | None = None) -> dict[str, Any]:
    """Validate every golden benchmark below a directory.

    ``benchmarks`` and ``benchmarks/golden`` are both accepted.  The explicit
    directory result makes CI failures attributable to one benchmark instead
    of collapsing seven contract checks into one opaque exit code.
    """

    directory = path.resolve()
    golden_root = directory / "golden" if (directory / "golden").is_dir() else directory
    repository_root = root.resolve() if root is not None else (
        directory.parent if directory.name == "benchmarks" else directory.parent.parent
    )
    files = sorted(
        candidate
        for candidate in golden_root.glob("*.json")
        if candidate.is_file() and candidate.name not in {"assets.json"}
    )
    file_results: list[dict[str, Any]] = []
    for candidate in files:
        payload, load_errors = load_json(candidate)
        errors = load_errors or validate_benchmark(payload, repository_root)
        try:
            display_path = str(candidate.relative_to(repository_root))
        except ValueError:
            display_path = str(candidate)
        file_result: dict[str, Any] = {
            "path": display_path,
            "id": payload.get("id") if isinstance(payload, dict) else None,
            "valid": not errors,
        }
        if errors:
            file_result["errors"] = errors
        file_results.append(file_result)
    catalog_errors: list[str] = []
    observed_ids = {
        item.get("id")
        for item in file_results
        if isinstance(item.get("id"), str)
    }
    missing_ids = sorted(GOLDEN_BENCHMARK_IDS - observed_ids)
    unexpected_ids = sorted(observed_ids - GOLDEN_BENCHMARK_IDS)
    if missing_ids:
        catalog_errors.append("missing required golden benchmarks: " + ", ".join(missing_ids))
    if unexpected_ids:
        catalog_errors.append("unexpected golden benchmarks: " + ", ".join(unexpected_ids))
    if not files:
        file_results.append({"path": str(golden_root), "valid": False, "errors": ["no golden benchmark JSON files found"]})
    return {
        "kind": "benchmark-directory",
        "path": str(path),
        "valid": all(bool(item.get("valid")) for item in file_results) and not catalog_errors,
        "benchmark_count": len(files),
        "files": file_results,
        "errors": catalog_errors,
    }


def _dump(payload: Any, pretty: bool = False) -> str:
    kwargs: dict[str, Any] = {
        "ensure_ascii": False,
        "sort_keys": True,
    }
    if pretty:
        kwargs["indent"] = 2
    else:
        kwargs["separators"] = (",", ":")
    return json.dumps(payload, **kwargs)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="validate a benchmark, run, critic, or ledger JSON")
    validate_parser.add_argument("path", type=Path)
    validate_parser.add_argument("--kind", choices=("auto", *SCHEMA_FILES), default="auto")
    validate_parser.add_argument("--root", type=Path, help="repository root for local path checks")
    validate_parser.add_argument(
        "--benchmark",
        type=Path,
        help="benchmark JSON required when validating a run packet",
    )
    validate_parser.add_argument("--pretty", action="store_true")

    args = parser.parse_args(argv)
    if args.path.is_dir():
        if args.kind not in {"auto", "benchmark"}:
            parser.error("directory validation only supports benchmark contracts")
        result = validate_benchmark_directory(args.path, args.root)
        print(_dump(result, args.pretty))
        return 0 if result["valid"] else 2

    payload, load_errors = load_json(args.path)
    kind = infer_kind(payload) if args.kind == "auto" else args.kind
    errors: list[str] = list(load_errors)
    benchmark: dict[str, Any] | None = None
    if kind == "run":
        if args.benchmark is None:
            errors.append("run validation requires --benchmark PATH")
        else:
            benchmark, benchmark_load_errors = load_json(args.benchmark)
            errors.extend(benchmark_load_errors)
            if not benchmark_load_errors:
                errors.extend(validate_benchmark(benchmark, args.root))
    if not load_errors:
        if kind == "run":
            errors.extend(validate_run(payload, args.root, benchmark))
        else:
            errors.extend(validate(kind, payload, args.root))
    errors = sorted(set(errors))
    result = {
        "kind": kind,
        "path": str(args.path),
        "valid": not errors,
    }
    if errors:
        result["errors"] = errors
    print(_dump(result, args.pretty))
    return 0 if not errors else 2


if __name__ == "__main__":
    sys.exit(main())
