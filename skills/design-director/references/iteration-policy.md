# Adaptive visual iteration policy

Generation 1 is not automatically accepted for material visual work. The system must generate or implement, inspect the artifact, score the applicable criteria, and decide whether a correction is justified.

## Pass loop

```text
Generate or implement
→ render/inspect
→ score regions and dimensions
→ independent or separated read-only critique
→ choose: accept, edit, regenerate, or stop with limitation
```

After every material fix, produce a fresh render and fresh critique. Carry forward facts and constraints, not the previous approval. A correction brief names the largest gap, affected region/state, expected change, evidence, and whether identity must remain locked.

## Adaptive iteration budget

Budgets are ceilings, not obligations:

| Work | Default maximum | Use when |
| --- | ---: | --- |
| Trivial | 1 cycle | Isolated icon, tiny copy/crop correction, or low-risk change |
| Normal | 2 cycles | Standard asset or interface with a bounded quality gap |
| High-value visual | 3 cycles | Hero, campaign asset, brand surface, major dashboard, or high-traffic route |
| Explicit high-fidelity | 4 cycles | User explicitly requires fidelity and cost/latency are acceptable |

Set the budget from scope, risk, evidence availability, and cost. Do not loop indefinitely to chase a noisy score.

## Edit versus regenerate

Prefer `EDIT` when identity is correct, composition is nearly correct, the change is localized, the product/character must remain consistent, or a supplied artifact is the authorized edit target. Preserve the parent asset and provenance.

Consider `REGENERATE` when the composition is structurally wrong, the art direction misses the brief, the visual language is incompatible, or many independent structural findings make local edits brittle. Regeneration still carries the identity lock, reference roles, exact text constraints, and acceptance criteria.

If the choice is uncertain, select the least destructive path that can address the largest gap and record the rationale as an implementation decision—not as critic input.

## Stop conditions

Stop and record one reason when:

1. the applicable threshold is reached and no material correction remains;
2. the budget is exhausted;
3. a required tool, artifact, reference, credential, or capability is unavailable;
4. cost or latency no longer justifies another cycle;
5. the last change produced insignificant or negative improvement;
6. the user explicitly accepts a lower score, chooses another direction, interrupts, prohibits generation, or requests audit-only work.

The final packet must include `stop_reason`, last observed score, unresolved findings, evidence state, and next safe action. “Looks good” is not a stop reason.

## Largest-gap prioritization

Select the next correction using the [visual QA](visual-qa.md) ledger and region scores. Prioritize criticality, user impact, identity/constraint risk, and region gap before polish. Do not spend a cycle on shadow tuning while a mobile CTA, broken state, wrong package, or unreadable table remains.

## Human override and degradation

The user can accept below threshold, require a style, choose a different concept, stop iteration, prohibit generation, or ask for an audit only. Record who/what made the override, scope, reason, residual risk, and evidence state. The override is a declared decision, not an AAA or PASS claim.

When imagegen, browser, Figma, fonts, references, or assets fail, preserve unaffected work and mark the affected criterion `Blocked` or `Not run`. Offer a safe fallback, but do not silently change medium, identity, product truth, or acceptance target. See [degradation and evidence](degradation-and-evidence.md).

## Iteration record

Keep one record per cycle:

```yaml
cycle: 1
operation: EDIT # EDIT | REGENERATE | IMPLEMENT | INSPECT
input_artifact: "..."
changed_region: "..."
largest_gap: "..."
budget: 3
score_before: 82
score_after: null
critic_level: INDEPENDENT
stop_reason: null
evidence: "..."
```

Do not call an iteration complete until `score_after` and its evidence exist, or the cycle is explicitly stopped as `BLOCKED`, `NOT RUN`, or an accepted override.

In the machine-readable run contract, bind the cycle count to the benchmark:

```yaml
iteration_budget:
  max_cycles: 3
  cycles_used: 1
  remaining_cycles: 2
```

Every `EDIT`/`REGENERATE` record must reference a new render with a new path
and verifiably changed content, and include `score_before`, `score_after`,
`correction_brief`, and evidence. When local files are available the validator
compares their SHA-256 content identity; a different ID or renamed identical
file is not a fresh render. The scorer rejects counts that do not reconcile. A human override is structured with
scope, reason, trade-off, residual risk, compensating evidence, owner, and a
revalidation trigger; it can produce `CONDITIONAL PASS`, never an AAA result.
