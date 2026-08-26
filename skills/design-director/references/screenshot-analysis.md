# Screenshot analysis

## Inspect before interpreting

Load the supplied screenshot with the available image viewer at native resolution when possible. Record dimensions, crop, device clues, and whether browser chrome or scaling is present. If the image is missing, corrupt, or resized without known dimensions, mark exact parity as blocked.

## Decompose the surface

Describe the screenshot as layers:

1. page canvas and background treatment;
2. container, grid, gutters, and major anchors;
3. navigation and global chrome;
4. hero/primary task and visual focal point;
5. sections, cards, tables, or supporting modules;
6. typography roles and line measures;
7. imagery, icons, surfaces, borders, and shadows;
8. interactive states visible in the frame;
9. responsive clues and likely hidden behavior.

Separate observation from inference. Record approximate geometry only as a starting hypothesis; confirm against the rendered artifact.

## Fidelity ledger

Use a table with `location`, `reference`, `actual`, `severity`, `fix`, and `evidence`. Include at least geometry, typography, spacing, color, imagery, and copy/state comparisons. Diff exact copy when text is important. Do not replace a branded logo or product with a hand-drawn approximation without explicit authorization.

## Reconstruction limits

Reconstruct structure in semantic code. Use image assets only for visual content that is actually raster in the reference. Do not bake the whole UI into one screenshot, hide broken behavior behind an image, or infer unavailable screens as facts. Test intermediate widths because a screenshot proves one frame, not a responsive system.
