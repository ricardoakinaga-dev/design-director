#!/usr/bin/env python3
"""Run deterministic coverage checks for the forward-eval catalog.

This checks the test specification itself; it does not pretend to replace a
model run, tool trace, browser render, image inspection, or independent critic.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REQUIRED_IDS = {
    "dd-01-banner-positive",
    "dd-02-python-negative",
    "dd-03-backend-negative-pack",
    "dd-04-dashboard-redesign",
    "dd-05-saas-landing",
    "dd-06-svg-medium-negative",
    "dd-07-identity-lock",
    "dd-08-screenshot-reconstruction",
    "dd-09-hero-only-scope",
    "dd-10-audit-positive",
    "dd-11-native-image-route",
    "dd-12-fidelity-override",
    "dd-13-game-routing",
    "dd-14-figma-routing",
    "dd-15-ambiguous-context",
    "dd-16-browser-blocked",
    "dd-17-mobile-accessibility",
    "dd-18-visual-regression-positive",
    "dd-19-data-visualization-boundary",
    "dd-20-package-handoff",
}


def load_cases(path: Path) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    cases = payload.get("evals", []) if isinstance(payload, dict) else []
    return cases if isinstance(cases, list) else []


def check_cases(cases: list[dict[str, object]]) -> list[str]:
    errors: list[str] = []
    ids = {case.get("id") for case in cases if isinstance(case, dict)}
    errors.extend(f"missing required eval: {case_id}" for case_id in sorted(REQUIRED_IDS - ids))
    valid_cases = [case for case in cases if isinstance(case, dict)]
    if not any(case.get("expected_skill") == "design-director" for case in valid_cases):
        errors.append("no positive design-director eval exists")
    if not any(case.get("expected_skill") is None for case in valid_cases):
        errors.append("no negative boundary eval exists")
    for case in valid_cases:
        for field in ("id", "prompt", "expected_output", "expectations"):
            if not case.get(field):
                errors.append(f"{case.get('id', 'unknown')} missing {field}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evals", type=Path)
    args = parser.parse_args()
    try:
        cases = load_cases(args.evals)
        errors = check_cases(cases)
    except (OSError, json.JSONDecodeError, TypeError) as error:
        print(json.dumps({"status": "fail", "error": str(error)}, indent=2))
        return 1
    result = {"status": "pass" if not errors else "fail", "case_count": len(cases), "errors": errors}
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
