# Accessibility

Use the current project standard when one exists. Otherwise treat WCAG 2.2 AA as the working baseline and state that assumption. Accessibility is a design gate, not a final color pass.

## Structure and names

Use semantic landmarks, one clear page heading, logical heading order, native controls, labels, accessible names, descriptive link text, and programmatic relationships. Preserve state in text/ARIA only when native semantics cannot express it. Verify dialogs, menus, tabs, tables, toasts, and live regions in their actual interaction order.

## Input and focus

Every action must work by keyboard where relevant. Keep focus visible, logical, and restored after overlays or navigation. Do not trap focus accidentally. Check hover-only information, pointer cancellation, touch target size, drag alternatives, and error recovery.

## Perception

Check contrast for text, controls, focus indicators, borders that convey structure, and text over imagery. Pair color with another cue. Support zoom/reflow, readable measure, reduced motion, and content that survives font substitution or localization.

## Content and media

Use useful alt text for informative images and empty alt for decorative images. Do not bake required copy into a raster. Caption or transcribe meaningful media as appropriate. Expose status and errors in a way assistive technology can perceive.

## Verification

Run automated checks as a filter, then manually test keyboard, focus, names, state changes, contrast, zoom, reduced motion, and a representative screen reader path when available. Record what was tested and what remains unavailable; a static scan is not proof of usability.
