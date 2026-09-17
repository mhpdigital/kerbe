---
name: rwalk
description: >-
  Use when a recorded review needs working through with a human — walks a QR's rows one
  turn at a time, reads each one first and opens it in the editor, then records the
  verdict in place and moves to the next, resuming wherever the last walk stopped.
disable-model-invocation: true
---

# kerbe:rwalk — walk a recorded review, row by row

`/kerbe:review` **produces** the QR; nothing consumed it. A recorded review is a queue of
decisions a human still has to make, and making them by hand — find the next unresolved
row, copy its open command, read the code cold, type the strikethrough — costs more
attention than the decisions themselves. This skill runs that queue: one row per turn,
pre-read so the human confirms or challenges instead of reading cold, struck in place the
moment it resolves.

Position in the lifecycle: **after** `/kerbe:review`, before merge. The walk records
verdicts; it never fixes code. A row that turns out to be a defect routes to `/kerbe:bug`
exactly as the review's own findings do.

## Setup

1. Read `kerbe.yml` (hard stop if missing). Resolve `planning_root`, `editor_cmd` /
   `editor_cmd_method`, and `workspace.*` for the branch → slice mapping.
2. Resolve the **slice**: from the argument, else from the branch name
   (`{workspace.branch_prefix}{slice}` / `{workspace.review_prefix}{slice}`), else ask.
   Hard stop if `{planning_root}/{slice}/REVIEW.md` does not exist — say to run
   `/kerbe:review` first.
3. Arguments are positional but **type-sniffed, not order-bound**: a bare token matching
   `^(QR-\d+/)?[BGF]\d+$` is a start id, anything else is the slice. Neither requires the
   other.

## Step 1 — parse the QR and resolve the position

Parse every QR in the file into an ordered queue: the Business-logic rows, then the Glue
rows, then the Flags. Boilerplate rows are never queued (see Step 2).

**A row's state lives in the row** — there is no ledger file and no walk state to keep in
sync. A row is **closed** when it carries an unstruck bold status
(`**RESOLVED**` / `**VERIFIED**` / `**FIXED**` / `**DEFERRED**` / `**FALSE POSITIVE**` /
`**EXPECTED**` / `**IMPROVED**` / `**REMOVED**` / `**BUG-{id} RAISED**`), and **open**
when it carries none. Resume is therefore always derivable: the first open row wins.

- **Target QR** = the newest QR with any open row. All QRs closed ⇒ report
  `{slice} QR-{n}: {m}/{m} closed — nothing to walk` and stop.
- **Start** = the first open row of that QR, scanning `B → G → F`.
- **Forced id** overrides both. An id that is already closed is not silently re-opened —
  ask once (`B3 is RESOLVED (VERIFIED) {date} — re-open it?`), because re-opening rewrites
  a recorded verdict. A bare id while more than one QR has open rows resolves against the
  newest and says which it chose; `QR-2/B3` qualifies it.

Announce the resolved position in one line before the first turn, so a wrong guess costs
one correction instead of a silent wrong start:

```
{slice} · QR-{n} · {total} items · {open} open · resuming at {id}
```

### Ids, and back-filling them

Rows are addressed by an **ID column**, leftmost: `B1…Bn` business-logic, `G1…Gn` glue,
`F1…Fn` flags. Ids are needed because line numbers are not stable handles — resolution
prose lands in the row and shifts every line below it — and because the resume pointer,
the commit message and any bug raised all need something to cite.

A REVIEW.md written before the ID column existed is **back-filled on first walk**: insert
the header cell and one id per row in table order, and label any unlabelled flag in order
of appearance. Never renumber an id that already exists, in either direction. Ids are
permanent: a struck row keeps its id, and a new row takes the next free number.

State is the bold status word, never a checkbox: a task-list checkbox does not render
inside a table cell, and the strikethrough convention already carries done-ness. Two
representations of one fact drift; one does not.

## Step 2 — the opening turn: tier 3

Boilerplate is the tier the review declares unread on purpose, so walking it row by row
spends the human on exactly what the tiering already decided not to spend them on. Open
with a single turn instead:

> Tier 3 — {n} files, trusted behind {the QR's test evidence}: {one-line grouping}.
> Accept the tiering, or name any to challenge?

Accepting closes tier 3 for this walk in one turn. A challenged file is read in-session
against the tier-1 discipline; anything found becomes a **new flag** (`F{n+1}`, noted as
raised by the walk) rather than a fabricated tier row, since the QR's tier tables record
what the review classified, not what the walk re-classified.

## Step 3 — the item turn

One item, one turn. The turn has three parts and then it **stops**.

1. **Pre-read.** Read the lines the row cites before presenting it, and lead with what
   they actually do — the mechanism, in a sentence or two — followed by the specific thing
   the human is being asked to judge. A row presented cold ("here is B4, go look") makes
   the human do the reading the walk exists to have already done; a row presented with a
   pre-verdict makes their turn a confirm-or-challenge. State honest uncertainty as
   uncertainty; a pre-verdict that is always "looks right" is worth nothing.
2. **Open it.** Run the row's Open cell verbatim, unescaping `\|` back to `|` first. A
   failed launch (editor not running, path moved) is reported and never blocks the turn —
   say the path instead.
3. **Stop.** Wait. Never present the next row in the same turn, and never resolve a row
   the human has not answered on.

Keep the presentation short — the row, the mechanism, the question. The code is in their
editor; re-pasting it is noise.

## Step 4 — the verbs

| Input | Effect |
|---|---|
| `ok` (or bare Enter) | strike the row, record `**RESOLVED (VERIFIED) {date}**` with the mechanism, next item |
| *any prose or question* | stay on the row, discuss, write nothing — the verdict accumulates from the discussion |
| `bug` | route to `/kerbe:bug`, strike with `**BUG-{id} RAISED**`, next item |
| `defer` | strike with `**DEFERRED {date}**` + reason, mirror into the review guide's Known Issues, next item |
| `skip` | leave the row untouched and open, next item |
| `back` | return to the previous item |
| `stop` | commit and report `{closed}/{total}` |

Anything not in the table is prose: discuss it, stay on the row.

## Step 5 — recording the verdict

Per the strikethrough convention, the original stays in place, struck; the status is bold
and **unstruck**; the id cell is never struck, so the row stays addressable and greppable:

```
| B2 | ~~`{file}` · `{method}()` (L81–110)~~ **RESOLVED (VERIFIED) {date}** | ~~{original why}~~ Confirmed: {mechanism} | ~~{open cmd}~~ |
```

**The verdict must carry substance, not a conclusion.** "Confirmed correct" records
nothing a later reader can check; "the existing-row lookup runs through
`applyTenantScope()`, which binds the user from the security token, so no caller input can
select another member's row" records why it is correct and survives the reviewer
forgetting. An `ok` still gets the mechanism sentence from the pre-read.

Write the edit **the moment the row resolves**, not at the end: a walk that dies mid-way
must leave a truthful file. Commit once, at `stop` or completion, scoped by pathspec (the
index is shared across concurrent sessions):

```bash
git -C {planning_repo} commit -m "{slice}: rwalk QR-{n} — {ids} resolved" -- <slices>/{slice}/REVIEW.md
```

**What the discussion produces goes where it belongs:** a defect → `/kerbe:bug`; a ruling
about intended behaviour → the file's `## Design decisions` top-context section; something
a human reviewer needs to know → the review guide's Known Issues and its Code Reviews
Completed row. A promise that turns out not to be built is **not** a walk finding — that
is the coverage ledger's denominator, and it routes to `/kerbe:coverage`.

## Step 6 — glue batching

Tier 2 is defined as flow-only, ~30s a file; one turn each spends more attention on the
turn-taking than on the code. Present glue **five rows to a turn**, each with its
one-line pre-read, and open the first. A single `ok` closes all five. Any prose about one
row drops that row — only that row — into the Step 3 item turn, and the rest of the batch
waits.

Tier 1 and Flags are never batched. They are the rows the review exists to produce.

## Step 7 — finishing

When the queue empties, report the tally and what it produced (`{n} resolved · {n} bugs
raised · {n} deferred · {n} skipped`), update the review guide's Known Issues for anything
deferred, and commit. Rows left `skip`ped keep the QR open — say so plainly rather than
reporting a walk as complete.

## Rules

- **Never edit application code during a walk.** The walk records verdicts; fixes route to
  `/kerbe:bug` or back through the plan. A walk that starts fixing stops being a review
  pass and loses the human's place in it.
- One turn is one decision point. Never walk ahead of the human, and never mark a row they
  did not answer on.
- Never move a resolved row, never collect them into a "done" section, never prefix with
  ✅ — strike in place, status unstruck beside it.
- Never renumber an existing id, and never reuse one.
- Re-tiering is a finding about the QR, not a silent correction: a glue or boilerplate row
  that touches auth, ownership, query filtering, state transitions, uploads or money gets
  the tier-1 discipline for its turn **and** a flag saying the review mis-tiered it.
- The walk never asserts completeness of the review itself. It closes the rows the review
  recorded; whether the review found everything is `/kerbe:review`'s adversarial pass.
