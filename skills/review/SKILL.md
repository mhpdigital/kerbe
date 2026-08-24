---
name: review
description: >-
  Use when a slice's diff is ready for review — categorises every changed file by risk
  tier, produces per-line open commands for the business-logic rows, runs an adversarial
  pass over its own review, and records it as a numbered QR in the slice's REVIEW.md.
disable-model-invocation: true
---

# kerbe:review — risk-tiered code review, recorded

Reviews a slice's diff so a human spends attention where bugs live: business logic read
line by line, glue read for flow, boilerplate trusted — behind a full-suite run, never a
scoped one. The tier *concept* and the review discipline live here; every classification
*rule* lives in the stack adapter's `risk-tiers.md`. Config seam:
`{plugin}/skills/coverage/references/config.md`.

Position in the lifecycle: **after** the coverage verdict, before merge. Reviewing a
branch still missing promised functionality spends the reviewer on what is there instead
of what is not — run `/kerbe:coverage` first. Review findings are code defects, not
missing promises: they route to `/kerbe:bug`, never into the coverage ledger.

## Setup

1. Read `kerbe.yml` (hard stop if missing). Resolve `planning_root`, the stack adapter
   (`risk-tiers.md` for classification, `commands.md` for the full-suite trigger), the
   optional `editor_cmd`, and `workspace.*` for the diff base.
2. Resolve the slice: from the branch name (`{workspace.branch_prefix}{slice}` /
   `{workspace.review_prefix}{slice}`), else ask. Verify `{planning_root}/{slice}/`
   exists.
3. Resolve the diff. The user may give a branch or a commit range; with neither, diff the
   current branch against its merge-base with `workspace.base_branch`:
   ```bash
   git diff $(git merge-base HEAD {base_branch})...HEAD --stat
   ```
   Empty diff ⇒ say so and stop. Very large diff ⇒ process per file, never sample.

## Step 1 — read the slice's intent first

Before reading code, read the slice's spec docs — requirements, security, decisions,
routes, done-criteria (whatever the doc set carries; classify by content). The review's
highest-value findings are **spec deviations** — access level drift, ownership drift,
scope drift — and a code-only pass cannot see them.

## Step 2 — categorise every changed file

Assign each file exactly one tier per the stack adapter's `risk-tiers.md`, applying its
always-tier-1 overrides last (they win). Nothing is silently dropped: the tier tables
must union to the full `--name-only` list.

| Tier | Read discipline |
|---|---|
| 1 business-logic | **every line** — with specific line references and a per-row reason |
| 2 glue | signatures and flow only — right service, right route, right wiring; ~30s/file |
| 3 boilerplate | don't read — **trust a full-suite run** (see the narrow exemption) |

**The tier-3 exemption is narrow.** "Trust the tests" is only sound when the evidence is
a **full-suite** run. When the diff touches a global-effect artifact (the adapter's
`commands.md` list) and the report shows only a scoped run, the tier-3 skip does not
apply — read those files, and flag the missing run.

## Step 3 — identify review lines for tier 1

For every tier-1 file: the exact line ranges a human must read, each with a one-line
**why**. Focus on authorization decisions, query filtering and ownership, state
transitions, validation beyond types, error handling on sensitive paths, anything
implementing or deviating from a recorded decision.

## Step 4 — write the QR

Output shape (full format below): `## QR-{n} — Code Review: {slice}` with metadata, then
**Summary → Business-logic → Glue → Boilerplate → Flags**, in that order, Flags always
last. Method notes, deliberate product changes, and test status fold into Summary or
Flags — no trailing sections.

**ATOMIC-ITEM rule:** one review item = one table row, and the row carries its own open
command in an **Open** column — never a separate command block. Each row stands alone —
read, open, review, tick, next. The Open cell is `editor_cmd` with `{line}`
and the **absolute** `{file}` substituted; with no `editor_cmd` configured, a plain
`file:line` reference (clickable in most terminals) — and say the config key exists.

```
### Business-logic — read every line
| File · concern (lines) | Why | Open |
|---|---|---|
| `src/.../File.ext` · `method()` (L12–40) | {why this needs human eyes} | {editor_cmd or file:line} |

### Glue — read the flow, skip the syntax
| File | What to check | Open |
|---|---|---|

### Boilerplate — don't read, trust the full suite
| File | What it does |
|---|---|

### Flags
{Deviations from the spec docs, missing coverage, security observations — ranked by
severity, each with a concrete failing scenario. Include a "Verified safe" line for
consequential things checked and cleared, each citing the mechanism that makes it safe.
If none: "None."}
```

## Step 5 — adversarial review of the review

Before recording, subject the draft to a critic whose job is to **break** it — a fresh
reviewer with no prior context, dispatched per the executor adapter so it isn't anchored
on the first pass. It must check:

- **Coverage** — every changed file categorised (diff `--name-only` against the tables);
  every tier-1 file has line references.
- **Mis-tiering** — anything in glue/boilerplate that touches auth, ownership, query
  filtering, state transitions, uploads, or money is tier 1.
- **Unread inputs** — were the spec docs actually cross-checked? Re-derive the intended
  access level and slice ownership and compare to the code; stale security docs and scope
  drift are the findings a first pass most often misses.
- **Unsupported "verified safe" claims** — each must cite the mechanism or line; downgrade
  assumption-backed ones to "needs verification".
- **False positives** — each flag needs a concrete reachable failing scenario, or it drops.
- **Severity** — defensible, not diplomatic.

Feed the critique back, revise, and loop until the critic surfaces nothing material.
Record only the revised review; note in the QR that an adversarial pass ran.

## Step 6 — record

Write the **full** QR (complete tables, all Open commands, all flags — never a condensed
summary; the file must stand alone) to `{planning_root}/{slice}/REVIEW.md`:

- Section order of the whole file: top context (`# {Slice} — Quality Reviews`, then
  `## Design decisions` and `## Constraints` when there is content) → QRs in sequence,
  newest last, separated by `---` → `## Future functionality` as the end appendix.
- Sequential ids QR-1, QR-2, … — never reused.
- Commit scoped by pathspec: `git commit -m "..." -- {planning_root}/{slice}/REVIEW.md`
  (plus the guide below when created) — the index is shared across concurrent sessions.

**Re-reviews and resolutions — the strikethrough convention** (applies to every review
and planning markdown): strike the **entire** original item with `~~…~~`, follow it
unstruck with a bold status (`**FIXED**` / `**RESOLVED**` / `**EXPECTED**` /
`**FALSE POSITIVE**` / `**IMPROVED**` / `**REMOVED**`) plus the resolution, and leave it
**in place** — never move items to a "done" section, never prefix with ✅.

## Step 7 — lifecycle and the review guide (first QR only)

On the first QR for a slice: advance the slice to `in-review` in `INDEX.md`, and create
`{planning_root}/{slice}/REVIEW_GUIDE.md` — the human walkthrough companion, without
which a reviewer doesn't know what to test or what is deliberately out of scope:

```
# {Slice} — Review Guide
## Included        — every user-facing surface to test, grouped by role/area (with routes)
## Excluded        — deliberately NOT in scope (other slice / deferred / not built)
## Known Issues    — table: issue → status (include spec deviations from the review)
## Code Reviews Completed — table: QR | date | scope | findings
## How to Review   — access + login, numbered walkthrough per role, a mobile check
## Open Questions  — table: question → context
```

Derive Included/Excluded from the spec docs and done-criteria; derive How to Review from
the routes and the flows in the diff. Later QRs update Known Issues and Code Reviews
Completed rather than rewriting the guide.

## Rules

- Never skip a tier-1 file, and never let one appear without line references.
- A review is **slice-based, not session-based**: describe the slice's current state and
  findings, not a changelog of the working session. Intentional behaviours belong in
  Design decisions; fixes belong in Flags marked resolved; traceability is the QR
  metadata (`Reviewed at: {tip sha}`), not prose.
- Do not review code style — that is for linters.
- Findings route to `/kerbe:bug` (defects with blast radius get the impact analysis
  before their fix). They never become coverage-ledger rows.
- Any change to this skill or the `risk-tiers.md` adapters must pass the review gate in
  `fixtures/ACCEPTANCE.md` before use on a real project.
