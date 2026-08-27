# Identity, references, and provenance

References are typed evidence, not permission to copy protected expression. A reference can inform one attribute while leaving identity, composition, or subject unchanged.

## Identity Lock

Create an explicit lock before generating, editing, or reconstructing a sensitive asset:

```text
IDENTITY LOCK

Immutable:
- ...

High sensitivity:
- ...

Flexible:
- ...

Forbidden inference:
- ...
```

Use the categories this way:

- `Immutable`: logo geometry, wordmark, packaging proportions, product silhouette, facial identity, character-defining marks, required colors, exact legal/product text;
- `High sensitivity`: recognizable pose or expression, label hierarchy, mascot features, material finish, brand color relationships, distinctive costume or prop;
- `Flexible`: background, crop, lighting, supporting composition, non-identity texture, secondary decoration, and implementation medium when authorized;
- `Forbidden inference`: invented logo details, product claims, ingredients, prices, people, metrics, testimonials, legal copy, or identity traits not supported by input.

If a change touches `Immutable` or `High sensitivity`, require an explicit edit target and a post-edit acceptance check. Preserve identity before optimizing style.

## Reference roles

Declare one or more roles per reference, with a short rationale:

| Role | May inform | Does not authorize |
| --- | --- | --- |
| `IDENTITY` | Logo, package, product, character, person, mascot truth | Redrawing, recoloring, or changing proportions without permission |
| `SUBJECT` | What object/person/scene must be present | Copying another reference’s composition or style |
| `COMPOSITION` | Layout, crop, focal placement, scale, negative space | Changing identity or protected subject |
| `STYLE` | Visual language, rendering, texture, shape grammar | Copying exact subject/composition or identity |
| `LIGHTING` | Direction, softness, contrast, time, shadow behavior | Altering identity or composition by implication |
| `COLOR` | Palette relationships, contrast, temperature | Treating colors as brand-immutable without evidence |
| `MATERIAL` | Surface, finish, translucency, tactility | Inventing product material facts |
| `EDIT TARGET` | The supplied artifact that may be locally changed | Unrelated regeneration or silent replacement |
| `INSPIRATION` | Broad directional cues | Claims of fidelity or permission to reproduce |

One reference may have multiple roles, but each role must be scoped. A lighting reference does not authorize copying composition; a style reference does not authorize changing identity; an inspiration reference does not prove fidelity.

## Provenance record

Record provenance whenever possible:

```yaml
source: user-supplied # generated | edited | user-supplied | repository-existing | licensed | unknown
locator: "path, URL, or asset id"
parent: "source asset for an edit, if any"
tool: "native image generation, editor, repository, or unknown"
created_at: "timestamp or unknown"
license: "known terms or unknown"
reference_roles: [IDENTITY]
```

Never silently delete, overwrite, or relabel provenance. Preserve the original and name derived assets by role. If provenance is `unknown`, do not upgrade it to licensed or repository-existing by assumption.

## Reference fidelity rules

For reconstruction or brand work, capture native dimensions and inspect the reference and output in the same review pass. Separate `must preserve`, `may change`, and `must avoid`. If the reference is missing, inaccessible, low resolution, or not authorized for identity inference, mark fidelity `BLOCKED` or `Inferred`; do not claim faithful reconstruction.

## Identity acceptance

The [asset acceptance gate](asset-acceptance.md) must verify immutable and high-sensitivity fields independently from aesthetic polish. A beautiful result with a wrong logo, package, product, character, or person fails identity acceptance.

## Human direction and override

The user may choose a different direction, prohibit generation, require a specific style, or accept a controlled deviation. Record the decision, scope, approver, reason, and residual risk. An override changes the acceptance target; it does not erase evidence or relabel an unverified identity as faithful.
