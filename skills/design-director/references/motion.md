# Motion

## Give motion a job

Use motion to explain continuity, hierarchy, cause/effect, progress, or state change. Avoid animation whose only purpose is to signal “AI,” fill empty space, or delay a task.

## Define a motion system

Specify duration bands, easing, transform/opacity policy, entrance/exit choreography, and interruption behavior. Prefer composited properties and avoid layout-thrashing effects. Keep repeated motion quiet and purposeful.

## Interaction states

Check hover, focus-visible, pressed, loading, success, error, navigation, drawer, modal, and toast transitions. A state must remain understandable if motion is disabled or interrupted. Never hide the only feedback inside an animation.

## Reduced motion

Honor `prefers-reduced-motion`. Replace spatial or looping motion with opacity, instant state, or no animation as appropriate. Test the reduced-motion path instead of assuming a CSS media query covers every JavaScript transition.
