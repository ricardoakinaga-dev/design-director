# Asset acceptance gate

An important asset is accepted only after it is inspected in its intended use, not merely generated or saved to disk. Native image generation is the preferred generation path when available; the Design Director owns the asset role, art direction, references, identity lock, selection, acceptance, and iteration, while the image-generation specialist owns generation/edit mechanics.

## Asset packet

Before generation or editing, record the minimum applicable fields:

```text
Asset ID / role:
Use case and placement:
Audience and objective:
Brand context:
Subject and scene:
Composition / focal hierarchy:
Camera / framing / lighting:
Palette / materials / atmosphere:
Exact text and typography:
Safe zones and desktop/mobile crops:
Reference roles and provenance:
Identity lock:
Must preserve / may change / must include / must avoid:
Output size / format / integration target:
Acceptance criteria:
```

Omit fields that truly do not apply; do not invent details to fill a template. Keep exact interface copy in code or SVG whenever possible.

## Gate checklist

Evaluate each applicable item as `PASS`, `FAIL`, `NOT RUN`, or `BLOCKED`, with direct evidence:

- subject and scene correctness;
- composition, focal hierarchy, crop, and declared safe zones;
- brand fidelity and [Identity Lock](identity-and-references.md) compliance;
- exact text spelling, legibility, and text placement;
- artifacts, anatomy, geometry, edges, and unwanted generation residue;
- lighting, palette, material, and atmosphere against the brief;
- reference role compliance and provenance continuity;
- integration suitability at native size and target placement;
- mobile crop/readability when the asset is responsive;
- dimensions, aspect ratio, format, alpha/transparency, file size, color profile when relevant, and resolution for the role;
- licensing/provenance status and whether the asset is a placeholder.

One `FAIL` in identity, exact required text, subject correctness, or a critical integration constraint blocks acceptance. `NOT RUN` and `BLOCKED` do not become pass through explanation.

## Selection and iteration

Generate decision-shaped variants only when they answer a real uncertainty: composition, crop, material, or art-direction tradeoff. Inspect outputs at native resolution and in the intended interface. Score the largest material gap first; use [iteration-policy](iteration-policy.md) to choose `EDIT` or `REGENERATE`, set a finite budget, and record the stop reason.

Use `EDIT` for localized changes when identity and composition are sound. Use `REGENERATE` for structural composition or art-direction failure. Preserve the source asset and provenance in both cases; never overwrite an approved asset silently.

## Role-specific checks

- **Banner/hero:** focal subject survives desktop and mobile crops; CTA/copy safe zone is clear; contrast works over the image; the hero does not become a generic decorative backdrop.
- **Product/package/brand:** immutable geometry, label hierarchy, colors, proportions, and exact marks survive; no invented packaging or claims.
- **Character/person/mascot:** identity lock, anatomy, expression, costume/prop continuity, and authorized changes are checked.
- **Game UI/asset family:** shared palette, scale, anchor, silhouette, icon grammar, world/material language, and readability at runtime size are checked.
- **UI illustration/icon:** medium is appropriate, vector/text remains editable where needed, optical weight matches the system, and rasterized UI text is avoided.

## Degradation and override

If generation, inspection, a reference, or the target runtime is unavailable, keep the asset state `Blocked` or `Not run`, preserve a safe fallback, and state exactly what remains unverified. A user may accept a lower-fidelity asset, prohibit generation, choose another direction, or request audit-only work. Record the override, scope, reason, residual risk, provenance, and next action; do not call the asset AAA or fully accepted without the required evidence.
