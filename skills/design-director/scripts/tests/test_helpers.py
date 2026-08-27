#!/usr/bin/env python3
"""Small regression checks for the deterministic helper scripts."""

from __future__ import annotations

import json
import struct
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ElementTree
import zlib
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1]


def solid_png(width: int, height: int, rgba: tuple[int, int, int, int]) -> bytes:
    raw = b"".join(b"\x00" + bytes(rgba) * width for _ in range(height))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)

    def chunk(name: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + name
            + payload
            + struct.pack(">I", zlib.crc32(name + payload) & 0xFFFFFFFF)
        )

    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


class HelperScriptTests(unittest.TestCase):
    def run_script(self, name: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-B", str(SCRIPTS / name), *args],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_contrast_accepts_dark_on_light(self) -> None:
        result = self.run_script(
            "check_contrast.py",
            "--foreground",
            "#101828",
            "--background",
            "#F8F5EF",
        )
        self.assertEqual(result.returncode, 0)
        self.assertTrue(json.loads(result.stdout)["pass"])

    def test_contrast_rejects_known_bad_pair(self) -> None:
        result = self.run_script(
            "check_contrast.py",
            "--foreground",
            "#777777",
            "--background",
            "#FFFFFF",
        )
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["pass"])

    def test_package_contract_passes(self) -> None:
        package_root = SCRIPTS.parent
        result = self.run_script("validate_package.py", str(package_root))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_eval_catalog_smoke_passes(self) -> None:
        package_root = SCRIPTS.parent
        result = self.run_script("smoke_evals.py", str(package_root / "evals" / "evals.json"))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_asset_audit_decodes_package_icon(self) -> None:
        package_root = SCRIPTS.parent.parent.parent
        result = self.run_script("audit_assets.py", str(package_root / "assets"), "--strict")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_package_icon_is_well_formed_svg(self) -> None:
        package_root = SCRIPTS.parent.parent.parent
        root = ElementTree.parse(package_root / "assets" / "design-director.svg").getroot()
        self.assertTrue(root.tag.endswith("svg"))

    def test_asset_audit_rejects_malformed_png_and_svg(self) -> None:
        truncated_png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + b"\x00" * 13
        invalid_crc_png = (
            b"\x89PNG\r\n\x1a\n"
            + struct.pack(">I", 13)
            + b"IHDR"
            + struct.pack(">II", 10, 10)
            + b"\x08\x06\x00\x00\x00"
            + b"\x00\x00\x00\x00"
        )
        with tempfile.TemporaryDirectory(prefix="design-director-assets-") as temp_dir:
            root = Path(temp_dir)
            (root / "truncated.png").write_bytes(truncated_png)
            (root / "invalid-crc.png").write_bytes(invalid_crc_png)
            (root / "broken.svg").write_text("<svg viewBox='0 0 10 10'>", encoding="utf-8")
            result = self.run_script("audit_assets.py", str(root), "--strict")
        self.assertEqual(result.returncode, 1)
        records = json.loads(result.stdout)
        self.assertTrue(all(record["issues"] for record in records))

    def test_visual_compare_reports_identical_and_changed_native_pngs(self) -> None:
        with tempfile.TemporaryDirectory(prefix="design-director-compare-") as temp_dir:
            root = Path(temp_dir)
            reference = root / "reference.png"
            same = root / "same.png"
            changed = root / "changed.png"
            reference.write_bytes(solid_png(4, 3, (10, 20, 30, 255)))
            same.write_bytes(solid_png(4, 3, (10, 20, 30, 255)))
            changed.write_bytes(solid_png(4, 3, (240, 20, 30, 255)))
            identical = self.run_script("compare_visual.py", str(reference), str(same))
            different = self.run_script("compare_visual.py", str(reference), str(changed))
        self.assertEqual(identical.returncode, 0, identical.stdout + identical.stderr)
        self.assertEqual(json.loads(identical.stdout)["status"], "PASS")
        self.assertEqual(json.loads(identical.stdout)["changed_pixel_ratio"], 0.0)
        self.assertEqual(different.returncode, 1, different.stdout + different.stderr)
        different_payload = json.loads(different.stdout)
        self.assertEqual(different_payload["status"], "DIFF")
        self.assertGreater(different_payload["changed_pixel_ratio"], 0)


if __name__ == "__main__":
    unittest.main()
