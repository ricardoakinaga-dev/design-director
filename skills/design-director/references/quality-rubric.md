# Quality Rubric 2.0

Use this rubric to summarize observed quality, not to manufacture certainty. Score each applicable dimension from `0` to `10` using current evidence, record the denominator, and keep blockers separate from the average.

## Applicable dimensions and normalized weights

These are default priors, not universal truth. Omit irrelevant dimensions, then normalize the remaining weights:

| Dimension | Default weight | What to inspect |
| --- | ---: | --- |
| Hierarchy | 8 | Scan path, emphasis, task priority, rhythm |
| Typography | 7 | Roles, measure, wrapping, scale, fallback, numeric alignment |
| Spacing/layout | 7 | Grid, proportions, alignment, density, responsive geometry |
| Color | 5 | Semantic roles, contrast, state clarity, restraint |
| Consistency | 6 | Components, icons, tokens, radii, shadows, states |
| Usability | 10 | Affordance, flow, feedback, recovery, content clarity |
| Responsiveness | 8 | Narrow, intermediate, wide, reflow, crop, priority preservation |
| Accessibility | 10 | Keyboard, focus, semantics, names, errors, contrast, reflow |
| Brand/identity | 10 | Truth, identity lock, visual voice, product-specific detail |
| Polish | 5 | Finish, loading/empty/error states, media, motion, micro-detail |
| Reference fidelity | 7 | Only when a reference is an acceptance target |
| Asset quality | 4 | Subject, composition, file characteristics, artifacts, integration |
| Interaction quality | 4 | State transitions, touch, keyboard, feedback, motion |
| Information density | 4 | Useful comparison density, legibility, operational signal-to-noise |
| Product specificity | 5 | Domain-native content, workflows, metaphor, and composition |

For applicable dimensions `A`, calculate:

```text
normalized_weight_i = weight_i / sum(weights for A)
overall_score = round(100 × sum(normalized_weight_i × score_i / 10), 2)
```

Do not give an inapplicable dimension a neutral `5` merely to improve the average. Report `not_applicable` explicitly. A score may be accompanied by a region score, but neither is a substitute for evidence.

## Dimension anchors

Use these anchors consistently; add a short observation for every score below `8` and for every score used in an approval decision.

| Dimension | 0–3 | 4–6 | 7–8 | 9–10 |
| --- | --- | --- | --- | --- |
| Hierarchy | No clear priority | Some scan path, competing emphasis | Clear primary path | Immediate, calm, context-perfect priority |
| Typography | Broken or unclear | Usable but generic or unstable | Intentional roles and measure | Excellent voice, rhythm, wrapping, and fallback |
| Spacing/layout | Misaligned or cramped | Mostly coherent with local drift | Consistent grid and rhythm | Proportions feel inevitable across states/viewports |
| Color | Illegible or arbitrary | Usable but weak role/state system | Coherent semantic palette | Distinctive, restrained, accessible, resilient |
| Consistency | Pattern drift | Several one-offs | System mostly coherent | Components, icons, states, and assets share a grammar |
| Usability | Primary task broken or unclear | Task works with friction | Clear affordances and recovery | Fast, predictable, informative, forgiving |
| Responsiveness | Broken narrow/intermediate states | Basic reflow with misses | Priority survives tested widths | Deliberate composition at all required widths |
| Accessibility | Essential barriers | Partial checks | AA-oriented behavior and evidence | Inclusive interaction is tested and maintained |
| Brand/identity | Wrong or generic identity | Recognizable but inconsistent | Identity integrated | Memorable, faithful, appropriately specific |
| Polish | Raw or incomplete | Some refinement | Finished primary path | Detail, states, media, and motion all feel cared for |

For optional dimensions, use the same scale:

- `Reference fidelity`: compare native reference and artifact at declared regions; do not infer pixel fidelity from a resized preview.
- `Asset quality`: judge subject correctness, crop, artifacts, resolution, identity, and integration.
- `Interaction quality`: judge observed states and recovery, not intended behavior in code.
- `Information density`: judge whether the surface supports its domain job without noise or empty theater.
- `Product specificity`: apply the [specificity test](anti-patterns.md#product-specificity-test), not logo recognition alone.

## Gates and verdict bands

The numeric band is a routing signal:

| Score | Default action |
| ---: | --- |
| `< 70` | `FAIL` / major revision |
| `70–79` | Major revision |
| `80–89` | `CONDITIONAL PASS` / polish required |
| `90–94` | `PASS` candidate when required gates are complete |
| `95–100` | `AAA Candidate` only after the special gate below |

The following blockers override the mean score:

- any unresolved `Critical` finding;
- identity lock or product-truth violation;
- broken primary task or inaccessible essential control;
- unsupported “pixel-perfect”, “faithful”, “production ready”, or equivalent claim;
- missing required render, reference, state, or interaction evidence;
- an unaccepted `High` finding on a release-critical region.

`CONDITIONAL PASS` is not a silent pass: list the residual risk, owner, scope, and next evidence or correction.

## AAA Candidate gate

Use `AAA Candidate` only when all applicable conditions are true:

- overall score is at least `95`;
- no unresolved Critical finding and no unaccepted High finding;
- identity constraints and product truth are intact;
- accessibility has no blocker and the relevant interaction checks ran;
- responsive QA covered the product’s required breakpoints/states;
- an `INDEPENDENT` critique is complete, or the limitation is explicitly recorded and the result is not called AAA;
- evidence confidence is `HIGH`;
- no significant, unjustified anti-slop cluster remains;
- all material claims are `Observed`, not merely inferred from source.

AAA is a gate outcome, not marketing language. If a required condition is unavailable, report the score and `AAA: NOT ELIGIBLE` with the missing evidence.

## Evidence confidence

- `HIGH`: current screenshots/render, relevant interactions and states, reference when applicable, and fresh peer/independent critique;
- `MEDIUM`: current render or executable artifact plus partial state/reference evidence;
- `LOW`: code, concept, prompt, or builder narrative without current rendered evidence.

Never convert `Not run` or `Blocked` into a score of zero, a pass, or a confidence upgrade. Keep these evidence states distinct: `Observed`, `Inferred`, `Not run`, `Blocked`, and `Rejected`.

## Critic prompt

Give the blind packet to a read-only critic. Ask it to compare the actual artifact with only the applicable dimensions, region/state matrix, typed references, and acceptance criteria; identify the largest material gap first; cite evidence; assign severity, score, confidence, and verdict using [critic-contract](critic-contract.md). Do not provide builder rationale, auto-score, or desired verdict.
