# Design Director

`design-director` is a skill-only Codex plugin for directing high-quality visual product work: product strategy, art direction, UI/UX, design systems, image assets, frontend composition, and visual QA.

The canonical skill is [skills/design-director/SKILL.md](skills/design-director/SKILL.md). The package deliberately has no MCP server or app dependency. It composes with capabilities that may already be installed, such as `imagegen`, `frontend-app-builder`, Figma skills, Browser/IAB, Playwright, and game-studio tooling.

## What it does

- Converts a vague brief into a decision-ready visual strategy and asset plan.
- Chooses the right medium: native HTML/CSS for UI, SVG for simple vector work, and raster generation for image-led assets.
- Preserves identity and product truth when references or an existing codebase are supplied.
- Produces semantic tokens, responsive states, accessible interaction rules, and implementation guidance.
- Coordinates a real render → inspect → measure → critique → fix → render-again loop when a runnable artifact exists.
- Provides seven golden benchmark contracts, region/state ledgers, an independent-critic contract, bounded iteration policy, and deterministic score/gate validation.
- Reports evidence confidence, quality scores, limitations, stop reasons, provenance, and the next highest-value improvement.

## Validate locally

From this directory:

```bash
python3 -B /home/ricardo/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/design-director
python3 -B /home/ricardo/.codex/skills/.system/plugin-creator/scripts/validate_plugin.py .
python3 -B skills/design-director/scripts/validate_package.py skills/design-director
python3 -B skills/design-director/scripts/smoke_evals.py skills/design-director/evals/evals.json
python3 -B -m unittest discover -s skills/design-director/scripts/tests -v
python3 -B skills/design-director/scripts/check_contrast.py --foreground '#101828' --background '#F8F5EF'
python3 -B skills/design-director/scripts/audit_assets.py . --manifest benchmarks/fixtures/assets.json --strict
python3 -B skills/design-director/scripts/benchmark_validate.py benchmarks
python3 -B skills/design-director/scripts/score_visual.py --help
python3 -B skills/design-director/scripts/compare_visual.py --help
python3 -B skills/design-director/scripts/audit_design_tokens.py --help
python3 -B skills/design-director/scripts/quality_gates.py --help
```

The package is self-contained and uses only Python's standard library in its helper scripts. `compare_visual.py` compares native PNG captures with deterministic dimensions and per-pixel error metrics; browser launch, route/state setup and screenshot capture remain host responsibilities. The optional `plugin-eval` analyzer can inspect the skill directory when that official plugin is available.

## Install

For direct skill discovery, install or symlink `skills/design-director` as `design-director` under the active Codex skills directory, then restart Codex if the skill list is cached. For plugin discovery, place this plugin under a local marketplace's `plugins/design-director` directory and add the marketplace entry; see the official [plugin build guide](https://developers.openai.com/plugins/build/plugins) for the marketplace shape. The template's required `ON_INSTALL` catalog enum does not mean this skill needs credentials: the package declares no app or MCP server.

Do not copy an API key into this package. The built-in image-generation capability is the default route; the optional CLI/API fallback is only used when explicitly requested and separately configured.

## Documentation map

- [Research and compatibility decisions](docs/research.md)
- [Quality bar and verification contract](docs/quality-bar.md)
- [Golden benchmark catalog and run contract](benchmarks/README.md)
- [Worked handoff examples](docs/examples.md)
- [Validation record](docs/validation.md)
- [Local marketplace entry template](docs/marketplace-entry.json)
- [Skill instructions](skills/design-director/SKILL.md)
- [Eval prompts](skills/design-director/evals/evals.json)
- [Anti-patterns](skills/design-director/references/anti-patterns.md)

## Evidence boundary

`benchmarks/` describes the inputs and acceptance contract; it does not contain fabricated product outputs. A capable host must supply the actual builder artifact, render/screenshots, interactions and critic observation. The local validators verify paths, schema bindings, complete execution, native raster render dimensions, current render/inspection/score/critic chains, iteration hashes, PNG comparison metrics and gate logic, but they cannot decide visual excellence from code or a score alone. In this repository's current host, Browser/IAB, Playwright, Figma and a runnable product are unavailable, so live visual execution remains an explicit `BLOCKED`/`NOT_RUN` limitation.

## License

MIT. Project assets and user-provided references remain governed by their own licenses and permissions.
