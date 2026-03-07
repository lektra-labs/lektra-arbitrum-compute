# Lektra Console UX Notes

## Context
The current Lektra console already has the right core mental model: a user enters one prompt, the platform turns that prompt into a task, and several nodes collaborate to produce results. The UI extension should preserve that shell instead of introducing a separate blockchain product surface.

The corrected task story should drive the UX:
- one task
- 4 returned image outputs
- 3 distinct nodes involved
- one node creates 2 images
- Node 003 fails and its work is recovered on Node 001 (`Lektra`)

That relationship should be obvious in the interface. Right now the timeline proves it, but the surrounding UI does not explain it clearly enough.

## One-screen flow
- Keep the existing Generate page layout as the main canvas.
- Show all 4 returned images directly in the results area.
- Add node attribution directly on each image card so the user sees which node produced which output.
- Keep settlement in a collapsible side panel, not as a separate page.

Why:
- The user’s first concern is quality and speed, not escrow mechanics.
- Showing node attribution at the result level makes distributed execution legible without sending the user to a separate technical view.

## Execution detail
- The execution timeline should match the layout shown in the console:
  - 4 execution rows total
  - the first row is a failover path: `10.66 S Node 003 - Exxact -> Node 001 - Lektra`
  - the remaining rows show the other node executions directly
- There are 5 settlement records total:
  - 1 failed record for `Node 003 - Exxact`
  - 1 successful recovery record for `Node 001 - Lektra`
  - 3 other successful records for the remaining execution bars
- Each timeline bar should map to an execution unit with node name, duration, and role.
- The failover row should be visually distinct and explained in plain language.
- The page should explain repeated node use explicitly, for example: `Node 007 produced two images`.

Why:
- A task that fans out to several nodes is the product differentiator.
- Users need to understand why one prompt can produce several outputs, repeated node usage, and a failed attempt.
- This is the cleanest place to connect prompt, outputs, and node orchestration.

## Settlement panel
- The settlement proof box should live on the right side of the execution timeline area.
- Clicking a colored execution bar should open only the corresponding settlement record.
- The failover row should expose two separate settlement records:
  - one disputed record for the failed `Node 003 - Exxact` execution
  - one successful record for the recovered `Node 001 - Lektra` execution
- The drawer should show the proof bundle:
  - `task_id`
  - `execution_unit_id`
  - `escrow_job_id`
  - `result_hash`
  - `submit_result_tx_hash`
  - challenge window state
- Primary actions should be contextual:
  - `Release` only for releasable settlement records
  - `Copy proof`
  - `Open dispute`

Why:
- The task page already has the user’s trust context.
- Keeping the proof box beside the bars makes the cause-and-effect obvious.
- It avoids forcing the user to think in blockchain-first terms.
- Splitting the settlements prevents the UI from collapsing a failed execution and a recovered execution into one misleading status.

## Billing trace
- The Billing page should show more than balance changes.
- Each charge row should map prompt to task, node spread, failure state, and settlement state.
- Refunded or disputed tasks should be visible in the same table.

Why:
- Users care whether they were charged correctly.
- Billing becomes the business-facing explanation of settlement, while the task drawer remains the technical explanation.

## UX Principles
- Preserve the current Lektra shell.
- Explain distributed execution in plain language.
- Reveal settlement only when the user needs trust or payment detail.
- Keep proof tied to tasks, not to a separate crypto area.
- Make the mapping between prompt, task, execution units, nodes, outputs, and settlement explicit.

## Visual Direction
- Keep the dark left sidebar and light workspace from the current console.
- Reuse the compact prompt composer rather than replacing it with a new hero layout.
- Use small badges, accordions, and a side panel for technical metadata so the core product still feels like creative tooling, not chain tooling.

## Product Implication
If Lektra wants settlement to feel like a product advantage instead of a back-office mechanism, the UI should say:
"Your prompt was processed across multiple nodes, your outputs were delivered, and the payment trail is verifiable."

That story should be visible in one path inside one workspace:
`Generate` -> expand `Execution detail` -> click a colored bar -> read the matching payment record -> expand `Billing trace`
