# Rwalk recording protocol

Read this before the first write to `REVIEW.md`. The QR row is the only walk state: do
not create a pointer or ledger.

## IDs and legacy QRs

The leftmost column is the permanent id: `B1…Bn` for Business logic, `G1…Gn` for Glue,
and `F1…Fn` for Flags. If an older QR lacks ids, add the header cell and back-fill ids in
table order; label unnumbered flags in appearance order. Never renumber or reuse an id.

A forced id already carrying an unstruck bold status stays closed unless the human
explicitly confirms reopening it. Reopening rewrites a recorded verdict, so ask once:

> B3 is RESOLVED (VERIFIED) {date} — re-open it?

## Tier 3 status

Write the status as its own paragraph directly below `### Boilerplate`, above the table:

```markdown
### Boilerplate — don't read, trust the full suite

**TIER 3 ACCEPTED {date}** — {n} files, behind {the QR's test evidence}

| File | What it does |
```

If an earlier walk clearly passed the opening turn because any `B`/`G`/`F` row is closed,
back-fill:

```markdown
**TIER 3 ACCEPTED (inferred from closed rows) {today}**
```

For challenged files, read them with tier-1 discipline. Add each finding as the next
permanent flag id, marked as raised by the walk. Do not reclassify the Boilerplate table.
Close tier 3 with the result:

```markdown
**TIER 3 ACCEPTED {date}** — {n} files, behind {evidence} · challenged: {file} → {F<n> | clean}
```

Record this immediately. A walk stopped after tier-3 acceptance must still commit it.

## Row verdicts

Strike the original row cells but never its id. Put the bold status outside the strike:

```markdown
| B2 | ~~`{file}` · `{method}()` (L81–110)~~ **RESOLVED (VERIFIED) {date}** | ~~{original why}~~ Confirmed: {mechanism} | ~~{open cmd}~~ |
```

The verdict must preserve the mechanism, not merely the conclusion. Reuse the pre-read
sentence, tightened by any discussion. “Confirmed correct” is insufficient; record what
binds the data, enforces the transition, reaches the destination, or otherwise makes the
row correct.

Write the edit the moment the human resolves the row. Do not wait for the end of the walk.

## Route discoveries

- Defect: invoke `kerbe:bug`, then record `**BUG-{id} RAISED**`.
- Intended-behaviour ruling: add it to the file's top-context `## Design decisions`.
- Reviewer-facing concern or deferral: add it to the review guide's Known Issues and its
  Code Reviews Completed row.
- Promised work that is absent: route to `kerbe:coverage`; it is not a walk finding.
- Mis-tiered Glue or Boilerplate touching auth, ownership, query filtering, state
  transitions, uploads, or money: review with tier-1 discipline and append a new flag
  stating that the QR mis-tiered it.

## Stop and completion

At `stop` or queue exhaustion, update Known Issues for deferrals and commit only the
slice's `REVIEW.md` (plus the review guide when this walk changed it), using pathspecs so
an unrelated shared index cannot leak into the commit:

```bash
git -C {planning_repo} commit -m "{slice}: rwalk QR-{n} — {ids} resolved" -- <slices>/{slice}/REVIEW.md [<slices>/{slice}/REVIEW_GUIDE.md]
```

Report `{n} resolved · {n} bugs raised · {n} deferred · {n} skipped`. Skipped rows remain
open, so say that the walk stopped with open items rather than calling it complete.
