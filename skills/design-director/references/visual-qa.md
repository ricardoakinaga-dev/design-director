# Visual QA

Visual QA is an evidence loop, not a final opinion.

## Required loop

1. Start the real artifact through its supported command.
2. Open the target route and state in Browser/IAB when available; use Playwright only with a recorded fallback reason.
3. Capture the initial render at relevant viewport/state combinations.
4. Inspect the screenshot and interaction behavior. Check console and network failures.
5. Compare against the accepted concept, supplied reference, or system contract.
6. Write a fidelity ledger with location, expected, actual, severity, and evidence.
7. Fix the largest user-impact discrepancy, rerender, and inspect again.
8. Run the relevant regression and have a fresh read-only critic judge the integrated result.

## Comparison dimensions

Check geometry, typography, spacing, size, position, color, surface/background, shadow, radius, imagery, states, content, and behavior. For a supplied reference, inspect both the reference and current screenshot with the available image viewer in the same pass. Record native dimensions or a blocker; never claim pixel parity from a resized preview alone.

## Viewports and states

Use 375, 768, and 1440px as default fixtures when the surface is responsive. Add project breakpoints and state fixtures for loading, empty, error, success, selected, disabled, hover, focus-visible, drawer, modal, and long content. A single desktop screenshot cannot prove responsive or workflow quality.

## Severity

- **Critical:** wrong identity/content, broken primary path, inaccessible essential control, or a claim unsupported by evidence.
- **High:** major hierarchy/geometry/responsive/state regression or repeated pattern inconsistency.
- **Medium:** visible local mismatch that does not block the primary task.
- **Low / Polish:** refinement with limited user impact.

## Evidence report

Return command/procedure, environment, viewport/state, artifact paths, observed result, unresolved gaps, and confidence. A critic may approve only the scope actually observed. If browser or reference evidence is unavailable, state `BLOCKED` or `NOT RUN` for that claim.
