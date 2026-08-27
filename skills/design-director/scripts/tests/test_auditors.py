#!/usr/bin/env python3
"""Positive and negative regression tests for visual quality auditors."""

from __future__ import annotations

import json
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]


def png_bytes(width: int, height: int, color_type: int = 6) -> bytes:
    channels = {2: 3, 6: 4}[color_type]
    raw = b"".join(b"\x00" + b"\x00" * width * channels for _ in range(height))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)

    def chunk(name: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + name
            + payload
            + struct.pack(">I", zlib.crc32(name + payload) & 0xFFFFFFFF)
        )

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def jpeg_header(width: int, height: int) -> bytes:
    # SOF0 is enough for the auditor's deterministic frame-header parser.
    sof = b"\xff\xc0" + struct.pack(">H", 8) + b"\x08" + struct.pack(">HH", height, width) + b"\x03"
    return b"\xff\xd8" + sof + b"\xff\xd9"


def webp_vp8x(width: int, height: int, alpha: bool = False) -> bytes:
    payload = bytearray(10)
    if alpha:
        payload[0] |= 0x10
    payload[4:7] = (width - 1).to_bytes(3, "little")
    payload[7:10] = (height - 1).to_bytes(3, "little")
    chunk = b"VP8X" + struct.pack("<I", len(payload)) + bytes(payload)
    return b"RIFF" + struct.pack("<I", 4 + len(chunk)) + b"WEBP" + chunk


def run_script(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(SCRIPTS / name), *args],
        check=False,
        capture_output=True,
        text=True,
    )


class AssetAuditorTests(unittest.TestCase):
    def test_manifest_metadata_and_known_asset_findings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-director-assets-") as temp_dir:
            root = Path(temp_dir)
            (root / "hero.png").write_bytes(png_bytes(8, 4))
            (root / "copy.png").write_bytes(png_bytes(8, 4))
            (root / "photo.jpg").write_bytes(jpeg_header(320, 180))
            (root / "alpha.webp").write_bytes(webp_vp8x(64, 32, alpha=True))
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "assets": [
                            {
                                "path": "hero.png",
                                "role": "hero-image",
                                "provenance": "generated",
                                "min_width": 12,
                                "max_bytes": 1,
                                "expected_aspect_ratio": 2.0,
                                "used": True,
                            },
                            {
                                "path": "copy.png",
                                "role": "variant",
                                "provenance": "generated",
                                "used": False,
                            },
                            {
                                "path": "photo.jpg",
                                "role": "editorial-photo",
                                "provenance": "user-supplied",
                            },
                            {
                                "path": "alpha.webp",
                                "role": "overlay",
                                "provenance": "generated",
                            },
                        ],
                        "generated_paths": ["hero.png", "copy.png"],
                        "used_paths": ["hero.png"],
                    }
                ),
                encoding="utf-8",
            )
            result = run_script("audit_assets.py", str(root), "--manifest", str(manifest), "--strict")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        records = {record["path"]: record for record in json.loads(result.stdout)}
        self.assertEqual(records["hero.png"]["dimensions"], [8, 4])
        self.assertEqual(records["hero.png"]["alpha"], True)
        self.assertEqual(len(records["hero.png"]["sha256"]), 64)
        hero_codes = {issue["code"] for issue in records["hero.png"]["issue_details"]}
        self.assertIn("under_resolution", hero_codes)
        self.assertIn("oversized_file", hero_codes)
        self.assertEqual(records["photo.jpg"]["dimensions"], [320, 180])
        self.assertEqual(records["alpha.webp"]["dimensions"], [64, 32])
        self.assertTrue(records["alpha.webp"]["alpha"])
        copy_codes = {issue["code"] for issue in records["copy.png"]["issue_details"]}
        self.assertIn("duplicate_group", records["copy.png"])
        self.assertIn("unused_asset", copy_codes)
        self.assertIn("suspicious_name", copy_codes)
        self.assertTrue(
            any(
                "duplicate_content"
                in {issue["code"] for issue in record["issue_details"]}
                for record in records.values()
            )
        )

    def test_asset_json_output_and_strict_reject_malformed_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-director-assets-") as temp_dir:
            root = Path(temp_dir)
            (root / "broken.png").write_bytes(b"\x89PNG\r\n\x1a\n")
            output = root / "reports" / "assets.json"
            result = run_script("audit_assets.py", str(root), "--strict", "--json-output", str(output))
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))[0]["format"], "png")

    def test_manifest_reports_missing_declared_asset(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-director-assets-") as temp_dir:
            root = Path(temp_dir)
            (root / "present.svg").write_text(
                "<svg viewBox='0 0 10 10' xmlns='http://www.w3.org/2000/svg'></svg>",
                encoding="utf-8",
            )
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "assets": [
                            {"path": "present.svg", "role": "icon", "provenance": "repository-existing"},
                            {"path": "generated-hero.png", "role": "hero", "provenance": "generated"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            result = run_script("audit_assets.py", str(root), "--manifest", str(manifest), "--strict")
        self.assertEqual(result.returncode, 1)
        records = {record["path"]: record for record in json.loads(result.stdout)}
        self.assertIn("missing_asset", {item["code"] for item in records["generated-hero.png"]["issue_details"]})


class DesignTokenAuditorTests(unittest.TestCase):
    def test_clean_token_source_has_no_high_findings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-director-tokens-") as temp_dir:
            root = Path(temp_dir)
            (root / "tokens.css").write_text(
                """
                :root {
                  --color-brand: #123456;
                  --space-1: 4px;
                  --radius-sm: 4px;
                  --shadow-card: 0 2px 8px rgba(0, 0, 0, .12);
                  --font-body: "Aster";
                }
                .card {
                  color: var(--color-brand);
                  padding: var(--space-1);
                  border-radius: var(--radius-sm);
                  box-shadow: var(--shadow-card);
                  font-family: var(--font-body);
                }
                """,
                encoding="utf-8",
            )
            result = run_script("audit_design_tokens.py", str(root), "--strict")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(
            any(finding["severity"] in {"critical", "high"} for finding in payload["findings"])
        )

    def test_known_token_drift_and_bypass_are_reported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-director-tokens-") as temp_dir:
            root = Path(temp_dir)
            (root / "bad.scss").write_text(
                """
                :root {
                  --color-a: #123456;
                  --color-b: #133457;
                  --color-copy: #123456;
                  --space-1: 4px;
                  --radius-sm: 4px;
                  --shadow-card: 0 2px 8px rgba(0, 0, 0, .12);
                  --font-body: "Aster";
                }
                .a { color: #123456; padding: 5px 7px; margin: 3px 10px; border-radius: 7px; box-shadow: 0 1px 2px #000; font-family: Arial; }
                .b { color: #ffffff; padding: 13px; border-radius: 11px; box-shadow: 0 2px 4px #000; font-family: Georgia; }
                .c { padding: 17px; border-radius: 15px; box-shadow: 0 3px 6px #000; font-family: Verdana; }
                .d { padding: 21px; border-radius: 19px; box-shadow: 0 4px 8px #000; font-family: Tahoma; }
                .e { border-radius: 23px; }
                """,
                encoding="utf-8",
            )
            result = run_script("audit_design_tokens.py", str(root), "--strict")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        codes = {finding["code"] for finding in json.loads(result.stdout)["findings"]}
        self.assertIn("duplicate_color", codes)
        self.assertIn("near_duplicate_color", codes)
        self.assertIn("token_bypass", codes)
        self.assertIn("spacing_drift", codes)
        self.assertIn("radius_drift", codes)
        self.assertIn("shadow_proliferation", codes)
        self.assertIn("typography_drift", codes)


def full_quality_packet() -> dict[str, object]:
    def checks(names: list[str]) -> dict[str, dict[str, object]]:
        return {
            name: {"status": "PASS", "evidence": [f"evidence/{name}.json"]}
            for name in names
        }

    return {
        "schema_version": 1,
        "evidence": {
            "accessibility": checks(
                [
                    "keyboard",
                    "focus",
                    "semantics",
                    "names",
                    "errors",
                    "non_color",
                    "reduced_motion",
                    "touch_targets",
                    "zoom_reflow",
                    "contrast",
                ]
            ),
            "performance": {
                "lcp": {"value_ms": 1800, "status": "PASS", "evidence": ["web-vitals.json"]},
                "cls": {"value": 0.03, "status": "PASS", "evidence": ["web-vitals.json"]},
                **checks(["responsive_images", "font_loading", "oversized_media"]),
            },
            "typography": checks(
                [
                    "heading_hierarchy",
                    "measure",
                    "line_height",
                    "fallback",
                    "numeric_alignment",
                    "mobile_scale",
                ]
            ),
            "copy_stress": checks(
                ["short", "long", "empty", "large", "localized"]
            ),
        },
        "critical_blockers": [],
    }


class QualityGateTests(unittest.TestCase):
    def test_complete_evidence_packet_passes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-director-gates-") as temp_dir:
            packet = Path(temp_dir) / "packet.json"
            packet.write_text(json.dumps(full_quality_packet()), encoding="utf-8")
            result = run_script("quality_gates.py", str(packet))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = json.loads(result.stdout)
        self.assertTrue(output["pass"])
        self.assertEqual(output["status"], "PASS")
        self.assertTrue(all(gate["status"] == "PASS" for gate in output["gates"]))

    def test_missing_evidence_is_blocked_not_pass(self) -> None:
        packet_data = full_quality_packet()
        evidence = packet_data["evidence"]
        assert isinstance(evidence, dict)
        accessibility = evidence["accessibility"]
        assert isinstance(accessibility, dict)
        del accessibility["focus"]
        with tempfile.TemporaryDirectory(prefix="design-director-gates-") as temp_dir:
            packet = Path(temp_dir) / "packet.json"
            packet.write_text(json.dumps(packet_data), encoding="utf-8")
            result = run_script("quality_gates.py", str(packet))
        self.assertEqual(result.returncode, 1)
        output = json.loads(result.stdout)
        self.assertEqual(output["status"], "BLOCKED")
        access_gate = next(gate for gate in output["gates"] if gate["gate"] == "accessibility")
        self.assertIn("focus", access_gate["missing"])

    def test_critical_failure_cannot_pass(self) -> None:
        packet_data = full_quality_packet()
        evidence = packet_data["evidence"]
        assert isinstance(evidence, dict)
        accessibility = evidence["accessibility"]
        assert isinstance(accessibility, dict)
        accessibility["keyboard"] = {
            "status": "FAIL",
            "critical": True,
            "evidence": ["keyboard-failure.json"],
        }
        with tempfile.TemporaryDirectory(prefix="design-director-gates-") as temp_dir:
            packet = Path(temp_dir) / "packet.json"
            packet.write_text(json.dumps(packet_data), encoding="utf-8")
            result = run_script("quality_gates.py", str(packet))
        self.assertEqual(result.returncode, 1)
        output = json.loads(result.stdout)
        self.assertEqual(output["status"], "FAIL")
        self.assertTrue(output["critical_blockers"])

    def test_scoped_not_applicable_requires_and_accepts_rationale(self) -> None:
        packet_data = full_quality_packet()
        evidence = packet_data["evidence"]
        assert isinstance(evidence, dict)
        evidence["copy_stress"] = {
            "status": "NOT_APPLICABLE",
            "reason": "This surface contains no user-authored content.",
            "evidence": ["scope-decision.md"],
        }
        with tempfile.TemporaryDirectory(prefix="design-director-gates-") as temp_dir:
            packet = Path(temp_dir) / "packet.json"
            packet.write_text(json.dumps(packet_data), encoding="utf-8")
            result = run_script("quality_gates.py", str(packet))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        output = json.loads(result.stdout)
        self.assertTrue(output["pass"])
        copy_gate = next(gate for gate in output["gates"] if gate["gate"] == "copy_stress")
        self.assertEqual(copy_gate["status"], "NOT_APPLICABLE")

    def test_root_mode_rejects_missing_local_evidence(self) -> None:
        packet_data = full_quality_packet()
        with tempfile.TemporaryDirectory(prefix="design-director-gates-root-") as temp_dir:
            root = Path(temp_dir)
            packet = root / "packet.json"
            packet.write_text(json.dumps(packet_data), encoding="utf-8")
            result = run_script("quality_gates.py", str(packet), "--root", str(root))
        self.assertEqual(result.returncode, 1)
        output = json.loads(result.stdout)
        self.assertEqual(output["status"], "BLOCKED")
        self.assertTrue(any(gate["evidence_missing"] for gate in output["gates"]))

    def test_root_mode_rejects_empty_local_evidence(self) -> None:
        packet_data = full_quality_packet()
        evidence = packet_data["evidence"]
        assert isinstance(evidence, dict)
        accessibility = evidence["accessibility"]
        assert isinstance(accessibility, dict)
        accessibility["keyboard"] = {"status": "PASS", "evidence": ["empty.json"]}
        with tempfile.TemporaryDirectory(prefix="design-director-gates-empty-") as temp_dir:
            root = Path(temp_dir)
            (root / "empty.json").write_bytes(b"")
            (root / "web-vitals.json").write_text("{}", encoding="utf-8")
            (root / "evidence").mkdir()
            for gate in evidence.values():
                if not isinstance(gate, dict):
                    continue
                for detail in gate.values():
                    if isinstance(detail, dict) and isinstance(detail.get("evidence"), list):
                        for path in detail["evidence"]:
                            if isinstance(path, str) and path.startswith("evidence/"):
                                (root / path).write_text("observed", encoding="utf-8")
            packet = root / "packet.json"
            packet.write_text(json.dumps(packet_data), encoding="utf-8")
            result = run_script("quality_gates.py", str(packet), "--root", str(root))
        self.assertEqual(result.returncode, 1)
        output = json.loads(result.stdout)
        access_gate = next(gate for gate in output["gates"] if gate["gate"] == "accessibility")
        self.assertIn("keyboard", access_gate["evidence_missing"])

    def test_root_mode_does_not_treat_remote_uri_as_local_evidence(self) -> None:
        packet_data = full_quality_packet()
        evidence = packet_data["evidence"]
        assert isinstance(evidence, dict)
        accessibility = evidence["accessibility"]
        assert isinstance(accessibility, dict)
        accessibility["keyboard"] = {
            "status": "PASS",
            "evidence": ["https://example.invalid/keyboard.json"],
        }
        with tempfile.TemporaryDirectory(prefix="design-director-gates-remote-") as temp_dir:
            root = Path(temp_dir)
            packet = root / "packet.json"
            packet.write_text(json.dumps(packet_data), encoding="utf-8")
            result = run_script("quality_gates.py", str(packet), "--root", str(root))
        self.assertEqual(result.returncode, 1)
        output = json.loads(result.stdout)
        self.assertEqual(output["status"], "BLOCKED")
        access_gate = next(gate for gate in output["gates"] if gate["gate"] == "accessibility")
        self.assertIn("keyboard", access_gate["evidence_missing"])

    def test_metric_value_overrides_conflicting_status(self) -> None:
        packet_data = full_quality_packet()
        evidence = packet_data["evidence"]
        assert isinstance(evidence, dict)
        performance = evidence["performance"]
        assert isinstance(performance, dict)
        performance["lcp"] = {
            "status": "PASS",
            "value_ms": 4000,
            "evidence": ["web-vitals.json"],
        }
        with tempfile.TemporaryDirectory(prefix="design-director-gates-metric-") as temp_dir:
            packet = Path(temp_dir) / "packet.json"
            packet.write_text(json.dumps(packet_data), encoding="utf-8")
            result = run_script("quality_gates.py", str(packet))
        self.assertEqual(result.returncode, 1)
        output = json.loads(result.stdout)
        performance_gate = next(gate for gate in output["gates"] if gate["gate"] == "performance")
        lcp = performance_gate["checks"]["lcp"]
        self.assertEqual(lcp["status"], "FAIL")
        self.assertTrue(lcp["status_conflict"])

    def test_numeric_non_metric_and_invalid_cls_are_not_accepted(self) -> None:
        packet_data = full_quality_packet()
        evidence = packet_data["evidence"]
        assert isinstance(evidence, dict)
        accessibility = evidence["accessibility"]
        assert isinstance(accessibility, dict)
        accessibility["keyboard"] = 1
        performance = evidence["performance"]
        assert isinstance(performance, dict)
        performance["cls"] = {"value": -1, "status": "PASS", "evidence": ["web-vitals.json"]}
        with tempfile.TemporaryDirectory(prefix="design-director-gates-metric-domain-") as temp_dir:
            packet = Path(temp_dir) / "packet.json"
            packet.write_text(json.dumps(packet_data), encoding="utf-8")
            result = run_script("quality_gates.py", str(packet))
        self.assertEqual(result.returncode, 1)
        output = json.loads(result.stdout)
        self.assertEqual(output["status"], "FAIL")
        access_gate = next(gate for gate in output["gates"] if gate["gate"] == "accessibility")
        self.assertIn("keyboard", access_gate["missing"])
        performance_gate = next(gate for gate in output["gates"] if gate["gate"] == "performance")
        self.assertEqual(performance_gate["checks"]["cls"]["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
