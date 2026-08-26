#!/usr/bin/env python3
"""Validate package links and required support surfaces without third-party dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from smoke_evals import check_cases


REQUIRED_REFERENCES = {
    "accessibility.md",
    "anti-patterns.md",
    "art-direction.md",
    "banner-design.md",
    "color.md",
    "dashboards.md",
    "degradation-and-evidence.md",
    "design-principles.md",
    "design-systems.md",
    "game-visuals.md",
    "imagegen-direction.md",
    "landing-pages.md",
    "mobile.md",
    "motion.md",
    "quality-rubric.md",
    "responsive-design.md",
    "routing-matrix.md",
    "screenshot-analysis.md",
    "spacing-layout.md",
    "typography.md",
    "visual-brief-contract.md",
    "visual-hierarchy.md",
    "visual-qa.md",
    "workflows.md",
}
LINK_RE = re.compile(r"\]\(([^)]+)\)")


def frontmatter_errors(text: str, expected_name: str) -> list[str]:
    if not text.startswith("---\n"):
        return ["SKILL.md must start with YAML frontmatter"]
    header = text[4 : text.find("\n---", 4)]
    if "\n---" not in text[4:]:
        return ["SKILL.md frontmatter is not closed"]
    required = {"name:", "description:"}
    errors = [f"frontmatter is missing {field}" for field in required if field not in header]
    name_line = next((line for line in header.splitlines() if line.startswith("name:")), "")
    name = name_line.partition(":")[2].strip().strip('"\'')
    if name != expected_name:
        errors.append(f"frontmatter name must be {expected_name!r}")
    return errors


def local_targets(source: Path) -> list[str]:
    targets: list[str] = []
    for raw in LINK_RE.findall(source.read_text(encoding="utf-8")):
        target = raw.strip().split("#", 1)[0]
        if target and not target.startswith(("http://", "https://", "mailto:", "<")):
            targets.append(target)
    return targets


def broken_links(root: Path) -> list[str]:
    return [
        f"{source.relative_to(root)} -> {target}"
        for source in root.rglob("*.md")
        for target in local_targets(source)
        if not (source.parent / target).resolve().is_file()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_root", type=Path)
    args = parser.parse_args()
    root = args.skill_root.resolve()
    errors: list[str] = []
    skill_path = root / "SKILL.md"
    if not skill_path.is_file():
        errors.append("missing SKILL.md")
        skill_text = ""
    else:
        skill_text = skill_path.read_text(encoding="utf-8")
        errors.extend(frontmatter_errors(skill_text, root.name))
        if len(skill_text.splitlines()) > 500:
            errors.append("SKILL.md exceeds the 500-line progressive-disclosure limit")

    references = {path.name for path in (root / "references").glob("*.md")}
    errors.extend(f"missing required reference: references/{name}" for name in sorted(REQUIRED_REFERENCES - references))
    errors.extend(f"broken local link: {link}" for link in broken_links(root))
    errors.extend(
        f"missing helper script: scripts/{name}"
        for name in ("audit_assets.py", "check_contrast.py", "smoke_evals.py")
        if not (root / "scripts" / name).is_file()
    )

    evals_path = root / "evals" / "evals.json"
    if not evals_path.is_file():
        errors.append("missing evals/evals.json")
        cases: list[dict[str, object]] = []
    else:
        try:
            payload = json.loads(evals_path.read_text(encoding="utf-8"))
            cases = payload.get("evals", []) if isinstance(payload, dict) else []
            if not isinstance(cases, list):
                cases = []
                errors.append("evals/evals.json field evals must be an array")
        except (OSError, json.JSONDecodeError) as error:
            cases = []
            errors.append(f"evals/evals.json is invalid: {error}")
    errors.extend(check_cases(cases))

    marker = "[TODO" + ":"
    errors.extend(
        f"TODO placeholder found in {path.relative_to(root)}"
        for path in root.rglob("*")
        if path.is_file() and marker in path.read_text(encoding="utf-8", errors="replace")
    )

    if errors:
        print("Design Director package validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"Design Director package validation passed: {root}")
    print(f"- references: {len(references)}")
    print(f"- evals: {len(cases)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
