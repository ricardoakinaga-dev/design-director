# Routing matrix

Design Director is the visual-governance layer. The specialist that owns the hard boundary executes it; Design Director supplies intent, constraints, comparison criteria, and acceptance evidence.

| Request boundary | Primary owner | Design Director contribution | Do not duplicate |
| --- | --- | --- | --- |
| Raster generate/edit | `imagegen` / built-in `image_gen` | Asset role, prompt compiler, identity lock, acceptance, provenance | Tool invocation recipes, model flags, API-key setup |
| Frontend concept/build | `frontend-app-builder` | Product/brand thesis, tokens, asset plan, fidelity ledger, critique | Its concept workflow, framework recipes, browser mechanics |
| Browser interaction/screenshot | Browser/IAB; Playwright fallback | What to inspect, viewport/state matrix, discrepancy severity | Browser automation implementation |
| Figma → code | `figma-design-to-code` / direction-specific Figma skill | Get design context before implementation; map brand/system intent and acceptance | MCP/API operations or guessed Figma skill names |
| Code → Figma | `figma-generate-design` or actual installed direction | Visual contract and component intent | Connector operations |
| Figma motion | `figma-implement-motion` or actual installed direction | Motion intent and reduced-motion acceptance | Motion implementation mechanics |
| Game runtime/UI/playtest | `game-studio`, `game-ui-frontend`, `game-playtest` | Art bible, silhouette, palette, readability, visual QA | Engine, physics, collision, and playtest recipes |
| Sprite normalization/export | `sprite-pipeline` | Seed-frame direction, anchor, alpha, acceptance | Pipeline scripts and atlas processing |
| 3D asset preparation | `web-3d-asset-pipeline` or actual installed specialist | Style, material, camera, scale, visual acceptance | GLB/GLTF optimization recipes |
| Chart semantics/data encoding | `data-visualization`, `visualization-strategy-and-critique` | Brand language and non-data visual critique only | Data semantics, misleading encodings, chart implementation |
| Skill packaging | `skill-creator` / `plugin-creator` | Visual purpose and examples | Generic Codex package scaffolding |

## Precedence

1. An explicit user invocation or provider-specific URL wins.
2. A hard deliverable owner wins: Figma operations, raster generation, browser automation, chart semantics, game runtime, or skill packaging.
3. Design Director remains active when visual intent, brand direction, cross-specialist coordination, or visual critique is the main problem.
4. For multi-skill work, appoint one implementation owner and one visual-governance owner. Do not have two skills independently invent the same token or asset contract.
5. If current installed names differ, inspect their actual `SKILL.md` frontmatter and route to the available name. Never infer callable availability from a cache, README, or marketplace listing alone.

## Collision examples

- “Build a SaaS landing page” may involve Design Director plus `frontend-app-builder`; the former owns the visual thesis and acceptance, the latter owns implementation.
- “Make this dashboard's charts more meaningful” belongs to data-visualization; Design Director may review hierarchy, brand, and accessibility after semantics are established.
- “Make a sprite sheet” belongs to `sprite-pipeline`; Design Director defines the art direction and readability constraints.
- “Replace this simple SVG icon” is a direct vector edit, not a raster-generation task.
