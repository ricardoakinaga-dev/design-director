# Design Director Quality Bar v2

This is the frozen acceptance bar used for implementation and independent review. Version 1's package, routing, ownership, identity, accessibility, degradation and handoff criteria remain; v2 adds executable visual-result evidence. A score never cancels a failed required gate.

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

## Evidence-driven visual gates

For a benchmarked artifact, the result must be traceable as:

`benchmark → input/reference → artifact → render → inspection → region/state ledger → critic → score → iteration → final decision`.

The machine-readable contracts live under [`benchmarks/`](../benchmarks/), and the portable validators live under `skills/design-director/scripts/`. A missing or stale link is `NOT_RUN`/`BLOCKED`, never an implicit pass. The host may provide Browser/IAB, Playwright, image generation, Figma, game runtime or another renderer; this package does not pretend to provide those capabilities.

Applicable visual gates:

| ID | Gate | Required evidence | Failure rule |
| --- | --- | --- | --- |
| VQ-1 | Benchmark contract | Valid benchmark spec, resolved inputs/references, explicit constraints, states, viewports, threshold and iteration budget | Invalid or string-only benchmark fails |
| VQ-2 | Artifact/render | Every required artifact is bound and produced; screenshot render is a locally decodable visual image whose dimensions/state match the benchmark and current inspection record | Missing artifact, HTML/PDF placeholder, fake/incorrect-size render or stale inspection blocks visual PASS |
| VQ-3 | Independent critic | Read-only critic packet with typed blind inputs, distinct builder/reviewer provenance, packet digest, independence class, confidence and prioritized findings | Builder rationale or self-review cannot satisfy independent critique |
| VQ-4 | Region/state QA | Every applicable viewport/state/region triple is observed with evidence | A missing triple or material regional blocker overrides a reassuring global average |
| VQ-5 | Quality gates | Applicable dimensions, normalized weights, evidence confidence, blockers and stop reason | A score cannot override Critical or unresolved High findings |
| VQ-6 | Iteration | Reconciled budget, edit/regenerate decision, correction brief, before/after scores, new render and fresh critique after material change | Generation 1 is not automatically accepted for important visuals |
| VQ-7 | Identity/provenance | Identity Lock, reference roles, asset role/provenance and acceptance checks | Identity violation or unknown provenance blocks acceptance when material |
| VQ-8 | Frontend gates | Accessibility, performance, typography, copy-stress and responsive evidence where applicable | Missing runtime evidence remains explicit, not upgraded by source inspection |

## Score rubric

For a concrete design artifact, score ten dimensions from 0–10: hierarchy, typography, spacing/layout, color, consistency, usability, responsiveness, accessibility, brand/identity, and polish. With ten dimensions, the sum is already a 0–100 heuristic score. If fewer dimensions apply, report `sum / applicable dimensions × 10` and the denominator. If an average is shown, multiply it by ten exactly once. The target for important work is at least 90, but required evidence gates still stand independently.

Add only relevant dimensions for the surface: reference fidelity, asset quality, interaction quality, information density and product specificity. Normalize configured weights across applicable dimensions; do not sum irrelevant dimensions or allow their absence to inflate a result. Report `evidence_confidence` separately:

- `HIGH`: current render(s), relevant interaction/state evidence and reference comparison when required, plus separated critique.
- `MEDIUM`: current artifact inspection and partial render/interaction evidence, with a stated gap.
- `LOW`: source/code or plan inspection without enough rendered evidence.

Quality bands are heuristic: `<70 FAIL`, `70–79 MAJOR REVISION`, `80–89 POLISH REQUIRED`, `90–94 PASS`, `95+ REFERENCE QUALITY CANDIDATE`. The score is not objective truth. Any Critical issue blocks PASS; unresolved High issues require explicit disposition. `AAA Candidate` additionally requires overall `≥95`, zero Critical, no unaccepted High, identity intact, no accessibility blocker, responsive QA executed, independent critique completed, evidence confidence `HIGH`, and no material unreviewed AI-slop finding.

## Round protocol

Use `GOAL → BAR → DECOMPOSE → BUILD → RUN → INSPECT → MEASURE → CRITIQUE → PRIORITIZE → FIX → RENDER AGAIN → INDEPENDENT CRITIQUE → FINAL QA`. A fresh read-only critic must judge the integrated artifact after material changes. Record the largest meaningful gap first; do not polish around a broken route, missing identity lock, absent visual evidence, or failed accessibility gate. Trivial/normal/high-value/high-fidelity work gets a default budget of 1/2/3/4 cycles, adjustable per benchmark, and must record a stop reason.

## Applicability

The bar is adaptive. A pure SVG icon request may stop after medium selection, vector inspection, contrast/accessibility, and package checks. A live frontend redesign additionally requires browser render, interaction, responsive, region/state and visual QA evidence. A design-only brief can pass its strategy/handoff gates while clearly marking runtime render checks as not applicable or not run. A human may override a threshold or stop iterations, but the machine-readable override records scope, reason, tradeoff, residual risk, compensating evidence, owner and revalidation trigger; it may produce `CONDITIONAL PASS` only and does not relabel the result as AAA.

## Package-level vs artifact-level claims

The repository can prove package structure, contract validation, deterministic static audits and honest result gating. It cannot prove that an arbitrary future interface is beautiful, usable or pixel-faithful without the actual artifact, renderer, states, references and separated critique. Reports must keep those claims distinct.
