# Independent Visual Critic Contract

The critic is a read-only quality boundary between a builder and an accepted visual result. It diagnoses the observed artifact; it does not edit files, regenerate assets, or approve its own work.

## Blind input packet

For the first pass, provide only the minimum packet needed to judge the request:

- user request and intended audience/job;
- applicable constraints, preservation rules, and acceptance criteria;
- references with typed roles, native dimensions, and provenance;
- artifact path or URL, rendered screenshots, viewport, state, and environment;
- applicable quality dimensions and the relevant region/state matrix.

Do not provide builder rationale, design-defense narrative, self-assigned score, desired verdict, or a list of “known acceptable” issues. A builder may provide factual artifact metadata, but not an argument for approval. If the packet is incomplete, report the missing evidence instead of inferring it.

## Independence levels

Record the level on every critique. A fresh pass is useful at every level, but self-review is never independent:

| Level | Meaning | Approval authority |
| --- | --- | --- |
| `SELF` | Same builder and same reasoning context reviews its own artifact | Diagnostic only; never an independent approval |
| `SEPARATED_SELF` | Same builder/runtime reviews after context separation with rationale withheld | Stronger blind check, still not independent |
| `PEER` | Another specialist or agent reviews read-only, but shares project context or builder history | Fresh peer critique; not equivalent to independent review |
| `INDEPENDENT` | Separate reviewer/process receives only the blind packet and has no builder rationale or auto-score | Qualifies as the independent critique required by high-value work |

If the runtime cannot provide `INDEPENDENT`, state the strongest level actually achieved. Never relabel `SELF` or `SEPARATED_SELF` as independent for convenience.

## Required output

Return this contract in a stable, machine-readable shape when a runner is available, or with the same headings in prose:

```yaml
schema_version: "1"
benchmark_id: "..."
run_id: "..."
inspection_id: "..."
created_at: "2026-01-01T00:00:00Z"
reviewer_id: "..."
independent: true
blinded: true
independence: INDEPENDENT
blind_packet:
  request: "..."
  constraints: ["...are preserved"]
  references: []
  artifact: ["artifact.html", "render.png"]
  acceptance_criteria: ["...is observable in the current render"]
  builder_rationale_withheld: true
  self_score_withheld: true
reviewer_provenance:
  process: "fresh read-only review"
  builder_id: "builder-runtime"
  context_shared: [request, constraints, references, artifact, acceptance_criteria]
  rationale_received: false
  self_score_received: false
  packet_digest: "0000000000000000000000000000000000000000000000000000000000000000" # SHA-256 of canonical blind_packet JSON
verdict: BLOCKED # PASS | CONDITIONAL PASS | FAIL | BLOCKED
overall_score: null # 0-100, or null when evidence is insufficient
confidence: LOW # HIGH | MEDIUM | LOW
evidence_confidence: LOW # HIGH | MEDIUM | LOW
evidence_quality: NONE # HIGH | MEDIUM | LOW | NONE
dimension_scores: {}
region_scores: []
findings:
  critical: []
  high: []
  medium: []
  low: []
  polish: []
top_corrections: []
constraint_violations: []
evidence_missing: []
```

Each finding should include `id`, `location`, `expected`, `observed`, `severity`, `evidence`, and a state such as `OPEN`, `FIXED`, `ACCEPTED`, `NOT RUN`, or `BLOCKED`. `top_corrections` must be ordered by material user impact, not by how easy a change is.

The verdict has one meaning only:

- `PASS`: applicable evidence is present, no unresolved Critical or unaccepted High finding remains, and the threshold is met;
- `CONDITIONAL PASS`: the artifact is usable within a declared scope, but polish, evidence, or accepted residual risk remains;
- `FAIL`: observed evidence shows a material quality, identity, accessibility, usability, or constraint failure;
- `BLOCKED`: the critic cannot make the requested claim because a required artifact, reference, render, interaction, or capability is missing.

Never use `PASS` to mean “the code looks plausible.” A missing render is `BLOCKED` or `NOT RUN`, not a passing visual result.

## Scoring and evidence

Score only applicable dimensions using [quality-rubric](quality-rubric.md). Report the denominator and the evidence that supports each material score. The score is a QA heuristic, not objective truth. A high average cannot cancel a Critical constraint violation or hide a missing required gate.

Use evidence confidence as follows:

- `HIGH`: current render/screenshot, relevant interaction and states, reference when required, and a fresh separated or independent critique;
- `MEDIUM`: current render or executable artifact plus partial interaction/reference evidence, or a fresh peer critique;
- `LOW`: source code, plan, or builder description without current rendered evidence.

When evidence quality is `LOW`, do not issue an approval for a claim that requires visual observation. The critic may still identify likely risks and list the exact next evidence needed. A machine-qualified independent PASS also requires the blind packet, a distinct `builder_id`, and a SHA-256 `packet_digest` over its canonical JSON; these fields make the boundary auditable without pretending that a JSON claim proves reviewer psychology.

## Read-only boundary

The critic may inspect the artifact, screenshots, references, accessibility/performance reports, and repository state needed for the requested scope. It must not modify files, alter scores, rewrite the ledger, hide provenance, or select a more flattering viewport/state. Fixes belong to the builder/finisher; the next critique must use a fresh render after every material fix.

## Minimal review sequence

1. Confirm the packet, applicable dimensions, viewport/state coverage, and evidence quality.
2. Compare the artifact to the request, constraints, typed references, and acceptance criteria.
3. Score regions and dimensions; identify the largest material gap.
4. Classify findings as Critical, High, Medium, Low, or Polish with direct evidence.
5. Check identity lock, product specificity, anti-slop signals, accessibility, responsiveness, and asset suitability where applicable.
6. Return the contract, top corrections, missing evidence, and an honest verdict.

The critic diagnoses. It does not self-approve.
