# The promise ledger — `PROMISES.md`

Normative format for kerbe:coverage. `scripts/verdict.py` is the reference parser: anything
it rejects is malformed, and a malformed ledger is fixed, not worked around.

## File shape

Header block, then one pipe-table:

```markdown
# Promise ledger — {slice}
LEDGER_VERSION: 1
MODE: audit            # or pre-impl
STATUS: FROZEN         # EXTRACTING until phase A converges
SOURCES: docs@<git-sha> · design@<snapshot-version or n/a>
EXTRACTION: converged (passes=3)   # or: capped (passes=5)

| id | promise | promised-by | spec | plan | code | evidence |
|----|---------|-------------|------|------|------|----------|
```

## Column vocabulary

Anything outside this vocabulary is a format error (`verdict.py` exits 2):

| Column | Values |
|---|---|
| `id` | `P-001` … unique, never reused. A demoted row is deleted and its id retires. |
| `promise` | one line, leaf-level, user-recognizable |
| `promised-by` | `figma:<node-id>` · `req:<REQ-ID>` · `doc:<file>#<heading>` · `plan:<task heading>` |
| `spec` | `?` (unverified) · `req:<id>` / `doc:…` (where the spec captures it) · `origin` (promise originates here) · `GAP` (designed, unspec'd) · `n/a` (no design leg by config) |
| `plan` | `?` (unverified) · `task:<heading>` · `origin` · `GAP` (spec'd, untasked) · `none-yet` (no plan file exists — valid pre-impl state) |
| `code` | `?` (unverified) · `present` · `partial` (shell: stub, unwired route, dead link, unimported stylesheet, class mismatch, designed divergence) · `absent` · `to-build` (pre-impl label for expected absence) |
| `evidence` | `file:line` + wiring proof for `present`; the observable break for `partial`/`absent`/`GAP` |

Hard rules:

- **No `|` characters inside any cell** — the parser is a pipe-table split.
- **Ids are never reused.** Deleting a row (quality-pass demotion) retires its id; the next
  new row takes the next number.
- A row's status is **where the relay breaks**: `spec: GAP` = design↔spec hop broken;
  `plan: GAP` = spec↔plan broken; `code: absent`/`partial` = plan↔code broken. "Present but
  functionally missing" (stub, unwired, unimported) is always `partial`, never `present`.
- Built-but-diverging-from-design (part of the promise undelivered) is `partial` with the
  divergence in evidence.

## Worked example

```markdown
# Promise ledger — cards
LEDGER_VERSION: 1
MODE: audit
STATUS: FROZEN
SOURCES: docs@fixture · design@fixture-1
EXTRACTION: converged (passes=3)

| id | promise | promised-by | spec | plan | code | evidence |
|----|---------|-------------|------|------|------|----------|
| P-001 | Filter chips row on index | figma:1:4 | GAP | ? | ? | no spec doc mentions filter chips |
| P-002 | Share-by-email popup on detail | req:REQ-CARD-004 | origin | GAP | ? | no plan task covers the share popup |
| P-003 | Download row on detail | figma:2:2 | req:REQ-CARD-002 | task:T3 Download row | absent | no template renders a download row |
| P-004 | Card hover style | req:REQ-CARD-005 | origin | task:T5 hover style | partial | templates/card/index.html.twig:6 renders .card-hover; _hover.scss defines it but app.scss never imports it |
```

Running `verdict.py` on this example prints `promises: 4` and `FINISHED: NO — 4 open rows`.

## The computed verdict

```
usage: verdict.py PROMISES.md
```

- **audit** mode: FINISHED ⇔ zero `GAP`, zero `absent`, zero `partial`, and zero `?` in any
  column.
- **pre-impl** mode: FINISHED ⇔ zero `GAP` and zero `?` in `spec` and `plan`
  (the `code` column is the to-build inventory, informational).
- Exit codes: `0` finished · `1` not finished · `2` malformed.

Paste the script's output verbatim into the run summary. Never restate, adjust, or
recompute its numbers by hand — the ledger is the count.

## The drop-file — `OUT_OF_SCOPE.md`

Beside the ledger. One line per real finding that has no `promised-by`:

```markdown
- [route:/kerbe:review] two live payment-API calls inside an open DB transaction (src/Service/Billing.php:88)
- [route:/kerbe:audit] ROUTES.md lists a route name the code renamed; the route itself works
- [route:/kerbe:bug] scheduled cancel never fires for past_due members — check whether a REQ specifies it
```

Drop-file entries are never counted, never totalled, and never block FINISHED. Cross-slice
observations (a sibling slice's feature) go here too.
