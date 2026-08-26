# Color

## Start with roles

Define semantic roles such as canvas, surface, elevated surface, content primary/secondary/muted, border subtle/strong, action, focus, success, warning, and danger. Components consume roles; they should not scatter raw hex values.

## Build a usable palette

Choose a base, accent, and semantic status family with enough steps for text, surfaces, borders, hover, pressed, disabled, and focus. Test the actual foreground/background pair, not isolated swatches. Contrast is a relationship and can change when opacity, imagery, or overlays are introduced.

## Brand without tinting everything

Use brand color where it carries recognition or action. A persistent tint over every surface often lowers contrast and makes the interface visually flat. Neutral space can be part of the brand. An explicit user palette or existing identity overrides a generic “premium” palette.

## State and non-color cues

Never use color as the only signal for status, selection, error, or focus. Pair it with text, iconography, shape, position, or a pattern. Check color-vision conditions and dark/light or high-contrast modes when the project supports them.

## Image interaction

Audit text over imagery for local contrast, crop changes, and loading transitions. Use a scrim or layout separation with intent. Do not solve an unreadable hero by adding an opaque gradient that destroys the image's subject.
