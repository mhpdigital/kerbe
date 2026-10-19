# Turn variants

## Glue batching

For Glue only, batch up to five rows with a one-line pre-read each and open the first. One
`ok` closes the batch. Prose about one row moves only that row into a single-item turn;
the others wait. Never batch Business logic or Flags.

## Tier 3 opening turn

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
