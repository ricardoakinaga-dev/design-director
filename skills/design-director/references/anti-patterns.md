# Anti-patterns and AI-slop detection

This is a contextual rejection checklist, not a ban on particular aesthetics. A gradient, glass surface, pill, glow, centered composition, or three-column section can be valid when it has a product, brand, usability, or communication job. The critic must state the job and cite the evidence before treating it as a finding.

## Detection matrix

| ID | Pattern to inspect | Signal | Typical risk |
| --- | --- | --- | --- |
| `SL-01` | Purple/blue gradient cliché or gradient overload | Default “AI/startup” gradient with no semantic or brand role | Medium/High when it replaces identity |
| `SL-02` | Glassmorphism without purpose | Blur, translucency, and borders add no grouping, depth, or state meaning | Medium |
| `SL-03` | Excessive pills or meaningless badges | Every control, label, or metric uses a capsule without hierarchy | Medium |
| `SL-04` | Card soup / icon soup | Nested cards or unrelated icons fragment one task | High when density or scan path suffers |
| `SL-05` | Generic SaaS hero | Familiar copy, abstract gradient, and generic dashboard without product truth | High |
| `SL-06` | Meaningless orb/blob/glow | Decorative shape has no focal, brand, or compositional role | Low/Medium |
| `SL-07` | Fake logos, metrics, testimonials, or claims | Social proof or numbers are invented, unverifiable, or presented as real | Critical |
| `SL-08` | Oversized empty whitespace / low useful density | Space hides missing content or harms comparison/operations | Medium/High by job |
| `SL-09` | Decorative charts | Chart shape is ornamental, data encoding is absent, or insight is unclear | High for data surfaces |
| `SL-10` | Random glow, unnecessary neon, arbitrary gradients | Effects are copied between components without a reason | Medium |
| `SL-11` | Generic stock-like AI people | People are interchangeable decoration, not product-relevant subjects | Medium/High |
| `SL-12` | Inconsistent radii, arbitrary shadows, or token bypass | Local magic values drift from the system | Medium/High |
| `SL-13` | Meaningless badges and repetitive three-column sections | Repeated modules exist because the template expects them | Medium |
| `SL-14` | Overly centered composition | Everything is centered, flattening hierarchy and action direction | Medium |
| `SL-15` | AI-generated startup aesthetic cluster | Several generic signals combine without domain-specific content or interaction | High |
| `SL-16` | Generic font/icon family or weak CTA | Default choices are uninspected, competing, or semantically vague | Medium |
| `SL-17` | Dashboard as landing page / squeezed mobile | Surface ignores operational density or simply shrinks desktop | High |
| `SL-18` | Rasterized UI text or approximate identity redraw | Text, logo, package, face, or product identity is baked or guessed without reason | Critical/High |
| `SL-19` | Placeholder presented as final | Missing asset/state is hidden behind a polished-looking substitute | Critical |
| `SL-20` | Unsupported pixel-perfect claim | No native reference, screenshot, comparison, or current evidence | Critical |

## Systematic review protocol

For each applicable ID, record one of `OBSERVED`, `NOT OBSERVED`, `NOT RUN`, or `BLOCKED`, plus evidence, confidence, and context. A source scan can flag a risk, but it cannot prove a visual anti-pattern without a render. Do not convert an empty finding list into a pass when visual evidence is missing.

Escalate a pattern when it harms hierarchy, task completion, accessibility, product truth, identity fidelity, or specificity. An isolated decorative choice is not automatically a failure. A cluster of unmotivated choices can be a material finding even when each choice looks fashionable alone.

## Product-specificity test

Ask:

> If the logo and product name disappeared, would this still look specifically created for this product?

If the answer is no or uncertain, increase specificity through domain-native content, workflows, data, visual metaphor, hierarchy, interaction, composition, product-native states, or a defensible material/asset language. Do not fix it by adding another gradient, badge, orb, or generic illustration.

Record the result as an observation under `Product specificity` in the [quality rubric](quality-rubric.md). A recognizable logo alone is not evidence of product specificity.

## Existing rejection checklist

Also inspect gradient overload, indiscriminate glass, borders everywhere, exaggerated shadows, purposeless decoration, generic hero/illustration, badge overload, generic font, weak or competing CTA, bad copy width, inconsistent icons, over-centering, dashboard-as-landing-page, desktop squeezed into mobile, neon overuse, low domain density, fake claims, rasterized UI text, approximate redraw of supplied identity, placeholder-as-final, and unsupported pixel-perfect claims.

## Repair order

Fix structure first: truth, content, hierarchy, action, grid, type, density, and states. Then fix system consistency: tokens, components, icons, color roles, radii, shadows, and responsive behavior. Only then tune finish: crop, material, image treatment, motion, and micro-spacing. Do not add an effect to conceal a structural miss.
