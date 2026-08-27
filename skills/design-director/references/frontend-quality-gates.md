# Frontend quality gates

This reference defines the evidence contract for frontend visual quality. It
is complementary to the visual rubric and responsive guidance: a source scan
can find risks, but it cannot replace a rendered artifact, interaction pass,
or independent critique.

## Gate sequence

Use the following order for an executable interface:

~~~text
run app
→ open target
→ set viewport and state
→ capture screenshot and interaction evidence
→ audit assets/tokens
→ produce this packet
→ run quality_gates.py
→ record failures in the visual ledger
~~~

"quality_gates.py" consumes evidence. It does not launch a browser, measure
Core Web Vitals, operate a keyboard, or run a screen reader. Those activities
belong to the available Browser/IAB or project test runner. If that capability
is unavailable, record "NOT_RUN" or "BLOCKED"; never convert the absence into a
PASS.

For reference/capture comparison, use the dependency-free PNG primitive after
the host captures both files:

~~~bash
python3 -B skills/design-director/scripts/compare_visual.py \
  reference.png current.png --pretty
~~~

It rejects undecodable images and native dimension mismatches, then reports
changed-pixel ratio, mean absolute error, maximum channel error, and pixel
similarity. These metrics support the ledger; they do not replace semantic
inspection or independent visual criticism.

## Frontend evidence packet

The command accepts a JSON object with an optional "evidence" wrapper:

~~~json
{
  "schema_version": 1,
  "target": "checkout",
  "environment": {
    "url": "http://localhost:4173/checkout",
    "commit": "working-tree",
    "browser": "record the actual browser"
  },
  "evidence": {
    "accessibility": {
      "keyboard": {"status": "PASS", "evidence": ["keyboard-run.json"]},
      "focus": {"status": "PASS", "evidence": ["focus-visible.png"]},
      "semantics": {"status": "PASS", "evidence": ["axe-or-manual-report"]},
      "names": {"status": "PASS", "evidence": ["accessible-names.json"]},
      "errors": {"status": "PASS", "evidence": ["error-recovery.png"]},
      "non_color": {"status": "PASS", "evidence": ["state-cues.png"]},
      "reduced_motion": {"status": "PASS", "evidence": ["reduced-motion.png"]},
      "touch_targets": {"status": "PASS", "evidence": ["mobile-targets.png"]},
      "zoom_reflow": {"status": "PASS", "evidence": ["200-percent.png"]},
      "contrast": {"status": "PASS", "evidence": ["contrast-report.json"]}
    },
    "performance": {
      "lcp": {
        "value_ms": 2100,
        "status": "PASS",
        "evidence": ["web-vitals.json"]
      },
      "cls": {
        "value": 0.04,
        "status": "PASS",
        "evidence": ["web-vitals.json"]
      },
      "responsive_images": {"status": "PASS", "evidence": ["source-audit.json"]},
      "font_loading": {"status": "PASS", "evidence": ["font-loading.json"]},
      "oversized_media": {"status": "PASS", "evidence": ["asset-audit.json"]}
    },
    "typography": {
      "heading_hierarchy": {"status": "PASS", "evidence": ["heading-report.json"]},
      "measure": {"status": "PASS", "evidence": ["wide-and-narrow.png"]},
      "line_height": {"status": "PASS", "evidence": ["type-inspection.json"]},
      "fallback": {"status": "PASS", "evidence": ["font-fallback.png"]},
      "numeric_alignment": {"status": "PASS", "evidence": ["table.png"]},
      "mobile_scale": {"status": "PASS", "evidence": ["mobile-type.png"]}
    },
    "copy_stress": {
      "short": {"status": "PASS", "evidence": ["short-copy.png"]},
      "long": {"status": "PASS", "evidence": ["long-copy.png"]},
      "empty": {"status": "PASS", "evidence": ["empty-state.png"]},
      "large": {"status": "PASS", "evidence": ["large-number.png"]},
      "localized": {"status": "PASS", "evidence": ["localized-copy.png"]}
    }
  },
  "critical_blockers": []
}
~~~

The four sections and their required checks are:

| Gate | Required evidence |
| --- | --- |
| Accessibility | keyboard, focus, semantics, names, errors, non-color cues, reduced motion, touch targets, zoom/reflow, contrast |
| Performance | LCP, CLS, responsive images, font loading, oversized media |
| Typography | heading hierarchy, measure, line-height, fallback, numeric alignment, mobile scale |
| Copy stress | short, long, empty, large-number, and localized content |

Each observed "PASS", "WARN", or "FAIL" needs a non-empty "evidence" value.
Evidence may be a path, URL, report identifier, screenshot, or a list of
those. With `--root`, local path evidence must exist; the evaluator does not
download or verify remote URLs. A check with no recognized status, no evidence, or no section is
"BLOCKED". "NOT_RUN" is also blocking. Use "NOT_APPLICABLE" only for a scoped
section with a written rationale and evidence of why it does not apply.

The default performance thresholds are LCP ≤ 2500 ms and CLS ≤ 0.10. Supply a
packet-level "thresholds" object when a product has a documented budget:

~~~json
{"thresholds": {"lcp_good_ms": 1800, "cls_good": 0.05}}
~~~

## Result semantics

The evaluator returns one result per gate and an overall status:

| Status | Meaning |
| --- | --- |
| "PASS" | Every applicable check passed with evidence and no blocker exists |
| "CONDITIONAL" | Evidence exists but one or more checks are warnings; this is not a release PASS |
| "FAIL" | A required check failed or a critical blocker was declared |
| "BLOCKED" | Evidence is missing, unavailable, or malformed |
| "NOT_APPLICABLE" | A complete section was explicitly scoped out with rationale |

The CLI exits 0 only for overall "PASS". A critical blocker cannot be
averaged away. The output includes limitations so downstream reports do not
mistake this deterministic gate for a complete usability or visual judgment.

Run it with:

~~~bash
python3 -B skills/design-director/scripts/quality_gates.py frontend-packet.json
python3 -B skills/design-director/scripts/quality_gates.py frontend-packet.json \
  --json-output artifacts/frontend-gates.json
python3 -B skills/design-director/scripts/quality_gates.py frontend-packet.json \
  --root . --json-output artifacts/frontend-gates.json
~~~

Use `--root` in CI or a local verification run when evidence strings are
repository-relative paths. In root mode, a claimed PASS/WARN/FAIL whose
evidence file is absent becomes `BLOCKED`; URLs remain explicitly external and
are not downloaded by this dependency-free evaluator. Without `--root`, the
tool checks that evidence was declared but cannot verify local existence.

## Asset audit contract

"audit_assets.py" keeps its original interface:

~~~bash
python3 -B skills/design-director/scripts/audit_assets.py assets --strict
~~~

Supported local parsers are PNG, SVG, JPEG, GIF, WebP, and a conservative
AVIF/ISO-BMFF header reader. The report includes:

- dimensions and aspect ratio when a supported header/parser proves them;
- byte size, extension, detected parser, SHA-256, and alpha state;
- duplicate groups and suspicious export names;
- configured oversized and under-resolution findings;
- role, provenance, and usage data when a manifest is supplied.

For a repository-relative manifest, run the audit from the repository root so
manifest paths and report paths share the same coordinate system:

~~~bash
python3 -B skills/design-director/scripts/audit_assets.py . \
  --manifest benchmarks/fixtures/assets.json --strict
~~~

Unknown or malformed data is reported as unknown/uninspectable; the auditor
does not infer dimensions or alpha from the extension. Use "--max-bytes 0" to
disable the default 10 MiB limit, or pass "--min-width", "--min-height", and
"--manifest" for a role-specific budget.

Manifest example:

~~~json
{
  "assets": [
    {
      "path": "hero.webp",
      "role": "hero-image",
      "provenance": "generated",
      "min_width": 1440,
      "min_height": 720,
      "max_bytes": 500000,
      "expected_aspect_ratio": 2.0,
      "aspect_tolerance": 0.03,
      "used": true
    }
  ],
  "generated_paths": ["hero.webp", "unused-variant.png"],
  "used_paths": ["hero.webp"]
}
~~~

The manifest is the source of truth for role and provenance. "used_paths" and
"generated_paths", or an explicit per-asset "used: false", are required before
unused generated assets can be reported. Without them the auditor does not
claim to know whether an asset is referenced at runtime.

Optional report output:

~~~bash
python3 -B skills/design-director/scripts/audit_assets.py assets \
  --manifest assets.json --json-output artifacts/assets.json
~~~

## Token audit contract

"audit_design_tokens.py" scans CSS, SCSS, JSON, JS, JSX, TS, and TSX source.
It reports structured severity findings for:

- duplicate and near-duplicate token colors;
- raw color/spacing/radius/shadow/typography values bypassing declared tokens;
- spacing rhythm drift, radius drift, shadow proliferation, and typography drift;
- invalid JSON or unreadable supported source.

Use:

~~~bash
python3 -B skills/design-director/scripts/audit_design_tokens.py src
python3 -B skills/design-director/scripts/audit_design_tokens.py src --strict \
  --json-output artifacts/token-audit.json
~~~

"--strict" fails on high or critical findings. The scanner uses conservative
regular expressions rather than a CSS or JavaScript AST. It cannot resolve
cascade, imports, aliases, generated styles, computed values, or runtime
component boundaries. Near-duplicate color distance is Euclidean RGB, not
perceptual Delta E. Treat findings as review signals and record intentional
exceptions in the design-system evidence.

## Evidence boundary

These gates answer “did the declared checks produce sufficient evidence?” They
do not answer “is the visual direction excellent?” The latter still requires
the rendered screenshot/state matrix, applicable quality dimensions, region
ledger, and a fresh read-only independent critic. Never label an interface
pixel-perfect, faithful, visually complete, or production-ready from a source
scan alone.
