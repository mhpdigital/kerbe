# Rwalk review screen (`--screen`)

Follow this instead of the tier 3 and item turns. Verdicts are collected in a browser
screen; the scripts below are skill-relative under `scripts/`.

## Fallback

Any of these prints exactly one line, `Screen failed: {error}. Continuing in the terminal.`,
then runs "After the screen exits" steps 1 and 2 (raise `BUG PENDING` rows, mirror
`DEFERRED` rows), then runs the terminal walk from the current position:

1. `serve.py` exits 2 before the URL line (use its `error: …` stderr text; it builds the
   bundle itself, so a bundle failure lands here).
2. The server prints no URL line, or exits with no summary line.
3. The summary says `finished: false` (idle): say the screen timed out as the error.
   Keep every verdict already written.

If the human says the screen is unusable, kill the server process and take case 2
("exits with no summary line").

## Run

1. Resolve the slice and the position exactly as the main skill does, and announce it.
   A forced start id runs the terminal walk instead; do not open the screen.
2. Read `kerbe.yml`: `planning_root`, `workspace.base_branch`, `editor_cmd`,
   `rwalk.discuss_cmd`. If `rwalk.discuss_cmd` is unset, use your host's default as listed
   in `kerbe.yml.example`.
3. Start the server as a background process, keeping its stdout:
   `scripts/serve.py --review {REVIEW.md} --repo {code repo} --base {base_branch} --slice {slice} --discussion {slice folder}/REVIEW-discussion.md --discuss-cmd '{discuss_cmd}' [--editor-template '{editor_cmd}']`.
   Shell-quote `discuss_cmd` and `editor_cmd` in single quotes, writing each `'` inside
   them as `'\''`. Read its first stdout line, a JSON object with the `url`; if none
   arrives, fall back.
4. Print the URL for the human, then wait for the process to exit. Run it as a background
   process you are notified about on exit; do not poll it on a short timer, and set no
   time limit. On a multi-user host the token URL is visible to other local users in the
   process list.
5. On exit its last stdout line is a summary: `finished`, `reason`, and the counts
   verified, fix, bug, defer, open. `reason` is `finish` (Finish walk), `challenge`
   (Challenge in the terminal) or `idle` (timed out). If missing or `finished` is false,
   fall back. The counts are totals for the whole QR, not this walk; they map to the
   tally as verified → resolved, fix → fixes queued, bug → bugs raised, defer → deferred,
   open → skipped.

## After the screen exits

1. Raise each `BUG PENDING` row via `kerbe:bug`, and replace its status with
   `BUG-{id} RAISED`.
2. Mirror each `DEFERRED` row to Known Issues.
3. Commit per [recording.md](recording.md), with `REVIEW-discussion.md` added to the
   pathspec when it exists.
4. Report the tally.
5. Run the fix batch per [fix-batch.md](fix-batch.md) straight away when any row is
   `FIX QUEUED`. Do not ask first.
6. If `reason` is `challenge`, run the tier 3 opening turn as the ask case (case 4 in
   [turns.md](turns.md)), never the inferred case 3.
