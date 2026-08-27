#!/usr/bin/env python3
"""Regression tests for the evidence-driven benchmark contracts and scorer."""

from __future__ import annotations

import copy
import hashlib
import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]
REPOSITORY = SCRIPTS.parents[2]


def png_bytes(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    scanline = b"\x00" + (b"\x20\x40\x60\xff" * width)
    pixels = scanline * height
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(pixels, 1))
        + chunk(b"IEND", b"")
    )


RENDER_PNG = png_bytes(1440, 900)
RENDER_SHA256 = hashlib.sha256(RENDER_PNG).hexdigest()


class BenchmarkContractTests(unittest.TestCase):
    def run_script(self, name: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / name), *args],
            check=False,
            capture_output=True,
            text=True,
            cwd=REPOSITORY,
        )

    @staticmethod
    def write_json(root: Path, name: str, payload: object) -> Path:
        path = root / name
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    @staticmethod
    def benchmark() -> dict[str, object]:
        return {
            "id": "B02-saas-landing",
            "category": "landing-page",
            "brief": {
                "objective": "Present an operational SaaS product with a specific, credible visual system.",
                "audience": "Operations leads evaluating workflow software.",
                "surface": "Responsive marketing landing page.",
                "primary_action": "Request a demo.",
                "acceptance_criteria": [
                    "The hero establishes product specificity before the primary action.",
                    "The layout remains readable across the declared viewport matrix.",
                ],
            },
            "inputs": [
                {
                    "id": "brief",
                    "role": "brief",
                    "kind": "request",
                    "provenance": "user-supplied",
                    "content": "Build a precise operations landing page.",
                }
            ],
            "references": [],
            "constraints": {
                "scope": "new",
                "must_include": ["workflow proof", "accessible primary action"],
                "must_avoid": ["generic gradient hero", "invented customer logos"],
                "accessibility": ["keyboard", "focus", "contrast"],
                "responsive": ["desktop", "mobile"],
            },
            "viewports": [{"name": "desktop", "width": 1440, "height": 900}],
            "states": ["default"],
            "regions": ["hero"],
            "expected_artifacts": [
                {"id": "implementation", "kind": "ui", "role": "responsive landing page", "required": True},
            ],
            "preservation_rules": {
                "immutable": [],
                "high_sensitivity": [],
                "flexible": ["illustration direction", "surface treatment"],
                "forbidden_inference": ["customer claims", "performance claims"],
            },
            "quality_threshold": {
                "overall_min": 90,
                "aaa_min": 95,
                "evidence_confidence_min": "HIGH",
                "require_independent_critic": True,
                "block_critical": True,
                "block_high": True,
                "required_gates": ["render", "inspection", "independent-critique", "anti-slop"],
            },
            "iteration_budget": 3,
        }

    @staticmethod
    def run_packet() -> dict[str, object]:
        def quality_report(gate: str, checks: dict[str, object]) -> dict[str, object]:
            normalized_checks: dict[str, object] = {}
            for check_name, detail in checks.items():
                if isinstance(detail, dict):
                    normalized = dict(detail)
                    normalized.setdefault("evidence", ["render.png"])
                    normalized_checks[check_name] = normalized
                else:
                    normalized_checks[check_name] = {
                        "status": detail,
                        "evidence": ["render.png"],
                    }
            return {
                "producer": "quality_gates.py",
                "schema_version": 1,
                "gate": gate,
                "status": "PASS",
                "pass": True,
                "checks": normalized_checks,
            }

        dimensions = {
            "hierarchy": 9.6,
            "typography": 9.6,
            "spacing-layout": 9.6,
            "color": 9.6,
            "consistency": 9.6,
            "usability": 9.6,
            "responsiveness": 9.6,
            "accessibility": 9.6,
            "specificity": 9.6,
            "polish": 9.6,
        }
        empty_findings = {key: [] for key in ("critical", "high", "medium", "low", "polish")}
        packet = {
            "schema_version": "1",
            "run_id": "run-001",
            "benchmark_id": "B02-saas-landing",
                "execution": {
                    "status": "complete",
                    "mode": "browser",
                    "started_at": "2026-08-26T23:00:00Z",
                    "completed_at": "2026-08-26T23:01:00Z",
                    "tooling": ["browser"],
                    "procedure": "Open the target route, capture the declared viewport/state, inspect the PNG, and record the result.",
                    "result": "Rendered and inspected the declared artifact.",
                    "artifact_ids": ["implementation"],
                    "evidence": ["render.png"],
                },
            "artifacts": [
                {
                    "id": "implementation",
                    "path": "artifact.html",
                    "kind": "ui",
                    "role": "implementation",
                    "provenance": "generated",
                    "sha256": hashlib.sha256(b"<main>fixture</main>").hexdigest(),
                    "status": "produced",
                }
            ],
            "renders": [
                {
                    "id": "render-desktop-default",
                    "artifact_id": "implementation",
                    "path": "render.png",
                    "viewport": {"width": 1440, "height": 900},
                    "state": "default",
                    "format": "png",
                    "sha256": RENDER_SHA256,
                    "captured_at": "2026-08-26T23:00:30Z",
                    "evidence": ["render.png"],
                }
            ],
            "inspections": [
                {
                    "id": "inspection-001",
                    "render_id": "render-desktop-default",
                    "method": "browser",
                    "status": "pass",
                    "inspected_at": "2026-08-26T23:00:40Z",
                    "evidence": ["render.png"],
                    "findings": [],
                }
            ],
            "scores": [
                {
                    "id": "score-001",
                    "inspection_id": "inspection-001",
                    "scored_at": "2026-08-26T23:00:50Z",
                    "dimensions": dimensions,
                    "applicable_dimensions": list(dimensions),
                    "weights": {key: 1 for key in dimensions},
                    "regions": [
                        {
                            "region": "hero",
                            "render_id": "render-desktop-default",
                            "score": 96,
                            "viewport": {"width": 1440, "height": 900},
                            "state": "default",
                            "evidence": ["render.png"],
                        }
                    ],
                    "source": "human",
                }
            ],
            "critiques": [
                {
                    "id": "critic-001",
                    "inspection_id": "inspection-001",
                    "created_at": "2026-08-26T23:00:55Z",
                    "reviewer_id": "independent-critic",
                    "independent": True,
                    "blinded": True,
                    "independence": "INDEPENDENT",
                    "verdict": "PASS",
                    "overall_score": 96,
                    "confidence": "HIGH",
                    "evidence_confidence": "HIGH",
                    "evidence_quality": "HIGH",
                    "blind_packet": {
                        "request": "Present an operational SaaS product with a specific, credible visual system.",
                        "constraints": ["Avoid generic SaaS treatment.", "Keep the primary action reachable."],
                        "references": [],
                        "artifact": ["artifact.html", "render.png"],
                        "acceptance_criteria": ["Hero establishes product specificity."],
                        "builder_rationale_withheld": True,
                        "self_score_withheld": True,
                    },
                    "reviewer_provenance": {
                        "process": "Fresh read-only review from the acceptance packet only.",
                        "context_shared": ["request", "constraints", "references", "artifact", "acceptance_criteria"],
                        "rationale_received": False,
                        "self_score_received": False,
                    },
                    "dimension_scores": dimensions,
                    "region_scores": [{"region": "hero", "render_id": "render-desktop-default", "score": 96, "viewport": {"width": 1440, "height": 900}, "state": "default", "evidence": ["render.png"]}],
                    "findings": empty_findings,
                    "top_corrections": [],
                    "constraint_violations": [],
                    "evidence_missing": [],
                }
            ],
            "iterations": [],
            "ledger": [
                {
                    "id": "hero-desktop-default",
                    "render_id": "render-desktop-default",
                    "region": "hero",
                    "viewport": {"width": 1440, "height": 900},
                    "state": "default",
                    "expected": "Product-specific hero hierarchy and clear primary action.",
                    "observed": "Matches acceptance criteria in the inspected render.",
                    "severity": "polish",
                    "evidence": ["render.png"],
                    "fix": "No material fix required.",
                    "status": "fixed",
                    "score": 96,
                }
            ],
            "iteration_budget": {"max_cycles": 3, "cycles_used": 0, "remaining_cycles": 3},
            "gates": {
                "identity": {"status": "not-applicable", "evidence": []},
                "accessibility": {
                    "status": "pass",
                    "evidence": ["render.png"],
                    "report": quality_report(
                        "accessibility",
                        {name: {"status": "PASS"} for name in ("keyboard", "focus", "semantics", "names", "errors", "non_color", "reduced_motion", "touch_targets", "zoom_reflow", "contrast")},
                    ),
                },
                "responsive": {"status": "not-applicable", "evidence": []},
                "performance": {
                    "status": "pass",
                    "evidence": ["render.png"],
                    "report": quality_report(
                        "performance",
                        {
                            "lcp": {"status": "PASS", "value_ms": 1800},
                            "cls": {"status": "PASS", "value": 0.03},
                            "responsive_images": {"status": "PASS"},
                            "font_loading": {"status": "PASS"},
                            "oversized_media": {"status": "PASS"},
                        },
                    ),
                },
                "anti_slop": {"status": "pass", "evidence": ["render.png"]},
            },
            "final_decision": {
                "verdict": "AAA CANDIDATE",
                "reason": "All declared gates and the independent critique are complete.",
                "stop_reason": "threshold",
                "score": 96,
                "evidence_confidence": "HIGH",
                "approved_by": "independent-critic",
                "decided_at": "2026-08-26T23:01:10Z",
                "evidence": ["render.png"],
                "render_ids": ["render-desktop-default"],
                "inspection_id": "inspection-001",
                "score_id": "score-001",
                "critique_id": "critic-001",
            },
        }
        blind_packet = packet["critiques"][0]["blind_packet"]
        packet["critiques"][0]["reviewer_provenance"]["builder_id"] = "builder-agent"
        packet["critiques"][0]["reviewer_provenance"]["packet_digest"] = hashlib.sha256(
            json.dumps(blind_packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return packet

    def test_schema_files_have_operational_required_fields(self) -> None:
        required = {
            "benchmark.schema.json": {
                "id", "category", "brief", "inputs", "references", "constraints",
                "viewports", "states", "expected_artifacts", "preservation_rules",
                "regions", "quality_threshold", "iteration_budget",
            },
            "run.schema.json": {
                "schema_version", "run_id", "benchmark_id", "execution", "artifacts",
                "renders", "inspections", "scores", "critiques", "iterations", "ledger", "final_decision",
            },
        }
        for name, expected in required.items():
            payload = json.loads((REPOSITORY / "benchmarks" / "schema" / name).read_text(encoding="utf-8"))
            self.assertTrue(expected.issubset(set(payload["required"])), name)

    def test_valid_benchmark_passes_with_local_path_checks(self) -> None:
        benchmark = self.benchmark()
        with tempfile.TemporaryDirectory(prefix="design-director-contract-") as temp_dir:
            root = Path(temp_dir)
            benchmark["references"] = [
                {
                    "id": "reference-layout",
                    "role": "composition",
                    "provenance": "user-supplied",
                    "path": "reference.svg",
                }
            ]
            (root / "reference.svg").write_text("<svg viewBox='0 0 10 10'></svg>", encoding="utf-8")
            path = self.write_json(root, "benchmark.json", benchmark)
            result = self.run_script("benchmark_validate.py", "validate", str(path), "--kind", "benchmark", "--root", str(root))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["valid"])

    def test_golden_benchmark_directory_passes_and_reports_each_fixture(self) -> None:
        result = self.run_script(
            "benchmark_validate.py",
            "validate",
            "benchmarks",
            "--root",
            str(REPOSITORY),
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["valid"])
        self.assertEqual(report["benchmark_count"], 7)
        self.assertEqual([item["id"] for item in report["files"]], [
            "B01-premium-banner",
            "B02-saas-landing",
            "B03-operational-dashboard",
            "B04-mobile-flow",
            "B05-screenshot-reconstruction",
            "B06-product-brand-identity",
            "B07-game-ui-asset-family",
        ])

    def test_golden_catalog_requires_the_complete_b01_to_b07_set(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-director-incomplete-catalog-") as temp_dir:
            root = Path(temp_dir)
            golden = root / "golden"
            golden.mkdir()
            self.write_json(golden, "B02-saas-landing.json", self.benchmark())
            result = self.run_script("benchmark_validate.py", "validate", str(golden), "--root", str(root))
        self.assertEqual(result.returncode, 2)
        report = json.loads(result.stdout)
        self.assertFalse(report["valid"])
        self.assertTrue(any("missing required golden benchmarks" in error for error in report["errors"]))

    def test_invalid_iteration_budget_is_rejected(self) -> None:
        benchmark = self.benchmark()
        benchmark["iteration_budget"] = 0
        with tempfile.TemporaryDirectory(prefix="design-director-invalid-budget-") as temp_dir:
            root = Path(temp_dir)
            path = self.write_json(root, "benchmark.json", benchmark)
            result = self.run_script("benchmark_validate.py", "validate", str(path), "--kind", "benchmark")
        self.assertEqual(result.returncode, 2)
        self.assertIn("iteration_budget", json.loads(result.stdout)["errors"][0])

    def test_valid_packet_scores_only_applicable_dimensions_and_is_deterministic(self) -> None:
        run = self.run_packet()
        with tempfile.TemporaryDirectory(prefix="design-director-score-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            first = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
            second = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(first.stdout, second.stdout)
        scored = json.loads(first.stdout)
        self.assertEqual(scored["decision"], "AAA CANDIDATE")
        self.assertEqual(scored["evidence_confidence"], "HIGH")
        self.assertEqual(scored["overall"], 96.0)

        run["scores"][0]["dimensions"] = {"hierarchy": 10, "typography": 5, "unused": 0}
        run["scores"][0]["applicable_dimensions"] = ["hierarchy", "typography"]
        run["scores"][0]["weights"] = {"hierarchy": 2, "typography": 1}
        with tempfile.TemporaryDirectory(prefix="design-director-applicable-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["overall"], 83.33)
        self.assertEqual(scored["applicable_dimensions"], ["hierarchy", "typography"])
        self.assertNotIn("unused", scored["dimension_scores"])

    def test_final_score_declaration_must_match_computed_score(self) -> None:
        run = self.run_packet()
        run["final_decision"]["score"] = 99
        with tempfile.TemporaryDirectory(prefix="design-director-final-score-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["decision"], "BLOCKED")
        self.assertTrue(any("final decision score" in item for item in scored["gate_failures"]))

    def test_approval_requires_current_chain_bindings(self) -> None:
        run = self.run_packet()
        del run["final_decision"]["critique_id"]
        with tempfile.TemporaryDirectory(prefix="design-director-final-binding-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script(
                "score_visual.py",
                "score",
                str(run_path),
                "--benchmark",
                str(benchmark_path),
                "--root",
                str(root),
            )
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["decision"], "BLOCKED")
        self.assertIn("approval requires final_decision.critique_id", scored["gate_failures"])

    def test_produced_artifact_requires_a_matching_sha256(self) -> None:
        run = self.run_packet()
        del run["artifacts"][0]["sha256"]
        with tempfile.TemporaryDirectory(prefix="design-director-artifact-digest-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script(
                "benchmark_validate.py",
                "validate",
                str(run_path),
                "--kind",
                "run",
                "--benchmark",
                str(benchmark_path),
                "--root",
                str(root),
            )
        self.assertEqual(result.returncode, 2)
        self.assertTrue(any("produced artifacts require a SHA-256" in error for error in json.loads(result.stdout)["errors"]))

    def test_critique_must_follow_the_score_for_its_inspection(self) -> None:
        run = self.run_packet()
        run["critiques"][0]["created_at"] = "2026-08-26T23:00:45Z"
        with tempfile.TemporaryDirectory(prefix="design-director-critique-order-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script(
                "score_visual.py",
                "score",
                str(run_path),
                "--benchmark",
                str(benchmark_path),
                "--root",
                str(root),
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("cannot precede the score", " ".join(json.loads(result.stdout)["errors"]))

    def test_score_record_overall_must_match_computed_score(self) -> None:
        run = self.run_packet()
        run["scores"][0]["overall"] = 99
        with tempfile.TemporaryDirectory(prefix="design-director-score-record-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script(
                "score_visual.py",
                "score",
                str(run_path),
                "--benchmark",
                str(benchmark_path),
                "--root",
                str(root),
            )
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["decision"], "BLOCKED")
        self.assertIn("score record overall", " ".join(scored["gate_failures"]))

    def test_frontend_report_must_cover_all_checks_with_local_evidence(self) -> None:
        run = self.run_packet()
        report = run["gates"]["accessibility"]["report"]
        assert isinstance(report, dict)
        checks = report["checks"]
        assert isinstance(checks, dict)
        del checks["keyboard"]
        with tempfile.TemporaryDirectory(prefix="design-director-incomplete-report-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script(
                "score_visual.py",
                "score",
                str(run_path),
                "--benchmark",
                str(benchmark_path),
                "--root",
                str(root),
            )
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["decision"], "BLOCKED")
        self.assertEqual(scored["gates"]["accessibility"]["status"], "blocked")

    def test_complete_quality_gates_report_is_consumed_by_the_scorer(self) -> None:
        run = self.run_packet()
        quality_packet = {
            "evidence": {
                "accessibility": {
                    name: {"status": "PASS", "evidence": ["render.png"]}
                    for name in ("keyboard", "focus", "semantics", "names", "errors", "non_color", "reduced_motion", "touch_targets", "zoom_reflow", "contrast")
                },
                "performance": {
                    "lcp": {"status": "PASS", "value_ms": 1800, "evidence": ["render.png"]},
                    "cls": {"status": "PASS", "value": 0.03, "evidence": ["render.png"]},
                    **{
                        name: {"status": "PASS", "evidence": ["render.png"]}
                        for name in ("responsive_images", "font_loading", "oversized_media")
                    },
                },
                "typography": {
                    name: {"status": "PASS", "evidence": ["render.png"]}
                    for name in ("heading_hierarchy", "measure", "line_height", "fallback", "numeric_alignment", "mobile_scale")
                },
                "copy_stress": {
                    name: {"status": "PASS", "evidence": ["render.png"]}
                    for name in ("short_content", "long_content", "empty_content", "large_numbers", "localized_content")
                },
            }
        }
        with tempfile.TemporaryDirectory(prefix="design-director-complete-report-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            quality_packet_path = self.write_json(root, "quality-packet.json", quality_packet)
            quality_result = self.run_script("quality_gates.py", str(quality_packet_path))
            self.assertEqual(quality_result.returncode, 0, quality_result.stdout + quality_result.stderr)
            complete_report = json.loads(quality_result.stdout)
            run["gates"]["accessibility"]["report"] = complete_report
            run["gates"]["performance"]["report"] = complete_report
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script(
                "score_visual.py",
                "score",
                str(run_path),
                "--benchmark",
                str(benchmark_path),
                "--root",
                str(root),
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["decision"], "AAA CANDIDATE")
        self.assertEqual(scored["gates"]["accessibility"]["status"], "pass")
        self.assertEqual(scored["gates"]["performance"]["status"], "pass")

    def test_pass_approval_must_be_signed_by_the_independent_critic(self) -> None:
        run = self.run_packet()
        run["final_decision"]["approved_by"] = "builder-agent"
        with tempfile.TemporaryDirectory(prefix="design-director-approval-signer-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script(
                "score_visual.py",
                "score",
                str(run_path),
                "--benchmark",
                str(benchmark_path),
                "--root",
                str(root),
            )
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["decision"], "BLOCKED")
        self.assertIn("signed by the latest independent critic", " ".join(scored["gate_failures"]))

    def test_missing_render_blocks_even_when_final_decision_claims_pass(self) -> None:
        run = self.run_packet()
        run["renders"] = []
        run["inspections"] = []
        run["scores"] = []
        run["critiques"] = []
        run["ledger"] = []
        run["final_decision"] = {"verdict": "PASS", "reason": "incorrectly declared", "stop_reason": "threshold"}
        with tempfile.TemporaryDirectory(prefix="design-director-missing-render-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertIn("decision", scored, result.stdout)
        self.assertEqual(scored["decision"], "BLOCKED")
        self.assertIn("render evidence is not verified", scored["gate_failures"])

    def test_non_decodable_image_cannot_satisfy_render_gate(self) -> None:
        run = self.run_packet()
        run["renders"][0]["sha256"] = hashlib.sha256(b"not a screenshot").hexdigest()
        with tempfile.TemporaryDirectory(prefix="design-director-fake-render-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(b"not a screenshot")
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 2)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["status"], "invalid")
        self.assertTrue(any("not locally decodable" in error for error in scored["errors"]))

    def test_nonvisual_file_cannot_satisfy_render_gate(self) -> None:
        run = self.run_packet()
        run["renders"][0]["format"] = "html"
        with tempfile.TemporaryDirectory(prefix="design-director-html-render-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 2)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["status"], "invalid")
        self.assertTrue(any("format" in error for error in scored["errors"]))

    def test_incomplete_execution_cannot_reach_aaa(self) -> None:
        run = self.run_packet()
        run["execution"]["status"] = "blocked"
        with tempfile.TemporaryDirectory(prefix="design-director-execution-blocked-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["decision"], "BLOCKED")
        self.assertEqual(scored["gates"]["execution"]["status"], "blocked")

    def test_svg_cannot_satisfy_screenshot_contract(self) -> None:
        run = self.run_packet()
        run["renders"][0]["format"] = "svg"
        with tempfile.TemporaryDirectory(prefix="design-director-svg-render-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 2)
        self.assertTrue(any("format" in error for error in json.loads(result.stdout)["errors"]))

    def test_region_evidence_must_be_a_raster_capture(self) -> None:
        run = self.run_packet()
        run["scores"][0]["regions"][0]["evidence"] = ["artifact.html"]
        run["ledger"][0]["evidence"] = ["artifact.html"]
        with tempfile.TemporaryDirectory(prefix="design-director-region-source-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 2)
        self.assertTrue(any("raster evidence" in error for error in json.loads(result.stdout)["errors"]))

    def test_region_evidence_must_include_the_current_render(self) -> None:
        run = self.run_packet()
        run["scores"][0]["regions"][0]["evidence"] = ["stale.png"]
        run["ledger"][0]["evidence"] = ["stale.png"]
        with tempfile.TemporaryDirectory(prefix="design-director-stale-region-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            (root / "stale.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script(
                "score_visual.py",
                "score",
                str(run_path),
                "--benchmark",
                str(benchmark_path),
                "--root",
                str(root),
            )
        self.assertEqual(result.returncode, 2)
        self.assertTrue(any("current render path" in error for error in json.loads(result.stdout)["errors"]))

    def test_blocked_independent_critic_cannot_satisfy_approval_gate(self) -> None:
        run = self.run_packet()
        run["critiques"][0]["verdict"] = "BLOCKED"
        with tempfile.TemporaryDirectory(prefix="design-director-blocked-critic-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["decision"], "BLOCKED")
        self.assertEqual(scored["gates"]["independent-critique"]["status"], "blocked")

    def test_missing_region_evidence_cannot_be_promoted_to_pass(self) -> None:
        run = self.run_packet()
        run["scores"][0]["regions"][0]["evidence"] = ["missing-region.png"]
        run["ledger"][0]["evidence"] = ["missing-region.png"]
        with tempfile.TemporaryDirectory(prefix="design-director-region-evidence-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 2)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["status"], "invalid")
        self.assertTrue(any("missing-region.png" in error for error in scored["errors"]))

    def test_visual_score_requires_a_bound_benchmark(self) -> None:
        run = self.run_packet()
        with tempfile.TemporaryDirectory(prefix="design-director-unbound-run-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--root", str(root))
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["decision"], "BLOCKED")
        self.assertIn("benchmark contract is required", " ".join(scored["gate_failures"]))

    def test_stale_critic_and_score_cannot_approve_a_new_render(self) -> None:
        run = self.run_packet()
        run["renders"].append(
            {
                "id": "render-desktop-default-new",
                "artifact_id": "implementation",
                "path": "render-new.png",
                "viewport": {"width": 1440, "height": 900},
                "state": "default",
                "format": "png",
                "sha256": RENDER_SHA256,
                "captured_at": "2026-08-26T23:00:30Z",
                "evidence": ["render-new.png"],
            }
        )
        run["inspections"].append(
            {
                "id": "inspection-new",
                "render_id": "render-desktop-default-new",
                "method": "browser",
                "status": "pass",
                "inspected_at": "2026-08-26T23:00:40Z",
                "evidence": ["render-new.png"],
                "findings": [],
            }
        )
        run["execution"]["evidence"].append("render-new.png")
        with tempfile.TemporaryDirectory(prefix="design-director-stale-chain-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            (root / "render-new.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script(
                "score_visual.py",
                "score",
                str(run_path),
                "--benchmark",
                str(benchmark_path),
                "--root",
                str(root),
            )
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["decision"], "BLOCKED")
        self.assertEqual(scored["gates"]["independent-critique"]["status"], "blocked")
        self.assertEqual(scored["gates"]["score"]["status"], "blocked")

    def test_passing_critic_must_name_this_run_artifact(self) -> None:
        run = self.run_packet()
        run["critiques"][0]["blind_packet"]["artifact"] = ["stale-render.png"]
        run["critiques"][0]["reviewer_provenance"]["packet_digest"] = hashlib.sha256(
            json.dumps(
                run["critiques"][0]["blind_packet"],
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        with tempfile.TemporaryDirectory(prefix="design-director-critic-binding-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script(
                "score_visual.py",
                "score",
                str(run_path),
                "--benchmark",
                str(benchmark_path),
                "--root",
                str(root),
            )
        self.assertEqual(result.returncode, 2)
        self.assertIn("must name at least one artifact", result.stdout)

    def test_material_iteration_requires_distinct_after_render(self) -> None:
        run = self.run_packet()
        run["iterations"] = [
            {
                "id": "cycle-1",
                "action": "edit",
                "before_render_id": "render-desktop-default",
                "after_render_id": "render-desktop-default",
                "target": "hero CTA",
                "reason": "Fix the local CTA contrast gap.",
                "status": "complete",
                "correction_brief": "Increase CTA contrast while preserving the visual system.",
                "score_before": 90,
                "score_after": 96,
                "evidence": ["render.png"],
            }
        ]
        run["iteration_budget"] = {"max_cycles": 3, "cycles_used": 1, "remaining_cycles": 2}
        with tempfile.TemporaryDirectory(prefix="design-director-stale-iteration-") as temp_dir:
            root = Path(temp_dir)
            path = self.write_json(root, "run.json", run)
            result = self.run_script("benchmark_validate.py", "validate", str(path), "--kind", "run", "--root", str(root))
        self.assertEqual(result.returncode, 2)
        self.assertTrue(any("distinct after render" in error for error in json.loads(result.stdout)["errors"]))

    def test_material_iteration_rejects_reused_render_content(self) -> None:
        run = self.run_packet()
        run["renders"].append(
            {
                "id": "render-desktop-default-copy",
                "artifact_id": "implementation",
                "path": "render-copy.png",
                "viewport": {"width": 1440, "height": 900},
                "state": "default",
                "format": "png",
                "sha256": RENDER_SHA256,
                "captured_at": "2026-08-26T23:00:30Z",
                "evidence": ["render-copy.png"],
            }
        )
        inspection = copy.deepcopy(run["inspections"][0])
        inspection["id"] = "inspection-copy"
        inspection["render_id"] = "render-desktop-default-copy"
        inspection["evidence"] = ["render-copy.png"]
        run["inspections"].append(inspection)
        score = copy.deepcopy(run["scores"][0])
        score["id"] = "score-copy"
        score["inspection_id"] = "inspection-copy"
        score["regions"][0]["render_id"] = "render-desktop-default-copy"
        score["regions"][0]["evidence"] = ["render-copy.png"]
        run["scores"].append(score)
        critique = copy.deepcopy(run["critiques"][0])
        critique["id"] = "critic-copy"
        critique["inspection_id"] = "inspection-copy"
        critique["region_scores"][0]["render_id"] = "render-desktop-default-copy"
        critique["region_scores"][0]["evidence"] = ["render-copy.png"]
        run["critiques"].append(critique)
        run["iterations"] = [
            {
                "id": "cycle-copy",
                "action": "edit",
                "before_render_id": "render-desktop-default",
                "after_render_id": "render-desktop-default-copy",
                "target": "hero CTA",
                "reason": "Make a local correction.",
                "status": "complete",
                "correction_brief": "Correct the CTA while preserving the system.",
                "score_before": 96,
                "score_after": 96,
                "evidence": ["render-copy.png"],
            }
        ]
        run["iteration_budget"] = {"max_cycles": 3, "cycles_used": 1, "remaining_cycles": 2}
        with tempfile.TemporaryDirectory(prefix="design-director-reused-render-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            (root / "render-copy.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script(
                "benchmark_validate.py",
                "validate",
                str(run_path),
                "--kind",
                "run",
                "--benchmark",
                str(benchmark_path),
                "--root",
                str(root),
            )
        self.assertEqual(result.returncode, 2)
        self.assertTrue(any("identical content" in error for error in json.loads(result.stdout)["errors"]))

    def test_render_dimensions_must_match_declared_viewport(self) -> None:
        run = self.run_packet()
        run["renders"][0]["sha256"] = hashlib.sha256(png_bytes(1, 1)).hexdigest()
        with tempfile.TemporaryDirectory(prefix="design-director-wrong-dimensions-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(png_bytes(1, 1))
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["decision"], "BLOCKED")
        self.assertIn("dimensions", scored["gates"]["render"]["reason"])

    def test_render_dpr_must_match_benchmark(self) -> None:
        run = self.run_packet()
        run["renders"][0]["viewport"]["dpr"] = 2
        with tempfile.TemporaryDirectory(prefix="design-director-dpr-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 2)
        self.assertTrue(any("dpr" in error for error in json.loads(result.stdout)["errors"]))

    def test_missing_required_artifact_blocks_the_run(self) -> None:
        run = self.run_packet()
        benchmark = self.benchmark()
        benchmark["expected_artifacts"].append(
            {"id": "quality-report", "kind": "report", "role": "quality evidence", "required": True, "format": "json"}
        )
        with tempfile.TemporaryDirectory(prefix="design-director-missing-artifact-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", benchmark)
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["decision"], "BLOCKED")
        self.assertEqual(scored["gates"]["artifact_completeness"]["status"], "fail")
        self.assertIn("quality-report", scored["gates"]["artifact_completeness"]["reason"])

    def test_region_coverage_is_required_for_the_benchmark_matrix(self) -> None:
        run = self.run_packet()
        run["scores"][0]["regions"] = []
        run["ledger"] = []
        with tempfile.TemporaryDirectory(prefix="design-director-region-coverage-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["gates"]["coverage"]["status"], "blocked")
        coverage = scored["gates"]["coverage"]
        self.assertIn("region hero", coverage["reason"] + " " + " ".join(coverage["evidence"]))

    def test_region_coverage_ignores_observations_from_an_older_render(self) -> None:
        run = self.run_packet()
        run["renders"].append(
            {
                "id": "render-desktop-default-rerender",
                "artifact_id": "implementation",
                "path": "render-rerender.png",
                "viewport": {"width": 1440, "height": 900},
                "state": "default",
                "format": "png",
                "sha256": RENDER_SHA256,
                "captured_at": "2026-08-26T23:01:20Z",
                "evidence": ["render-rerender.png"],
            }
        )
        run["execution"]["evidence"].append("render-rerender.png")
        with tempfile.TemporaryDirectory(prefix="design-director-stale-region-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            (root / "render-rerender.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script(
                "score_visual.py",
                "score",
                str(run_path),
                "--benchmark",
                str(benchmark_path),
                "--root",
                str(root),
            )
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["gates"]["coverage"]["status"], "blocked")
        self.assertIn("region hero", " ".join(scored["gates"]["coverage"]["evidence"]))

    def test_iteration_budget_is_bound_to_recorded_cycles(self) -> None:
        run = self.run_packet()
        run["iteration_budget"]["cycles_used"] = 1
        with tempfile.TemporaryDirectory(prefix="design-director-budget-binding-") as temp_dir:
            path = self.write_json(Path(temp_dir), "run.json", run)
            result = self.run_script("benchmark_validate.py", "validate", str(path), "--kind", "run")
        self.assertEqual(result.returncode, 2)
        self.assertTrue(any("cycles_used" in error for error in json.loads(result.stdout)["errors"]))

    def test_human_override_is_conditional_and_never_aaa(self) -> None:
        run = self.run_packet()
        run["scores"][0]["dimensions"] = {key: 8 for key in run["scores"][0]["dimensions"]}
        run["final_decision"] = {
            "verdict": "CONDITIONAL PASS",
            "reason": "Human accepted a below-threshold result for a time-boxed review.",
            "stop_reason": "human-override",
            "score": 80,
            "evidence_confidence": "HIGH",
            "approved_by": "product-owner",
            "decided_at": "2026-08-26T23:01:10Z",
            "evidence": ["render.png"],
            "render_ids": ["render-desktop-default"],
            "inspection_id": "inspection-001",
            "score_id": "score-001",
            "critique_id": "critic-001",
        }
        run["human_override"] = {
            "scope": "visual polish only",
            "reason": "Launch review is time-boxed.",
            "tradeoff": "Accept one polish cycle of debt.",
            "residual_risk": "The visual system may need another refinement pass.",
            "compensating_evidence": ["render.png"],
            "owner": "product-owner",
            "revalidation_trigger": "Before the next campaign release.",
            "accepted_below_threshold": True,
            "requested_verdict": "CONDITIONAL PASS",
        }
        with tempfile.TemporaryDirectory(prefix="design-director-human-override-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["decision"], "CONDITIONAL PASS")
        self.assertTrue(scored["human_override_applied"])
        self.assertFalse(scored["aaa_candidate"])

    def test_critical_finding_cannot_be_masked_by_high_score(self) -> None:
        run = self.run_packet()
        run["critiques"][0]["findings"]["critical"] = [
            {
                "id": "identity-break",
                "severity": "critical",
                "description": "The approved mark was replaced by an unrelated mark.",
                "location": "header",
                "evidence": ["render.png"],
                "status": "open",
            }
        ]
        run["final_decision"]["verdict"] = "PASS"
        with tempfile.TemporaryDirectory(prefix="design-director-critical-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["overall"], 96.0)
        self.assertEqual(scored["decision"], "FAIL")
        self.assertEqual(scored["blockers"][0]["severity"], "critical")
        self.assertFalse(scored["decision_matches_declaration"])

    def test_inspection_critical_finding_cannot_be_disabled_by_threshold(self) -> None:
        run = self.run_packet()
        run["inspections"][0]["findings"] = [
            {
                "id": "inspection-identity-break",
                "severity": "critical",
                "description": "The inspected identity mark is wrong.",
                "location": "hero",
                "evidence": ["render.png"],
                "status": "open",
            }
        ]
        benchmark = self.benchmark()
        benchmark["quality_threshold"]["block_critical"] = False
        with tempfile.TemporaryDirectory(prefix="design-director-inspection-critical-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", benchmark)
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script(
                "score_visual.py",
                "score",
                str(run_path),
                "--benchmark",
                str(benchmark_path),
                "--root",
                str(root),
            )
        self.assertEqual(result.returncode, 1)
        scored = json.loads(result.stdout)
        self.assertEqual(scored["decision"], "FAIL")
        self.assertEqual(scored["blockers"][0]["severity"], "critical")

    def test_high_finding_requires_revision_even_at_perfect_score(self) -> None:
        run = self.run_packet()
        run["critiques"][0]["findings"]["high"] = [
            {
                "id": "layout-break",
                "severity": "high",
                "description": "The primary action is unreachable at the tested state.",
                "location": "hero",
                "evidence": ["render.png"],
                "status": "open",
            }
        ]
        with tempfile.TemporaryDirectory(prefix="design-director-high-") as temp_dir:
            root = Path(temp_dir)
            (root / "artifact.html").write_text("<main>fixture</main>", encoding="utf-8")
            (root / "render.png").write_bytes(RENDER_PNG)
            benchmark_path = self.write_json(root, "benchmark.json", self.benchmark())
            run_path = self.write_json(root, "run.json", run)
            result = self.run_script("score_visual.py", "score", str(run_path), "--benchmark", str(benchmark_path), "--root", str(root))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["decision"], "FAIL")

    def test_invalid_ledger_viewport_is_rejected(self) -> None:
        ledger = {
            "schema_version": "1",
            "benchmark_id": "B02-saas-landing",
            "run_id": "run-001",
            "entries": [
                {
                    "id": "hero-default",
                    "render_id": "render-default",
                    "region": "hero",
                    "viewport": {"width": 0},
                    "state": "default",
                    "expected": "Readable hero.",
                    "observed": "Unreadable hero.",
                    "severity": "high",
                    "evidence": [],
                    "fix": "Reduce density.",
                    "status": "open",
                }
            ],
        }
        with tempfile.TemporaryDirectory(prefix="design-director-ledger-") as temp_dir:
            path = self.write_json(Path(temp_dir), "ledger.json", ledger)
            result = self.run_script("benchmark_validate.py", "validate", str(path), "--kind", "ledger")
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["valid"])

    def test_pass_critic_without_independence_is_rejected(self) -> None:
        critic = {
            "schema_version": "1",
            "benchmark_id": "B02-saas-landing",
            "run_id": "run-001",
            "inspection_id": "inspection-001",
            "created_at": "2026-08-26T23:00:55Z",
            "reviewer_id": "builder",
            "independent": False,
            "blinded": False,
            "independence": "SELF",
            "verdict": "PASS",
            "overall_score": 96,
            "confidence": "HIGH",
            "evidence_confidence": "HIGH",
            "evidence_quality": "HIGH",
            "findings": {key: [] for key in ("critical", "high", "medium", "low", "polish")},
            "top_corrections": [],
            "constraint_violations": [],
            "evidence_missing": [],
        }
        with tempfile.TemporaryDirectory(prefix="design-director-critic-") as temp_dir:
            path = self.write_json(Path(temp_dir), "critic.json", critic)
            result = self.run_script("benchmark_validate.py", "validate", str(path), "--kind", "critic")
        self.assertEqual(result.returncode, 2)
        errors = json.loads(result.stdout)["errors"]
        self.assertTrue(any("independent" in error for error in errors))

    def test_run_validator_requires_a_benchmark_binding(self) -> None:
        run = self.run_packet()
        with tempfile.TemporaryDirectory(prefix="design-director-unbound-validation-") as temp_dir:
            path = self.write_json(Path(temp_dir), "run.json", run)
            result = self.run_script("benchmark_validate.py", "validate", str(path), "--kind", "run")
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires --benchmark", " ".join(json.loads(result.stdout)["errors"]))

    def test_cli_help_is_available(self) -> None:
        result = self.run_script("score_visual.py", "--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("score", result.stdout)


if __name__ == "__main__":
    unittest.main()
