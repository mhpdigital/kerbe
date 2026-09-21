---
name: rwalk
description: >-
  Use when a recorded review needs working through with a human — walks a QR's rows one
  turn at a time, pre-reads and opens each item, records verdicts in place, and resumes
  from the first unresolved row.
---

# kerbe:rwalk — walk a recorded review

`kerbe:review` produces a queue of decisions; this skill spends it with the human after
review and before merge. It records verdicts but never fixes application code. Defects
route to `kerbe:bug`.

## Setup

1. Read `kerbe.yml`; missing is a hard stop. Resolve `planning_root`, `editor_cmd` /
   `editor_cmd_method`, and `workspace.*`.
2. Resolve the slice from the arguments, else the branch
   (`{workspace.branch_prefix}{slice}` / `{workspace.review_prefix}{slice}`), else ask.
   Hard stop if `{planning_root}/{slice}/REVIEW.md` is missing: run `kerbe:review` first.
3. Arguments are type-sniffed, not order-bound: `^(QR-\d+/)?[BGF]\d+$` is a start id;
   another token is the slice.
4. Before the first write to `REVIEW.md`, read
   [references/recording.md](references/recording.md). Read its edge-case section earlier
   if the QR lacks ids, tier 3 was challenged, a closed id was forced, or a row was
   mis-tiered.

## Resolve the position

Parse every QR in file order. Its queue is Business logic, then Glue, then Flags;
Boilerplate is handled once as tier 3. Rows are addressed by their permanent leftmost
ids: `B1…`, `G1…`, `F1…`.

A row is closed only when it has an unstruck bold status: `RESOLVED`, `VERIFIED`,
`FIXED`, `DEFERRED`, `FALSE POSITIVE`, `EXPECTED`, `IMPROVED`, `REMOVED`, or
`BUG-{id} RAISED`. Otherwise it is open. Tier 3 is closed by its bold status line directly
under `### Boilerplate`.

- Target the newest QR with anything open. If all are closed, report
  `{slice} QR-{n}: {m}/{m} closed — nothing to walk` and stop.
- Start at its first open row in `B → G → F` order.
- A forced id overrides this. If it is already closed, ask once before reopening it. A
  bare id with multiple open QRs means the newest; say which QR was chosen.

Before presenting anything, announce:

```text
{slice} · QR-{n} · {total} items · {open} open · tier 3 {accepted {date} | open} · resuming at {id}
```

## Opening turn: tier 3

Run this only while tier 3 is open:

1. Status line present: skip to the first row.
2. Boilerplate table empty: skip and write nothing.
3. No status but any `B`/`G`/`F` row is closed: infer an earlier walk passed this turn;
   record the inferred acceptance per the reference, then continue.
4. Otherwise ask one question and stop:

> Tier 3 — {n} files, trusted behind {the QR's test evidence}: {one-line grouping}.
> Accept the tiering, or name any to challenge?

Record acceptance immediately. Read challenged files with tier-1 discipline; a finding is
a new flag, not a fabricated tier row. Then record the challenge result and close tier 3.

## Item turn

One decision point per turn, then stop:

1. **Pre-read** the cited lines. Explain the actual mechanism in one or two sentences,
   state honest uncertainty, and ask the specific question. Do not merely point at code or
   default every pre-verdict to “looks right.”
2. **Open** the row by running its Open cell verbatim after changing `\|` back to `|`.
   Launch failure does not block the turn; report the path.
3. **Stop and wait.** Never present the next row or resolve an unanswered row.

Keep it short: row, mechanism, question. The code is already in the editor.

For Glue only, batch up to five rows with a one-line pre-read each and open the first. One
`ok` closes the batch. Prose about one row moves only that row into a single-item turn;
the others wait. Never batch Business logic or Flags.

## Human verbs

| Input | Effect |
|---|---|
| `ok` or bare Enter | Record `RESOLVED (VERIFIED)` with the pre-read mechanism; next item |
| prose or a question | Discuss; stay on this item and write nothing |
| `bug` | Route to `kerbe:bug`, record `BUG-{id} RAISED`; next item |
| `defer` | Record `DEFERRED` with reason and mirror to Known Issues; next item |
| `skip` | Leave open; next item |
| `back` | Return to the previous item |
| `stop` | Commit and report the tally |

Anything else is discussion, not a verdict.

## Recording and finish

Follow [references/recording.md](references/recording.md) for exact row/status syntax,
id back-filling, challenged tier 3, decision routing, the scoped commit, and the final
tally. Write each verdict immediately; commit once at `stop` or when the queue empties.
Skipped rows keep the QR open—never report that walk as complete.

## Non-negotiable rules

- Never edit application code. A defect routes to `kerbe:bug`; missing promised work
  routes to `kerbe:coverage`.
- Never mark a row the human did not answer on, and never walk ahead of them.
- Keep resolved rows in place: id unstruck, original cells struck, status unstruck. Never
  add checkboxes or ✅, renumber an id, or reuse one.
- Treat auth, ownership, query filtering, state transitions, uploads, or money as tier 1.
  If such a row was Glue or Boilerplate, also add a mis-tiering flag.
- Close only the review's recorded rows. `rwalk` never claims the review itself was
  complete.
