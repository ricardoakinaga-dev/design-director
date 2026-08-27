# Visual QA

Visual QA is a reproducible evidence loop, not a final opinion. It applies to runnable interfaces and adapts to banners, assets, game UI, and design-only work.

## Required loop

```text
RUN APP → OPEN TARGET → SET VIEWPORT/STATE → SCREENSHOT
→ INSPECT → COMPARE → LEDGER → FIX LARGEST GAP
→ SCREENSHOT AGAIN → FRESH READ-ONLY CRITIQUE → FINAL QA
```

1. Start the real artifact through its supported command and record the command, environment, and route.
2. Use Browser/IAB when available. Use Playwright only as an explicitly recorded fallback; if neither exists, mark interaction and screenshot claims `BLOCKED` or `NOT RUN`.
3. Capture the initial render at every required viewport/state combination. Preserve native screenshot dimensions and bind the file to the declared artifact.
4. Inspect screenshot, interaction behavior, console, network failures, focus, and overflow where the capability supports it.
5. Compare against the accepted concept, supplied reference, product system, identity lock, and acceptance criteria.
6. Log every material discrepancy in the serializable ledger below and cover every applicable semantic region, including clean regions with an observed score/evidence record.
7. Fix the largest user-impact gap, rerender, and inspect again. Do not stop after a code-only fix.
8. After material changes, obtain a fresh read-only critique; the builder’s previous score does not count as approval.

## Viewport matrix

Use the product’s declared breakpoints when they exist. Otherwise use the fallback fixtures `375`, `768`, and `1440` CSS pixels. Add an intermediate width when wrapping or layout mode changes there. Record device pixel ratio separately; do not substitute a resized screenshot for a native viewport capture.

## State matrix

Test only states relevant to the surface, but do not test only the happy path:

`default`, `hover`, `focus-visible`, `active`, `disabled`, `loading`, `empty`, `error`, `success`, `selected`, `long-content`, `short-content`, and `keyboard-open/mobile` when applicable. Include modal, drawer, pagination, permission, offline, and recovery states when the product exposes them.

## Semantic regions

Score regions independently when the surface has meaningful structure. Adapt names to the product rather than forcing a template.

| Surface | Useful starting regions |
| --- | --- |
| Landing/marketing | Header, Hero, Trust, Features, Proof, CTA, Footer |
| Dashboard | Navigation, Header, Filters, KPI, Charts, Table, Actions, States |
| Mobile flow | Navigation, Primary task, Form, Actions, Keyboard area, Error recovery |
| Banner/asset | Subject, Focal area, Copy/CTA, Safe zones, Crop, Brand marks |
| Game UI | HUD, Character/subject, World/context, Icon family, Collectible, Environment |

## Fidelity ledger

Serialize one record per viewport/state/region discrepancy. The minimum contract is:

| Field | Meaning |
| --- | --- |
| `location` | Route, selector, asset area, or semantic region |
| `render_id` | Current native render that was inspected |
| `viewport` | Native width/height and DPR if known |
| `state` | State fixture used |
| `expected` | Reference, system, or acceptance expectation |
| `observed` | What the current artifact actually showed |
| `severity` | `Critical`, `High`, `Medium`, `Low`, or `Polish` |
| `evidence` | Screenshot/report path, interaction step, or explicit missing evidence |
| `fix` | Smallest material correction |
| `status` | `OPEN`, `FIXED`, `ACCEPTED`, `NOT RUN`, or `BLOCKED` |

Example:

```json
{
  "location": "Hero / primary CTA",
  "render_id": "hero-375-default",
  "viewport": {"width": 375, "height": 812, "dpr": 1},
  "state": "default",
  "expected": "CTA remains visible within the first mobile viewport",
  "observed": "CTA falls below an oversized decorative image",
  "severity": "High",
  "evidence": "artifacts/runs/2026-08-26/hero-375-default.png",
  "fix": "Reduce image crop and restore action priority",
  "status": "OPEN"
}
```

Do not mark a finding `FIXED` until a new render or interaction check observes the correction. `ACCEPTED` requires an explicit human or product decision and records the residual risk.

For a benchmark run, the minimum coverage set is the product of required
viewports and required states after their applicability filters, crossed with
required regions after their own viewport/state filters. A missing triple is
`BLOCKED`, even when the global score is high. Every render needs a passing
inspection, and the latest render/inspection/score/critic chain must be current.
A render must decode to its declared native width/height (multiplied by the
benchmark DPR when applicable); a resized, vector, source, or placeholder image
is not evidence of a browser capture. Render records carry a SHA-256 content
identity and capture timestamp; inspections and later score/critic records must
be chronologically downstream of the render they claim to assess. Region scores
and ledger entries carry `render_id` and cite the current inspectable raster
capture, not merely a stale file with a plausible name.

## Region and largest-gap scoring

Give each observed region a `0–100` score plus evidence confidence. Prioritize the next iteration by material impact, not by the prettiest easy win:

```text
priority = severity_weight × user_impact × region_gap
region_gap = max(0, target_score - observed_score)
```

Use the applicable [quality rubric](quality-rubric.md) for dimension scores. A broken primary task, identity violation, inaccessible essential control, or unsupported claim outranks a lower polish score. Report region scores such as `Hero: 86`, `CTA: 78`, and the reason the next fix targets the largest gap.

## Comparison checklist

Inspect geometry, typography, spacing, size, position, color, surfaces, shadows, radii, imagery, copy, content length, states, behavior, focus, and overflow. For references, inspect both reference and artifact at native dimensions and declare reference provenance. For assets, also inspect crop, safe zones, anatomy/artifacts, text, identity, integration, file characteristics, and mobile suitability.

## Evidence and claims

The evidence packet records command/procedure, timestamp or run context, environment, artifact paths, viewport/state, reference dimensions, observed result, ledger, unresolved gaps, and confidence. A critic may approve only the scope actually observed.

Do not claim `pixel-perfect`, `faithful`, `visually complete`, or `production ready` from one screenshot, source code, a resized preview, or an unexecuted plan. If Browser/IAB, Playwright, a reference, or a required state is unavailable, say exactly which claim is blocked.
