# Validation record

Run date: 2026-08-26. This record is evidence for the package itself; it is not a claim that a product UI was rendered.

## Gauntlet Result

**Goal**

Deliver a portable, skill-only `design-director` plugin that directs visual product work without duplicating specialist tool ownership.

**Quality Bar**

DD-1 structural integrity: PASS. DD-3/4/5/10 static contracts: PASS. DD-2/8/9/11 are partially evidenced. DD-6/7 are not applicable to this package because no runnable product UI, reference screenshot, Figma file, or generated raster asset is included.

**Rounds**

Discovery/research → package build → static checks → independent critique → targeted fixes → integrated checks → fresh final critique.

**Major gaps discovered**

- The workspace contains a skill package, not a runnable product surface; rendered visual QA, browser interaction, Figma inspection, and raster-generation behavior cannot be proven here.
- The first official `plugin-eval` benchmark was blocked before model execution by an external `max` reasoning-effort/model mismatch. A retry with an announced model remained without output and was stopped after the process showed no progress; its logs remain in the disposable `/tmp` run directory.

**Major improvements**

- Added a skill-only manifest, direct-skill metadata, 24 focused references, 20 forward evals, deterministic package/eval/contrast/asset checks, worked examples, and a local marketplace template.
- Added identity-lock, medium-selection, specialist-boundary, anti-slop, responsive, accessibility, degradation, and visual-QA contracts.
- Corrected the 0–100 score formula, documented metadata precedence and marketplace auth semantics, and made strict asset auditing reject empty/undecodable files.

**Verification performed**

- Official plugin validator: PASS.
- Official skill validator: PASS.
- Local package validator: PASS (`24` references, `20` evals).
- Eval smoke catalog: PASS (`20/20` required IDs).
- Helper tests: PASS (`7` tests, including truncated PNG, invalid-CRC PNG, and malformed SVG rejection).
- Contrast known-good pair: PASS (`16.31:1`). Known-bad pair: correctly rejected (`4.48:1` against `4.5`).
- SVG XML parse and strict asset audit: PASS; empty/malformed/undecodable fixtures: correctly rejected.
- Fresh `codex exec` forward test with `$design-director`: PASS for automatic discovery and landing-page routing; the model selected HTML/CSS, preserved no-claims/no-gradient constraints, and marked absent render evidence blocked.
- Fresh read-only positive/negative prompts: PASS for banner medium selection and SQL/backend non-activation.
- Static `plugin-eval analyze`: completed with a conservative budget warning because it sums all deferred references/evals/helpers; this is an upper-bound heuristic for a progressively loaded package, not a runtime failure.

**Final Critic**

Fresh read-only integration critique performed after the CRC-fixture and metadata-documentation fixes: `CONDITIONAL PASS`, with no mandatory correction. The critic confirmed the malformed-asset coverage, `dd-19` boundary, score normalization, metadata/`ON_INSTALL` documentation, and honest runtime labels. Runtime visual criteria remain explicitly `NOT RUN`/`BLOCKED` because the package intentionally contains no application artifact.

**Remaining limitations**

No live Browser/IAB, Figma, image-generation, frontend implementation, game runtime, data-visualization, reference-image, font, or screen-reader run was available in this package workspace. Install the optional specialist capabilities and run their real artifact checks for those claims.

**Final verdict**

CONDITIONAL PASS — package and routing contracts are validated; product-level visual quality and external specialist integration require a real target artifact and available capabilities.
