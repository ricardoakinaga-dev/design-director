# Degradation and evidence

## Evidence states

- **Observed:** current artifact, render, interaction, asset, or command was actually inspected.
- **Inferred:** a reversible assumption based on available context; label it.
- **Not run:** a relevant procedure was not executed.
- **Blocked:** an unavailable capability, input, credential, or authority prevents the claim.
- **Rejected:** the artifact was inspected and failed a criterion.

Never convert `Not run` or `Blocked` into a pass by explanation. A score may summarize observed quality but cannot erase a required missing gate.

## Capability matrix

| Dependency | Minimum safe fallback | Required limitation |
| --- | --- | --- |
| Imagegen | Existing approved asset, code-native treatment, or precise brief | Say which raster asset remains unverified or blocked. |
| Browser/IAB | Static/source checks and local test runner | Do not claim screenshot, interaction, or pixel parity. |
| Playwright | Browser/IAB or manual procedure | Record why the primary path was unavailable. |
| Figma | Export/spec/code-side handoff | Do not claim node inspection or sync. |
| Reference image | Ask a material question or infer only safe structure | Do not claim identity/reference fidelity. |
| Font | Metrics-aware documented fallback | Recheck typography after the real font arrives. |
| Generated asset | Approved local substitute or retry | Keep failure visible; never relabel a placeholder final. |
| CLI/API credential | Native tool or blocked handoff | Never ask for or print the full secret. |

## Failure behavior

For each failure, preserve the request, explain the affected scope, offer the next safe action, and continue with unaffected work. A fallback may be lower fidelity; it must not silently change the medium, product truth, identity, or acceptance claim.

## Evidence packet

Return exact command/procedure, timestamp or run context, environment, artifact path, observed result, affected criterion IDs, and limitations. For visual work include viewport, state, reference dimensions, screenshot path, and fidelity ledger where applicable.
