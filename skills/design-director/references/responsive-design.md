# Responsive design

## Model behavior, not device labels

Define behavior for narrow (~375), intermediate (~768), and wide (~1440) viewports when applicable. Add breakpoints when content, controls, or reading measure fail. A device label is only a test fixture; the layout contract is the real requirement.

## Transformation checklist

For each section specify whether it:

- keeps its grid, changes column count, or becomes a stack;
- preserves order or changes reading order;
- wraps, scrolls, truncates, or reveals more;
- keeps controls visible or moves them to a drawer/action sheet;
- changes type scale, media crop, spacing, or alignment;
- preserves the primary action and required content.

Do not squeeze desktop into a narrow viewport. Do not hide required copy, tables, filters, or error messages merely to make a screenshot fit.

## Test intermediate widths

Check long headings, nav overflow, table columns, filters, modal width, images, sticky elements, keyboard focus, and horizontal scrolling between named endpoints. Verify zoom/reflow when accessibility requires it.

## Mobile-specific quality

Prioritize one-handed reach, clear back behavior, touch targets, input ergonomics, safe areas, keyboard occlusion, and meaningful loading/empty/error states. Keep gestures optional where an equivalent visible control is needed.
