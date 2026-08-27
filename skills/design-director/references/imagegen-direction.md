# Image-generation direction

This reference defines the design boundary around image generation. The installed `imagegen` skill remains the authority for tool mechanics, supported inputs, output handling, and fallback commands.

## Use image generation when

The request needs a photo, illustration, texture, environmental scene, character, product mockup, mascot, editorial hero, complex background, or game art. Keep UI layout, exact text, controls, tables, and stateful content in code/SVG.

## Native-first policy

Use the built-in `image_gen` capability first. It does not require `OPENAI_API_KEY`. Make one call per distinct asset or meaningful variant, inspect the result, and move approved outputs to the project without overwriting existing files. Never silently switch to a CLI/API route or hardcode a model for a native tool abstraction.

Only use a CLI/API fallback when the user explicitly requests it or the native route is unavailable and the dependency is accepted. Follow the current installed `imagegen` instructions; do not ask the user to paste a secret into chat.

## Prompt and input discipline

Use the Visual Prompt Compiler in the main skill. Name the asset role, subject, composition, crop, light, palette, materials, exact text, references, must-preserve constraints, must-include details, avoid list, and output intent. Classify each reference as inspiration, identity, subject, composition, style, or edit target. Inspect an unseen edit target before sending it to a tool.

## Acceptance

Inspect every candidate for subject fidelity, composition, identity drift, anatomy/object integrity, edge quality, text spelling, contrast, crop/safe zones, alpha/transparency, dimensions, file format, loadability, integration suitability and mobile suitability. Reject generic, unreadable, overprocessed, or unlicensed outputs. Record provenance and the consuming role. For important assets, use an explicit acceptance gate and do not accept Generation 1 without inspection.

## Variants and edits

Keep identity locks stable across variants. Change local, structural, or style axes deliberately. Use targeted edits when identity/composition is correct and the correction is localized; regenerate when composition, direction or multiple structural constraints fail. Preserve the original, use a new filename for each candidate/approved output, and stop after the benchmark's bounded iteration budget with a recorded reason.
