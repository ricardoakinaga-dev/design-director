# Design systems

## Audit the existing system

Inventory tokens, themes, typography, primitives, components, variants, states, icons, and consuming routes. Locate raw values and one-off exceptions. Separate a genuine missing primitive from a one-off visual requirement before adding anything.

## Token layers

Use three layers where the product warrants them:

1. **Primitive:** raw palette, type, spacing, radius, elevation values.
2. **Semantic:** roles such as `color.content.primary` or `space.section`.
3. **Component:** a control's states and local composition.

Prefer semantic aliases in components. Document the owner and intended use of a new token. Avoid tokens that encode a single page's accidental geometry.

## Component contract

For each changed component, define anatomy, content rules, variants, states, responsive behavior, keyboard/focus behavior, and examples. Make loading, empty, error, success, selected, disabled, and permission states first-class when the workflow exposes them.

## Migration discipline

Change shared primitives only when the benefit and blast radius are understood. Keep unrelated screens stable, migrate consumers coherently, and compare before/after screenshots. Do not silently replace a logo, font, copy, or brand color because a new concept looks better in isolation.

## System health

A system is healthy when repeated decisions are easy, exceptions are visible, and product teams can compose new surfaces without flattening their identity. Measure consistency against function, not uniformity for its own sake.
