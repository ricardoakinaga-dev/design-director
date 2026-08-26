# Design Director research record

Research date: 2026-08-26. The workspace was empty before this package was created, so the record covers the current Codex/plugin surfaces and local companion skills rather than an existing application.

## Sources checked

1. [OpenAI plugin concepts](https://developers.openai.com/plugins/concepts/plugins) — a plugin is a package and can contain skills, with MCP/apps optional.
2. [OpenAI skill concepts](https://developers.openai.com/plugins/concepts/skills) — the minimal skill surface is a directory containing `SKILL.md`; references, scripts, and assets are optional support surfaces.
3. [Build skills](https://developers.openai.com/plugins/build/skills) — skills should target a recognizable outcome, use progressive disclosure, and be evaluated with direct, indirect, incomplete, negative, and edge prompts.
4. [Build plugins](https://developers.openai.com/plugins/build/plugins) — the package manifest is `.codex-plugin/plugin.json`; a skills-only plugin is valid and uses `skills: "./skills/"`.
5. [Connect plugins to ChatGPT](https://developers.openai.com/plugins/deploy/connect-chatgpt) — local installation and evaluation must verify that references resolve and that starter prompts work.
6. [GPT Image 2 model documentation](https://developers.openai.com/api/docs/models/gpt-image-2) — the current official image model is documented as GPT Image 2 with generation/editing and high-fidelity input support.
7. [Image generation guide](https://developers.openai.com/api/docs/guides/image-generation) — the built-in image-generation tool is the appropriate conversational route; Image API and Responses API are separate routes with different interaction tradeoffs.
8. The current official `openai/plugins` checkout was inspected at commit `33bd9529725fcee78c9e51fcbaa93cd963c3a47b`. Its `build-web-apps`, `figma`, `game-studio`, and `plugin-eval` surfaces were compared with the local skill cache.

## Architectural decisions

### Skill-only plugin

The package has no `.mcp.json`, `.app.json`, or declared tool dependency. Design Director is an orchestration layer: it routes to installed capabilities at runtime and degrades gracefully when a capability is unavailable. This keeps installation portable and avoids pretending that an optional external connector is mandatory.

### One canonical skill, progressive references

All behavior starts in `skills/design-director/SKILL.md`. Domain references are short, linked, and loaded only when the active mode needs them. This keeps the always-loaded contract operational while preserving depth for banner, landing page, dashboard, mobile, game-visual, accessibility, image, and QA work.

### Native image generation first

When a request needs a raster asset, the skill routes to the built-in `image_gen` capability and the local `imagegen` instructions. It does not require `OPENAI_API_KEY`, does not hardcode a model for the native tool, and does not silently switch to a CLI/API route. A CLI/API route is permitted only after an explicit request or a clearly documented fallback decision.

### Compose with frontend and Figma skills

`frontend-app-builder` remains the specialist for concept-led frontend construction and browser verification; Design Director supplies the strategic, brand, art-direction, medium-selection, and critique layer. Figma routes are chosen by direction: Figma-to-code, code-to-Figma, or motion. Design Director does not reimplement those tools' connectors.

### Metadata precedence

The plugin manifest controls marketplace/package presentation. The skill-level `agents/openai.yaml` controls direct skill presentation and implicit-invocation policy. `skills/design-director/SKILL.md` is the behavioral source of truth; the two presentation layers intentionally repeat the display name, short description, and brand color because they serve different discovery surfaces.

The local marketplace template uses the current `AVAILABLE`/`ON_INSTALL` policy enum required by the catalog shape. In this skill-only package, `ON_INSTALL` is catalog metadata for the installation/authentication policy surface; it does not mean that the skill needs credentials. The manifest declares no app, MCP server, hook, or secret. If presentation metadata conflicts, use the plugin manifest for marketplace/package presentation, `agents/openai.yaml` for direct-skill presentation, and `SKILL.md` for behavior.

### Visual evidence over source confidence

The quality bar treats a current render, screenshot, interaction, or asset inspection as stronger evidence than a prose claim. When no browser, reference, font, or generation capability is available, the package reports the missing evidence and provides a review-ready handoff instead of inventing a pass.

## Compatibility notes

- The plugin manifest follows the local plugin validator and current official package shape.
- The skill frontmatter uses only the common `name` and `description` fields.
- `agents/openai.yaml` is optional UI metadata and has no MCP dependencies.
- Helper scripts use Python 3's standard library; no package installation is required.
- The built-in image tool abstracts model selection. The current official model documentation is recorded above for research traceability, not as a hardcoded runtime dependency.
