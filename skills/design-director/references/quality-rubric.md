# Quality rubric

## Score dimensions

Score each applicable dimension from 0–10 using observed evidence. With all ten dimensions, the sum is already a 0–100 heuristic score. If fewer dimensions apply, report `sum / applicable dimensions × 10` and the denominator; do not imply a full ten-dimension score.

| Dimension | 0–3 | 4–6 | 7–8 | 9–10 |
| --- | --- | --- | --- | --- |
| Hierarchy | No clear priority | Some scan path, competing emphasis | Clear primary path | Immediate, calm, context-perfect priority |
| Typography | Broken/unclear type | Usable but generic or unstable | Intentional roles and measure | Excellent voice, rhythm, wrapping, and fallback behavior |
| Spacing/layout | Misaligned or cramped | Mostly coherent with local drift | Consistent grid and rhythm | Proportions feel inevitable across states/viewports |
| Color | Illegible or arbitrary | Usable but weak role/state system | Coherent semantic palette | Distinctive, restrained, accessible, and resilient |
| Consistency | Pattern drift | Several one-offs | System is mostly coherent | Components, icons, states, and assets share a grammar |
| Usability | Primary task unclear/broken | Task works with friction | Clear affordances and recovery | Fast, predictable, informative, and forgiving |
| Responsiveness | Broken narrow/intermediate states | Basic reflow with misses | Layout adapts and preserves priority | Deliberate composition at all tested widths |
| Accessibility | Essential barriers | Partial checks | AA-oriented behavior and evidence | Inclusive interaction is designed, tested, and maintained |
| Brand/identity | Wrong or generic identity | Recognizable but inconsistent | Identity is integrated | Memorable, faithful, and appropriately specific |
| Polish | Raw/incomplete | Some refinement | Finished primary path | Detail, loading, empty, error, motion, and media all feel cared for |

## Scoring rules

Use whole numbers and state evidence quality. Do not average away a failed critical gate. Important visual work targets 90+, but a 90 without current runtime or identity evidence is not a release approval. If presenting an average instead, multiply the average by ten exactly once.

## Critic prompt

Ask a fresh read-only critic to compare the actual artifact with the applicable dimensions, identify the largest meaningful gap first, cite evidence, assign severity and confidence, and return `APPROVE`, `REJECT`, or `BLOCKED`. Do not provide the builder's explanation or desired verdict.
