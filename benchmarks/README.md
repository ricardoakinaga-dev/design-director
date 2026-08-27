# Visual benchmark harness

This directory contains machine-readable contracts for the Design Director's
evidence-driven visual QA loop. A benchmark describes the task and acceptance
bar; it is not a fabricated product result.

## Contract

Each benchmark declares:

`id`, `category`, `brief`, `inputs`, `references`, `constraints`, `viewports`,
`states`, `regions`, `expected_artifacts`, `preservation_rules`,
`quality_threshold`, and `iteration_budget`.

The execution contract is split into four JSON schemas:

- `schema/benchmark.schema.json` — brief, references, constraints and quality bar;
- `schema/run.schema.json` — artifact, render, inspection, score, critique, iteration, ledger, budget, override and final decision;
- `schema/critic.schema.json` — read-only, blinded critic result with packet and reviewer provenance;
- `schema/ledger.schema.json` — region-aware expected-versus-observed records.

Paths are repository-relative. References and generated assets carry a
provenance value (`source`, `generated`, `edited`, `user-supplied`,
`repository-existing`, `licensed`, or `unknown`). Fixtures in
`fixtures/assets.json` are original, fictional references; they are not golden
outputs.

## Golden set

The initial suite is intentionally small and covers different failure modes:

The golden catalog is closed: the directory validator requires exactly
`B01` through `B07`; a valid subset is not a valid release benchmark suite.

| ID | Surface | Primary evidence |
| --- | --- | --- |
| B01 | Premium banner | composition, focal subject, CTA, crop, safe zone and polish |
| B02 | SaaS landing page | product specificity, narrative hierarchy, states and responsiveness |
| B03 | Operational dashboard | density, filters, table meaning, states and mobile adaptation |
| B04 | Mobile flow | touch, form semantics, keyboard, errors, recovery and reflow |
| B05 | Screenshot reconstruction | reference fidelity, region order, crop and responsive transformation |
| B06 | Product/brand identity | identity lock, package proportions, label fidelity, crop and provenance |
| B07 | Game UI / asset family | original character/world/HUD family, readability, anchors, alpha and scale |

## Validate and score

From the repository root:

```bash
python3 -B skills/design-director/scripts/benchmark_validate.py validate benchmarks --root . --pretty
python3 -B skills/design-director/scripts/benchmark_validate.py validate benchmarks/golden/B02-saas-landing.json --root . --pretty
python3 -B skills/design-director/scripts/score_visual.py score path/to/run.json \
  --benchmark benchmarks/golden/B02-saas-landing.json --root . --pretty
```

The directory validator reports every golden file and exits `2` on a contract
failure. Run validation requires `--benchmark`; an unbound run is not a valid
benchmark result. The scorer exits `0` only for `PASS` or `AAA CANDIDATE`, `1`
for a valid but blocked/revision-needed/conditional run, and `2` for an
invalid packet. It requires complete execution, current non-empty and locally
decodable raster render evidence with native dimensions, binds every required
artifact, covers every applicable viewport/state/region triple, applies
critical/high finding blockers independently of the mean, and records
evidence confidence. A complete execution records a timezone-aware procedure,
result, tooling, artifact IDs, timestamps, and evidence; each render carries a
content SHA-256 and the execution evidence must include its current path.
`html`, `pdf`, and vector files may be declared as
auxiliary artifacts, but they do not satisfy a screenshot/render gate.

An independent critic must carry an auditable blind packet containing only the
request, constraints, typed references, artifact, and acceptance criteria.
Reviewer provenance records that builder rationale and self-score were not
received, identifies a distinct builder, and includes a SHA-256 digest of the
blind packet. This is a machine-auditable separation signal, not proof of
epistemic independence. Frontend quality reports must be produced by the
quality-gates contract, cover every required check, and include non-empty
evidence that is locally available when `--root` is supplied; the scorer
independently rechecks the reported LCP/CLS thresholds. Region scores,
inspections and ledger entries carry `render_id` and must cite the current
inspectable raster capture for their viewport/state pair. Material iterations
require a new path, a later capture timestamp, and verifiably changed content
(SHA-256 when local files are available); a renamed copy is rejected. An
approval decision also records its decision timestamp, every current render ID,
latest inspection/score/critique IDs, approver and final evidence; the
validator rejects a stale or incomplete binding.

A host must supply the actual builder, renderer/browser, interaction/state
setup, image inspection and separated critic. The local scorer validates the
declared evidence chain; it does not perform computer vision or infer visual
quality from source code. Missing capabilities must be recorded as
`NOT_RUN`/`BLOCKED`, never replaced by a made-up screenshot or score.

## Iteration rule

Important visual work follows:

`generate → inspect → score → correction brief → edit/regenerate → render again → fresh critique`.

The benchmark budget is bounded from 1 to 4 cycles. The run packet records the
declared ceiling, cycles used, and remaining cycles; each edit/regenerate
cycle records before/after scores, correction brief and evidence. Stop reasons include a
threshold pass, no material correction, budget exhaustion, unavailable tool,
unjustified cost/latency, or insignificant marginal improvement. A human may
override the threshold, but the run must record the reason, trade-off, owner,
residual risk, compensating evidence, and revalidation trigger; the result is
`CONDITIONAL PASS` at most and never `AAA CANDIDATE`.
