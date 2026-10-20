# Rwalk fix batch

Read this when the walk ends with any row marked `FIX QUEUED`. The human already ruled
every one of these fixes during the walk. Do not ask again whether to fix them, and do not
walk the result.

## Hand off

1. Commit `REVIEW.md` first (the walk's normal scoped commit), so the rulings are recorded
   before any code changes.
2. Run `kerbe:implement` in review-fix mode with the task source
   `{slice} QR-{n} FIX QUEUED rows`. It owns the workspace, dispatch, the per-task gate,
   the full-suite run and integration. Do not dispatch workers from the walk.
3. Every queued row in the QR goes into the one batch, across all tiers. Never split the
   batch across turns or ask between fixes.

## After the batch

`kerbe:implement` writes the result into each row:

- built and verified: `**FIXED {sha} {date}**`, keeping the ruling and adding the test that
  proves it
- not built: the row stays `**FIX QUEUED**` with a `Blocked:` note naming what failed

Report `{n} fixed · {n} blocked`. A blocked row is still owed, so do not call the QR
closed while one remains.

The batch gets no new `kerbe:review`. Update the slice's stale status docs and stop. If a
later review runs for another reason, it records the batch's commits as already closed
rows, citing the ruling, so the human is not asked to review their own fixes again.
