# Mobile product surfaces

## Touch-first contract

Design for reachable primary actions, comfortable touch targets, visible pressed/focus states, and clear navigation/back behavior. Do not rely on hover, precision drag, hidden swipe, or tiny icon-only controls without an equivalent visible affordance.

## Information and layout

Prioritize one task per view where appropriate, preserve required context, and use progressive disclosure for secondary detail. Define stack/order, sticky behavior, bottom sheets, drawers, and scroll ownership. Avoid desktop columns squeezed into a narrow viewport.

## Input and system UI

Test virtual keyboard occlusion, autofill, input types, validation, safe-area insets, orientation, zoom, and reduced motion. Restore focus and scroll position after overlays or navigation. Keep errors near the field and announce status when needed.

## Responsive consistency

Share tokens and component behavior with larger surfaces where useful, but allow mobile-specific composition. Check 375px and an intermediate width with realistic content, loading/empty/error states, and network delay.
