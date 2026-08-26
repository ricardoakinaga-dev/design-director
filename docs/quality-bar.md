# Design Director Quality Bar v1

This is the frozen acceptance bar used for implementation and independent review. A score never cancels a failed required gate.

| ID | Dimension | Required target | Evidence | Priority |
| --- | --- | --- | --- | --- |
| DD-1 | Package integrity | Manifest, skill frontmatter, references, scripts, assets, and eval JSON are structurally valid; no broken local links or TODO placeholders | Official/local validators plus `validate_package.py` | critical |
| DD-2 | Routing | Visual/design requests activate the skill; pure backend/logic requests are explicitly out of scope; asset medium is selected correctly | SKILL routing table, positive/negative evals, direct prompt inspection | critical |
| DD-3 | Composition | Existing specialist capabilities are invoked by role and boundary, without duplicated imagegen/frontend/Figma/game instructions | Composition section, research record, adversarial critique | high |
| DD-4 | Design reasoning | Briefs become a strategy, art direction, token plan, asset plan, implementation contract, and measurable DoD | Forward prompts and artifact inspection | critical |
| DD-5 | Identity safety | References are classified; identity references are locked; edits preserve explicit must-preserve constraints; no invented brand/product/legal/price claims | Identity-lock eval and reference protocol | critical |
| DD-6 | Visual quality | Critique covers hierarchy, typography, layout, color, consistency, usability, responsiveness, accessibility, brand, and polish; anti-slop checks are explicit | Quality rubric, anti-patterns, independent critic | high |
| DD-7 | Visual QA | Runnable UI work uses real render/screenshot/inspection at 375, 768, and 1440 when applicable, then fixes and rerenders | Visual QA reference and QA handoff | critical |
| DD-8 | Accessibility | Contrast, semantics, keyboard/focus, names/labels, alt, reduced motion, touch targets, and responsive readability are checked when applicable | Accessibility reference and contrast script | high |
| DD-9 | Graceful degradation | Missing imagegen/browser/Figma/reference/font, corrupt assets, failed generation, or absent API key produce an actionable fallback and honest limitation | Degradation matrix and adversarial evals | high |
| DD-10 | Maintainability | Semantic tokens, stable asset names/provenance, existing design-system preservation, concise references, and no redundant specialist copies | Static inspection and package map | medium |
| DD-11 | Evaluation | At least eight forward prompts cover banner, dashboard, landing, SVG medium choice, identity lock, screenshot reconstruction, hero-only scope, and a Python/backend negative | `evals/evals.json` plus prompt runs | high |
| DD-12 | Handoff | Final report includes architecture, files, integrations, tests, fixed problems, limitations, installation/use, examples, and final validation | README plus final Gauntlet report | high |

## Score rubric

For a concrete design artifact, score ten dimensions from 0–10: hierarchy, typography, spacing/layout, color, consistency, usability, responsiveness, accessibility, brand/identity, and polish. With ten dimensions, the sum is already a 0–100 heuristic score. If fewer dimensions apply, report `sum / applicable dimensions × 10` and the denominator. If an average is shown, multiply it by ten exactly once. The target for important work is at least 90, but required evidence gates still stand independently.

## Round protocol

Use `GOAL → BAR → DECOMPOSE → BUILD → RUN → INSPECT → CRITIQUE → SCORE → FIX → RETEST`. A fresh read-only critic must judge the integrated artifact after material changes. Record the largest meaningful gap first; do not polish around a broken route, missing identity lock, absent visual evidence, or failed accessibility gate.

## Applicability

The bar is adaptive. A pure SVG icon request may stop after medium selection, vector inspection, contrast/accessibility, and package checks. A live frontend redesign additionally requires browser render, interaction, responsive, and visual QA evidence. A design-only brief can pass its strategy/handoff gates while clearly marking runtime render checks as not applicable or not run.
