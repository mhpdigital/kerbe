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
| `promised-by` | `figma:<node-id>` · `design:<file>#<id>` (claude-design artboard leaf) · `req:<REQ-ID>` · `doc:<file>#<heading>` · `plan:<task heading>` |
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
- **`origin` means the promise enters the relay at or upstream of this column.** A
  plan-originated promise (`promised-by: plan:…`) therefore carries `spec: origin` —
  `GAP` is only for a hop the relay should have carried the promise across and didn't
  (`spec: GAP` = a *design-originated* promise no spec doc captures).
- **A plan task promises its seams and its cited cases — nothing else.** A
  `promised-by: plan:<task>` row (with `spec: origin`) is admissible only when it names
  one of:
  - a **seam**: an `Interfaces → Produces` entry (or, in a plan without Interfaces blocks,
    the task's named deliverable) that has a consumer — a later task, a specified test, a
    later slice, a route table, a schema, a payload someone parses, **or the user**. A
    user-reachable deliverable is always a seam, the user being its consumer: a screen, a
    page, a route, a command, an endpoint, a download. `T3 detail screen — route
    /gallery/detail opened from a grid item tap` is a row even when no requirement names a
    detail screen; that the plan invented the scope goes in the drop-file *as well*, never
    instead of the row.
  - a **case-table row** that cites a `REQ-` id or a design node.

  Everything else in a task — its `Decisions` block, its Step 3 fragments, the pattern it
  names, internal helpers, private methods, constructor wiring, memoisation, exception
  classes caught inside the task — is **approach**, revisable by the worker and by review,
  and is never a row. The test: could a reviewer change this without breaking another
  task, a requirement, or something the user reaches? If yes, it is approach. The test: could a reviewer change this without breaking
  another task or a requirement? If yes, it is approach. A planned seam that is unbuilt or
  unwired is still missing functionality and still a row; the *doc mismatch itself* (plan
  invented scope, or the spec is behind) is the reverse-direction observation — note that
  in the drop-file, never as a `spec: GAP`. (Narrowed 2026-09-16: the earlier rule made
  every plan line a promise, so a planner's own choices — a rate-limiter policy, an entry
  point — froze with the authority of a human decision and review could not revisit them
  without ledger surgery.)
- `absent` vs `partial`: `absent` = nothing of the promise exists; `partial` = something
  exists but a link in its wiring chain is broken (stub, unregistered route, dead link,
  unimported stylesheet, undeclared asset). When nothing exists at all, the row is
  `absent` even if the plan names it.
- **Every hop is checked against the promise itself, and a broken hop never blanks the
  ones after it.** A design-originated promise no spec captures can still be checked for
  a plan task and for code — so it carries `spec: GAP`, `plan: GAP` (if no task covers
  it), `code: absent` (if nothing is built). `?` means only "this check has not run or
  could not run", never "upstream was GAP so I stopped".
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
| P-001 | Filter chips row on index | figma:1:4 | GAP | GAP | absent | no spec doc mentions filter chips; no plan task covers them; no template renders chip markup |
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
