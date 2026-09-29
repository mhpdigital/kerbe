# Plan draft → grill → freeze

**Date:** 2026-09-30 · **Release:** 0.10.0 · **Skills:** `plan`, `grill` (plus guards in
`coverage`, `implement`, `start`)

## The problem

Every step that makes a slice more concrete surfaces decisions the step before could not
see. The spec surfaces scope questions; the plan surfaces implementation questions — which
table a task writes, which of two routes a seam uses, what a case asserts. Grilling should
sit after the step that surfaces the most of them, and before anything is locked.

Up to 0.9.x, `/kerbe:plan` fused **drafting** (where the questions appear) and **freezing**
(which forbids asking them). That made both possible orders wrong:

| Order | What goes wrong |
|---|---|
| grill → plan | grilling interrogates a thin spec; the plan's own questions arrive after the freeze |
| plan → grill | the questions surface, but the plan is frozen, so every answer becomes an amendment |

A second failure compounded it. On 2026-09-29 a dayshift run of `ddx-suggestions` ran
`/kerbe:grill` unattended: nobody was present, so it "resolved all four decisions by
inspection" and recorded them in `DECISIONS.md` — rulings that read as the user's and were
not. The grill skill already forbade recording a decision the user did not make; nothing
told a session what to do *instead* when no user exists.

## The change

Split planning into a draft and a freeze, with the grill between them:

```
kerbe:figma → kerbe:plan (draft) → kerbe:grill → kerbe:plan (freeze) → kerbe:coverage pre-impl
```

- **Draft** (`/kerbe:plan`, no `PLAN.md`) writes every task, but a decision a person owns is
  not made. It becomes an `OD-n` entry in `## Open decisions` (before the first task) with
  options and a recommended answer; each task it changes carries `OD-n (open)` and is written
  for the recommendation. Header `**Status:** draft`. A draft with nothing open freezes in
  the same run.
- **Grill** takes the draft's `OD-n` entries as round one, under their own ids, and records
  rulings in `DECISIONS.md` under those ids. It does not touch a draft plan.
- **Freeze** (`/kerbe:plan`, `**Status:** draft`) needs a recorded ruling for every `OD-n` —
  otherwise it stops, naming them. It folds each ruling into the task it changes (a draft's
  tasks may be rewritten; that is the point), deletes the section, sets `**Status:** frozen`.
  If folding a ruling adds unmeasured UI it stops for `/kerbe:figma`; if it raises a question
  the ruling does not answer, it lists a new `OD-n` and stays a draft.
- **Nobody present** ⇒ grill writes the brief and seeded round to `GRILLING_STATE.md` and
  stops. It never answers its own rounds.

Mode stays computed from the file, never a flag: no `PLAN.md` ⇒ draft; `Status: draft` ⇒
freeze; `Status: frozen` or no Status line (every pre-0.10 plan) ⇒ remediation. A post-freeze
grill still amends, unchanged.

`coverage` pre-impl and `implement` refuse a draft plan. `start` gains the INDEX status
`drafted` and a TIMING row "2a. Plan draft".

## Enforcement

`fixtures/check_plan.py` reads the Status line. A draft must list at least one `OD-n`, each
with `**Affects:**` and `**Recommended:**`, each marked open in some task, and no task may
cite an unlisted `OD-n (open)`; its Open-decisions section is the one place the placeholder
scan skips. A frozen or legacy plan may carry neither the section nor an `(open)` marker.
13 new cases in `tests/test_check_plan.py`.

## Night Shift

`ceremonies.yml` replaces `scoped->ready` with two legs, both prose-first so a session reads
the Status line before choosing a command (running `/kerbe:plan` on a pre-0.10 frozen plan
would otherwise resolve to remediation mode):

- `scoped->drafted` — draft; set `drafted`; if anything is open, copy the `OD-n`s into the
  tracker's Blockers and end `<waiting-for-user/>`. Never answers them, never runs grill.
- `drafted->ready` — freeze (stops, waiting, on an unruled `OD-n`; never falls back on the
  recommendations), then the pre-impl coverage loop, then `ready`.

The grill itself runs by day, with the person who owns the decisions.

## Validation

Recorded in `fixtures/ACCEPTANCE.md` (2026-09-30). Draft run, freeze-stop run, unattended
grill run and two full-freeze runs on `symfony-mini`. The first full freeze scored `ALL PASS`
while minting a decision and typing its own design measurement; the fold rules above were
added in response and the re-run held.
