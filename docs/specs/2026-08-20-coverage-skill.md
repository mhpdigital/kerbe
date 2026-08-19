# kerbe:coverage — specification

> Decided 2026-08-20, from the post-mortem of the reference project's frozen coverage skill
> (20 skill commits Jul 4 – Aug 19 2026; 51 loop commits; four session reconstructions).
> This spec supersedes the predecessor's design. The predecessor stays frozen and unused.

## The one question

**Is anything that the approach documentation promises missing from the build?**

Not "is the code good", not "are the docs accurate", not "are the tests deep". The skill exists
so that nobody discovers missing functionality by stumbling over it later. Every other real
concern an agent notices is routed, uncounted, to a drop-file.

## The root defect this design removes

The predecessor had no denominator: "what was promised" was re-derived inside each review
round's context, so no two rounds provably searched the same space and the gap count measured
the round's brief, model, and appetite. Every enforcement mechanism it accreted (frozen
invocation files, a dispatch guard, snapshot caches, model pinning, loop epochs, ledger
arithmetic rules) compensated for that one defect.

**The fix is structural: the inventory of promises becomes an explicit, frozen, committed
artifact — the promise ledger — and the verdict is computed by counting its rows, never
asserted by any agent.**

## Pairwise hops, built from the ground up

The relay is design → spec → plan → code. It is checked as **pairwise two-column mappings
accumulated in the ledger**, not as overlapping three-way checks. Each promise row enters at
its source column and is carried rightward one hop at a time:

- **design ↔ spec** — is the designed leaf captured in the spec docs? (`spec` column)
- **spec ↔ plan** — does a plan task cover the spec item? (`plan` column)
- **plan ↔ code** — is the planned thing present *and wired*? (`code` column)

A row's status is *where the relay breaks*. Adjacent hops share a column by construction, so
the full chain is covered without any triangle bookkeeping.

Only the forward direction is counted: a promise with nothing downstream. Reverse observations
(code with no plan origin, plan tasks with no spec origin) are not missing functionality — they
go to the drop-file, routed to `kerbe:audit` / `kerbe:review`.

## Two phases with different shapes

### Phase A — EXTRACT (the only place a loop runs)

Produce the promise ledger `PROMISES.md` in the slice's planning folder: **one row per
leaf-level promise**, from the sources the project config declares (design snapshot via the
design adapter; spec docs; plan). Leaf-level means the predecessor's #1-blind-spot rule: a
designed page frame contributes one row per interactive leaf (button, toggle, action row,
picker, link), never one row per page.

Extraction is bounded by the size of the source documents, so a convergence loop is safe here:

1. Dispatch one extractor per source class (design, spec docs, plan). Merge and dedupe
   (same `promised-by` citation + same leaf = one row).
2. Dispatch a fresh full extractor against the same frozen sources. If it proposes rows the
   ledger lacks, add them and repeat.
3. Stop after **two consecutive passes that add zero rows**, or at a cap of 5 passes
   (report `EXTRACTION: capped` honestly).
4. Freeze the ledger: stamp `STATUS: FROZEN` plus the source pin (git commit of the docs,
   design-snapshot version), and commit it. The frozen ledger is the loop's denominator and
   diffs between runs are meaningful.

The design snapshot is fetched **once** per extraction by the design adapter and read from
disk thereafter (ported snapshot script). A new design version ⇒ a new extraction ⇒ a
diffable new ledger — the diff *is* the design change.

### Phase B — VERIFY (no loop, ever)

Each row is verified independently against the frozen sources and the code:

- fill `spec` / `plan` / `code` columns per the vocab below,
- `code: present` requires **wiring evidence** per the stack adapter's recipes
  (existence ≠ wired),
- every verdict cites evidence (`file:line` or the reason for the break).

Verification is embarrassingly parallel and idempotent — re-running a row always produces the
same answer from the same sources, so concurrent workers cannot corrupt anything.

**Quality pass (bounded, not a loop):** a second, independent agent
(a) re-verifies every `GAP`/`absent`/`partial` row **including its `promised-by` citation** —
a stretched promise is the one way a non-coverage finding sneaks in — and
(b) spot-audits a sample of `present` rows (10%, minimum 5).
Demoted rows move to the drop-file and the ledger row is deleted; the verdict is recomputed.

**No agent ever asserts "nothing is missing."** The most expensive claim in the predecessor
has no author here: `scripts/verdict.py` computes the verdict from the ledger.

## The promise ledger — `PROMISES.md`

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

Column vocabulary (anything else is a format error — `verdict.py` exits 2):

| Column | Values |
|---|---|
| `id` | `P-001` … unique, never reused |
| `promise` | one line, leaf-level, user-recognizable |
| `promised-by` | `figma:<node-id>` · `req:<REQ-ID>` · `doc:<file>#<heading>` · `plan:<task heading>` |
| `spec` | `?` (unverified) · `req:<id>` / `doc:…` (where the spec captures it) · `origin` (promise originates here) · `GAP` (designed, unspec'd) · `n/a` (no design leg by config) |
| `plan` | `?` (unverified) · `task:<heading>` · `origin` · `GAP` (spec'd, untasked) · `none-yet` (no plan file exists — valid pre-impl state) |
| `code` | `?` (unverified) · `present` · `partial` (shell: stub, unwired route, dead link, unimported stylesheet, class mismatch) · `absent` · `to-build` (pre-impl label for expected absence) |
| `evidence` | `file:line` + wiring proof for `present`; the observable break for `partial`/`absent`/`GAP` |

The predecessor's gap groups map onto column values: group (a) = `spec: GAP`,
(b) = `plan: GAP`, (c) = `code: absent`, "present but functionally missing" = `code: partial`.
Group (d) (built but diverging from design so part of the promise is undelivered) =
`code: partial` with the divergence in evidence.

## The computed verdict — `scripts/verdict.py`

```
usage: verdict.py PROMISES.md
```

Parses the ledger, validates the vocabulary, prints:

```
kerbe:coverage verdict — cards (mode: audit)
promises: 143
hop design->spec : 3 GAP
hop spec->plan   : 2 GAP
hop plan->code   : 128 present · 9 partial · 4 absent · 0 unverified
FINISHED: NO — 18 open rows: P-004 P-011 P-017 …
```

- **audit** mode: FINISHED ⇔ zero `GAP`, zero `absent`, zero `partial`, and zero `?` in any
  column.
- **pre-impl** mode: FINISHED ⇔ zero `GAP` and zero `?` in `spec` and `plan`
  (the `code` column is the to-build inventory, informational).
- Exit codes: `0` finished · `1` not finished · `2` malformed ledger (bad vocab, duplicate
  ids, missing header fields). Malformed is loud, never guessed around.

After fixes land, re-verify the affected rows against the **same frozen ledger** and recompute.
The denominator does not move until a new extraction is deliberately run.

## Scope containment is physical

A finding that has no promise row **cannot be counted** — there is nowhere to put it. Anything
real an agent notices without a `promised-by` goes to `OUT_OF_SCOPE.md` beside the ledger, one
line each, routed to the owning skill (`kerbe:review`, `kerbe:bug`, `kerbe:audit`), never
totalled. Cross-slice observations (a sibling slice's feature) go there too — the predecessor's
scope-conflation guard, kept.

## Modes

Same ledger, same hops; the mode changes labels and the FINISHED rule only:

- **pre-impl** — code absence is `to-build`, not a defect; the deliverable is a complete
  spec+plan (no `GAP`s) plus the to-build inventory. The skill **reports only** — closing
  gaps in docs/plan is a separate, user-approved step (a deliberate narrowing vs the
  predecessor, which edited docs).
- **audit** — `absent`/`partial` are defects to fix (fixing is a separate step).
- Auto-detect per slice when unstated: probe the configured `code_roots` for the slice's
  artifacts; substantially none ⇒ pre-impl.

v1 runs **one slice per invocation**. A feature spanning slices = one run per slice;
cross-slice seams land in the drop-file.

## Project independence — the config seam

The skill body contains **no project path, doc name, stack probe, or design-tool call**.
Everything resolves through `kerbe.yml` at the target project root:

```yaml
kerbe:
  planning_root: planning/slices          # slice folders live at {planning_root}/{slice}
  promise_sources:
    spec_globs: ["*.md"]                  # classified by content, not filename
    plan_glob: "*PLAN*.md"                # the frozen task list; progress ledgers excluded
  design:
    adapter: figma                        # figma | none
    cache_dir: design-cache               # relative to the slice folder
    file_key: "<figma-file-key>"
    token_env: FIGMA_API_TOKEN            # or token_cmd: "<shell command printing the token>"
  stack:
    adapter: symfony                      # symfony | flutter
    code_roots: ["symfony/"]
```

- **Design adapters** (`adapters/design/{figma,none}.md`): how to snapshot the design once
  per extraction and how to enumerate leaves from the snapshot. `none` ⇒ no design-sourced
  rows and `spec: n/a` is not a gap.
- **Stack adapters** (`adapters/stack/{symfony,flutter}/verify.md`): what `present` **and
  wired** means on that stack. Symfony: route defined and reachable, template rendered by a
  controller, stylesheet imported by the manifest, importmap entry present, class the template
  renders has a rule in the authored CSS. Flutter: widget reachable in the tree, route
  registered in the router table, asset declared in `pubspec.yaml`, provider/bloc actually
  wired. The recipes are the portable form of the predecessor's battle-tested
  existence≠wired catalog.

## Runtime cost profile

Extraction: `sonnet`. Verification and the quality pass: `haiku` (per-row work is mechanical
and self-evidencing). The verdict: a script. No model ever holds the verdict, so the
predecessor's cheap-model false-all-clear cannot recur by construction. Model choice is
recorded in the ledger header for the record, but changing it does not invalidate anything —
rows are re-runnable facts, not signals.

## The fixture harness (breaks the meta-loop)

Two mini fixture projects ship in the repo with **planted, known** gaps and **planted decoys**:

- `fixtures/symfony-mini/` — planted: a designed leaf that is spec'd+planned but unbuilt; a
  designed leaf no spec captures; a spec'd requirement no plan tasks; a dead-linked/unwired
  route; an unimported stylesheet whose class the template renders; a stub handler.
  Decoys (must NOT be counted): an unused public method; a test with no assertions; stale
  checkboxes in a done-criteria doc.
- `fixtures/flutter-mini/` — planted: a designed leaf unbuilt; a planned route not in the
  router table; a spec'd asset missing from `pubspec.yaml`. Decoy: an unused function.

Each fixture carries `EXPECTED.json`: `require` patterns (a row must exist matching column +
evidence substring) and `forbid` patterns (no counted row may match). `fixtures/score.py`
scores a produced ledger + drop-file against it, deterministically.

**Acceptance for the skill — and for every future edit to it:** on both fixtures, all
`require` patterns hit, zero `forbid` hits, and the verdict identical across two consecutive
runs. Skill changes are never debugged on a live project.

## Deliberately not ported

The open-ended adversarial hunt as the primary mechanism; frozen round-invocation files and
the dispatch guard; loop numbers/epochs/dispatch logs; model-pinning rules;
`total_gaps` arithmetic and the CONVERGED status grammar; doc-accuracy auditing (belongs to
`kerbe:audit`); editing spec docs in pre-impl mode; multi-slice orchestration (v1).
