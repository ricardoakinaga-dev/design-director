# Game visuals

## Art bible first

Record genre, camera, audience, silhouette language, palette, material, lighting, perspective, scale, anchor/origin, animation cadence, and forbidden elements. Define what makes a character, prop, tile, environment, and HUD belong to the same world.

## Asset roles

Separate world art, gameplay-readable sprites, UI/HUD, effects, background layers, and marketing art. Use transparent raster assets for sprites when appropriate; keep HUD typography, score, controls, hit states, and responsive layout code-native.

## Consistency and gameplay readability

Check silhouette, contrast against every expected background, collision/anchor alignment, frame dimensions, animation spacing, and small-size legibility. Do not let attractive detail hide danger, collectible, player, or interactable state.

## Specialist routing

Use `game-studio` for game architecture, rendering, interaction, and playtest; use `sprite-pipeline` for approved seed-frame, strip, normalization, anchor, transparency, and preview workflows. Design Director supplies the art bible, visual QA criteria, and asset acceptance—not a duplicate game engine.

## QA

Inspect assets at actual in-game scale and in motion. Test loading, fallback, retina/scale behavior, alpha edges, and performance. Compare a playable frame, not only an exported image, before approving a game visual.
