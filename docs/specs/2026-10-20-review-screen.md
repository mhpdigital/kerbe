# rwalk review screen

**Date:** 2026-10-20 · **Release:** 0.13.0 · **Skills:** `rwalk` (plus `recording.md`)

## The problem

Each rwalk turn spans three places. The agent explains the row in the terminal and opens
the editor at the line. The human reads the code in the editor and answers in the
terminal. The explanation, the code and the discussion are never on one screen, the human
cannot see where they are in the QR, and moving between rows means typing `back` and
`skip`.

Review is the bottleneck once implementation is delegated. Making each row faster to judge
makes delegation pay off.

## The change

`/kerbe:rwalk --screen` runs the same walk in a local browser window. One page per row,
top to bottom:

1. **Why this row matters** (the QR's Why cell) and **What the code does** (a mechanism
   pre-read).
2. The **diff** for that row, long lines wrapped, no sideways scrolling. **Open in editor**
   stays available.
3. A **discussion** with an agent that can read the repo but not write to it. When it
   proposes choices it ends with a numbered `O0…On` list, and each option has a **Pick**
   button.
4. The **verdict**: Verified, Queue fix, Raise bug, Defer, Skip. Keys `a f b d s`, rows
   `j k`.
5. **Queue fix** opens a panel: the chosen option (if any), a multi-line **decision
   detail**, and **proves it**. It previews the exact `REVIEW.md` text before queueing.

A left rail lists every row grouped B / G / F with its status. **Finish** closes the
server and hands back to the terminal, which commits, raises bugs and runs the fix batch
exactly as today.

The terminal walk is unchanged and remains the fallback for headless and remote sessions.

## Break glass

The terminal walk is the break-glass path. It must work when the screen does not.

1. **Default stays terminal.** `/kerbe:rwalk` with no `--screen` runs today's terminal walk.
   Its instructions stay in `SKILL.md` and `references/recording.md` and never depend on
   any screen script, so a broken `bundle.py`, `serve.py` or `index.html` cannot stop it.
2. **Automatic fallback.** If `bundle.py` fails, `serve.py` does not print its URL line, or
   `serve.py` exits without a summary line, rwalk says the screen failed (one line, with the
   error) and continues the walk in the terminal from the same position. No question.
3. **Mid-walk switch.** Every verdict is written to `REVIEW.md` as it is given, so closing
   the window or killing the server loses nothing. Re-running `/kerbe:rwalk` without
   `--screen` resumes at the next open row. `BUG PENDING` rows left by the screen are raised
   by the terminal walk before it continues.

## How it runs

```
rwalk --screen
  → bundle.py   parse the QR, slice git diff per row → bundle JSON (mktemp, never a dotfolder)
  → serve.py    127.0.0.1, random port, per-run token, opens an app window
      GET  /                index.html
      GET  /api/bundle      rows + live statuses re-read from REVIEW.md
      GET  /api/preread     mechanism pre-read for one row (pending | ready)
      POST /api/verdict     rewrite one row in REVIEW.md
      POST /api/ask         run the discussion command, stream NDJSON back
      POST /api/open        classify and launch the editor for one row
      POST /api/finish      print the tally and exit
  → serve.py exits → rwalk resumes in the terminal: commit, kerbe:bug, fix batch
```

The host agent starts `serve.py` as a background process and waits for it to exit. While
the screen is open the terminal session is idle.

**Discussion bridge.** Each question runs `rwalk.discuss_cmd` as a subprocess (argv split,
no shell) with the prompt on stdin and the answer on stdout. The prompt carries the row,
its diff, the earlier questions and answers for that row, and the answer-format rule.
Follow-ups keep context because the server replays the row's history into the prompt, not
through any harness's resume flag, so the bridge is harness-neutral. Defaults:

| Host | `discuss_cmd` |
|---|---|
| Claude Code | `claude -p --model sonnet --allowedTools Read,Grep,Glob` |
| Codex | `codex exec --sandbox read-only -` |

The discussion agent is not the terminal session. It knows the row, the diff and what it
reads in the repo, not what was said in the terminal earlier. Every question draws on the
plan window. `discuss_cmd` can point at any command that reads stdin and writes stdout.

**Pre-reads.** At start the server fills each row's "What the code does" in a background
thread through the same bridge, current row first. Results live in memory for the run.

**Install.** Nothing beyond Kerbe: one HTML file and three Python stdlib scripts in
`skills/rwalk/`. Python 3 is already required. Chrome or Edge gives the app window
(`--app=`), any other browser gets a normal tab.

## Recording

`REVIEW.md` rows remain the only walk state. The screen keeps no pointer file, database
or browser storage, so the terminal walk can resume from wherever the screen stopped.

| Verdict | Row text (syntax per `references/recording.md`) |
|---|---|
| Verified | `**RESOLVED (VERIFIED) {date}**` · `Confirmed: {mechanism}` |
| Queue fix | `**FIX QUEUED {date}**` · `Ruled: {Ox: option text}<br>{detail} · proves it: {proves}` |
| Raise bug | `**BUG PENDING {date}**` · `Bug: {detail}` — terminal runs `kerbe:bug` after Finish and replaces it with `BUG-{id} RAISED` |
| Defer | `**DEFERRED {date}**` · `Deferred: {reason}` — terminal mirrors it to Known Issues after Finish |
| Skip | nothing written |

User text is cell-escaped: `|` → `\|`, line breaks → `<br>`. Discussions are appended to
`REVIEW-discussion.md` beside `REVIEW.md`, one `## QR-n/ID — title` section per row, and
committed with it.

## Decisions

| | Decision | Why |
|---|---|---|
| D1 | The diff is `git diff {base}...{Reviewed at}` rendered in the page, wrapped. | No install, and it is the diff the review recorded. |
| D2 | Extend rwalk with `--screen`; no new skill. | One resume rule, one recording rule, one gate. The fix batch is reused unchanged. |
| D3 | Why and mechanism above the code; mechanism pre-read in the background at start. | The reason is read before the code; no wait when moving to the next row. |
| D4 | Open never runs the QR's Open cell. The server resolves file and line from the row and launches only what `classify_editor_open.py` allows, as argv, no shell. | The browser must not become a way to run commands. |
| D5 | Localhost only, random port, per-run token in the URL fragment sent as a header, `Host` checked, exit on Finish or 30 min idle. | The server writes to the repo. |
| D6 | Bug clicks record `BUG PENDING`; `kerbe:bug` runs in the terminal after Finish. | Impact analysis needs the full agent. |
| D7 | Queue fix records chosen option, multi-line detail and proves it. The detail is the fix worker's brief. | Rulings are often "O2, with these conditions". |
| D8 | Local web app opened as an app window (`--app=`), falling back to a tab. Not Electron or Tauri. | Desktop feel with no build chain; stays stdlib-only and ships through the plugin cache. |
| D9 | Picking an option fills the option, not the detail. The detail is written by the human. | A drafted detail would read as the human's ruling. |
| D10 | Tier 3: the screen offers Accept only. A challenge is done in the terminal walk. | Challenged files need tier-1 reading and new flags, which is agent work. |
| D11 | v1 shows each answer when the command finishes, with an elapsed-time indicator. Token streaming is a later, per-harness option. | Plain stdout is harness-neutral; streaming formats differ per CLI. |

## Not in scope

- Spec excerpts in the bundle. The discussion agent reads spec files itself.
- Building fixes from the screen. The terminal fix batch owns that.
- difftastic or any external diff tool.
- Multiple repos or slices in one window.
