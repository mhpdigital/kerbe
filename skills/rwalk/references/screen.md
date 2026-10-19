# Rwalk review screen (`--screen`)

Follow this instead of the tier 3 and item turns. Verdicts are collected in a browser
screen; the scripts below are skill-relative under `scripts/`.

## Fallback

Any of these prints exactly one line, `Screen failed: {error}. Continuing in the terminal.`,
and then runs the terminal walk from the current position:

1. The bundle step exits non-zero (use its `error: …` stderr text).
2. The server prints no URL line.
3. The server exits with no summary line.
4. The summary says `finished: false` (idle): say the screen timed out as the error.
   Keep every verdict already written.

## Run

1. Resolve the slice and the position exactly as the main skill does, and announce it.
2. Read `kerbe.yml`: `planning_root`, `workspace.base_branch`, `editor_cmd`,
   `rwalk.discuss_cmd`. If `rwalk.discuss_cmd` is unset, use your host's default as listed
   in `kerbe.yml.example`.
3. Check the bundle builds, into a fresh directory from `mktemp -d`:
   `scripts/bundle.py --review {REVIEW.md} --repo {code repo} --base {base_branch} --slice {slice} --out {dir}`.
   On failure, fall back.
4. Start the server as a background process, keeping its stdout:
   `scripts/serve.py --review {REVIEW.md} --repo {code repo} --base {base_branch} --slice {slice} --discussion {slice folder}/REVIEW-discussion.md --discuss-cmd "{discuss_cmd}" [--editor-template "{editor_cmd}"]`.
   Read its first stdout line, a JSON object with the `url`; if none arrives, fall back.
5. Print the URL for the human, then wait for the process to exit. Run it as a background
   process you are notified about on exit; do not poll it on a short timer, and set no
   time limit.
6. On exit its last stdout line is a summary: `finished`, `reason`, and the counts
   verified, fix, bug, defer, open. If missing or `finished` is false, fall back.

## After the screen exits

1. Raise each `BUG PENDING` row via `kerbe:bug`, and replace its status with
   `BUG-{id} RAISED`.
2. Mirror each `DEFERRED` row to Known Issues.
3. Commit per [recording.md](recording.md), with `REVIEW-discussion.md` added to the
   pathspec when it exists.
4. Report the tally.
5. Run the fix batch per [fix-batch.md](fix-batch.md) straight away when any row is
   `FIX QUEUED`. Do not ask first.

A tier 3 challenge made from the screen ("Challenge in the terminal") continues as the
terminal opening turn for tier 3, after the steps above.
