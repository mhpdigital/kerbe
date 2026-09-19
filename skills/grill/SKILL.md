---
name: grill
description: >-
  Use when a slice's spec docs are drafted but the decisions behind them are not settled —
  runs the grilling rounds that turn silent assumptions into recorded decisions, then writes
  them into DECISIONS.md, the spec docs, and — when the slice already has one — the same
  PLAN.md as a dated amendment. This is kerbe's Specify step, between figma and plan.
disable-model-invocation: true
---

# kerbe:grill — settle the spec by interrogation

`/kerbe:plan` Step 1 requires a spec whose **open questions are resolved**, because "a plan
written on an unsettled spec churns, and it churns after it has been frozen and handed to
workers". This skill is how they get resolved: grilling rounds against the slice's own docs,
ending in a `DECISIONS.md` the plan and the requirements can cite.

It is a **wrapper**, not a new interrogation method. The rounds come from the grilling skill
your install provides (`mattpocock-skills:grilling` at time of writing): a design tree worked
in rounds, each round asking the whole frontier with a recommended answer per question, and
waiting. What this skill adds is the part that is easy to get wrong by hand — assembling the
brief that points grilling at the right documents with the right authority, and landing the
result somewhere durable. Everything project-specific resolves through `kerbe.yml`
(`{plugin}/skills/coverage/references/config.md`).

## Where it sits

Lifecycle step **3, Specify** — after `/kerbe:figma`, before `/kerbe:plan`. The docs exist
from `/kerbe:start`; this is where the decisions inside them stop being assumptions.

Run **after** a plan is frozen it is the same step with one more destination: the decisions
still go to `DECISIONS.md` and the spec docs, and Step 6 carries the ones that change work
into the slice's own `PLAN.md` as a dated amendment. Grilling never leaves a plan describing
a spec the slice has since ruled against.

**This skill establishes that placement; it does not inherit it.** Step 3 has been `manual`
in the TIMING template since the template was written, and no slice has ever stamped it. The
evidence behind putting grilling there is one campaign — `ddx-freeform-input`, 2026-09-16,
twelve rounds, a 262-line `DECISIONS.md` that `REQUIREMENTS.md` and `PLAN.md` then cited —
whose TIMING row was annotated "Grilling rounds replace the manual specify step" but left
unstamped. That row asserted the mapping. This skill is what makes it a step: it stamps row 3,
so a slice that was grilled is distinguishable from one where nobody asked.

## Setup

Read `kerbe.yml` (hard stop if missing). Resolve `planning_root`, `timezone`, and the
`stack.code_roots` entry for this slice — facts come from that code, so the session needs to
read it. Resolve the slice from the argument, else the branch
(`{workspace.branch_prefix}{slice}` / `{workspace.review_prefix}{slice}`), else ask. Hard
stop if `{planning_root}/{slice}/` does not exist — say to run `/kerbe:start` first. Honour
`kerbe.constraints` and `kerbe.constraints_by_skill.grill`.

**If `PLAN.md` already exists, grilling still lands in that plan.** Frozen means a task body
is never rewritten; it does not mean the plan is closed. `/kerbe:plan`'s own rule is that a
frozen plan is amended by **a dated amendment section at its end**, and that is where a
post-freeze decision goes — Step 6 writes it, into the same `PLAN.md`, in the same session.
`FIX_PLAN.md` is not the route: that is coverage's remediation file, and its tasks cite
**ledger ids**, which a grilling decision does not have. A decision cites a `DECISIONS.md`
question id and belongs in the plan it changes.

Say the two real costs before starting, then proceed:

- code already built against a task the amendment supersedes is not unbuilt by the amendment
  — each of those is its own decision, and Step 6 names them rather than assuming either way
- if `PROMISES.md` exists, the spec edits and the amendment move the ledger's denominator, so
  the slice needs a fresh `/kerbe:coverage` extraction; the diff against the old ledger is the
  record of what moved

## Step 1 — assemble the brief

This is the skill's whole reason to exist. Grilling is only as good as what it was pointed
at, and the shape below is the one that worked. Build it from the slice, do not ask the user
to supply it, and **cite paths — never paste document contents**.

Seven parts, in order:

1. **Target.** "Interview me on the `{slice}` slice."
2. **The slice's own docs, listed explicitly, with authority annotated.** Not "read the slice
   folder" — name each file and say what standing it has. A measured catalogue outranks a
   draft: `UI_ELEMENTS.md` (when `design_required: true`, it is the measured catalogue),
   `REQUIREMENTS.md`, `ENTITIES.md`, `ROUTES.md`, `SECURITY.md`, `DONE_CRITERIA.md`, and
   `IMPORT.md`/`CODEMAP.md` where a legacy counterpart exists.
3. **Parent and sibling docs, scoped to an ID range.** A root plan or a parent slice's
   `DECISIONS.md` is usually large and mostly irrelevant. Name the entries that bind this
   slice (`entries {PREFIX}-10 through {PREFIX}-15`), not the file.
4. **Dependency state — what is already built, and where to read it.** For each slice this one
   depends on: whether it has landed, on which branch, and the specific docs that define the
   contract being consumed. A grilling session that does not know a dependency already shipped
   will re-litigate its decisions.
5. **The fact/decision split, stated outright.** "Facts come from those files and from the code
   in `{code_root}`; the decisions are mine." The grilling skill already holds this rule —
   finding facts is its job, never the user's — and repeating it in the brief keeps a round
   from degenerating into questions the session could have answered by reading.
6. **Deferred recording.** "Record nothing yet: when the frontier is empty, we write the
   decisions into `{planning_root}/{slice}/DECISIONS.md`." Recording mid-campaign produces a
   file that contradicts itself as later rounds reshape earlier answers.
7. **Seeded round one.** The open questions the docs already flag — a `[Q]` marker, a TODO, a
   contradiction between two docs, a requirement with no entity behind it. Hand grilling the
   questions the slice has already asked itself rather than making it rediscover them.

Show the assembled brief to the user before invoking, and let them add to it. They know which
decisions they are actually unsure about; the docs only know which ones are unwritten.

## Step 2 — run the rounds

Invoke the grilling skill with the brief. Do not re-implement its method: the tree, the
frontier, the round format and the "wait for answers" discipline are all its own. Two
obligations belong to this skill while the rounds run:

- **Dispatch sub-agents for facts.** Grilling requires it, and a kerbe slice keeps its facts in
  two places the session can reach — the planning docs and the code root. A question the user
  is asked that a `grep` could have answered is a defect in this step.
- **Track the round numbers.** Every question gets an id (`Q1`, `Q1d`, `Q11`) that the recorded
  decision will cite. Sub-lettering is how a decision that split into sub-decisions stays
  traceable to the moment it split.

## Step 3 — survive the context wall

A real campaign will not fit in one context. The worked example ran twelve rounds and was
resumed twice. Keep `{planning_root}/{slice}/GRILLING_STATE.md` — the settled decisions so
far, the open frontier, and the next round's questions — updated as rounds close.

It is **transient**: uncommitted while the campaign runs, deleted when `DECISIONS.md` is
written. It is not a second ledger and never outlives the session that needed it. Resuming is
`/kerbe:grill {slice}` again — read the state file, rebuild the frontier, carry on.

## Step 4 — record the decisions

When the frontier is empty, write `{planning_root}/{slice}/DECISIONS.md`. The shape that
worked:

- **A header stating provenance**: "Non-obvious choices made during scoping of this slice.
  Settled by grilling on {date}; each heading names the grilling question(s) it resolved."
- **Sections by topic, citing question ids** — `### Session and chip state (Q1)`,
  `### Dismissed chips (Q2, Q11)`. Topic first so it is readable by someone who never saw the
  rounds; ids second so it is traceable by someone who did.
- **Each bullet records the ruling _and_ the reasoning.** "We chose X" is not a decision
  record, it is a note. Quote the user where they ruled something out explicitly — the reason
  a door was closed is what stops it being reopened in three weeks.
- **`**Known limit, to record:**`** for anything the decision knowingly leaves broken or
  deferred. A limit written down is a scope boundary; the same limit unwritten is a bug report
  waiting to be filed against you.
- **Propagation notes** naming the doc each decision must reach — "these three protections go
  in `SECURITY.md`" — and, where the slice already has a `PLAN.md`, whether the decision is
  also a plan change (Step 6 rules on that).

## Step 5 — propagate into the spec docs

Follow every propagation note from Step 4 into the doc it names: a decision that never reaches
`SECURITY.md`/`ENTITIES.md`/`REQUIREMENTS.md` did not change the slice, it only changed a file
about the slice. Add a `REQ-` id for any testable requirement a decision created.

## Step 6 — feed the decisions into the plan

**No `{planning_root}/{slice}/PLAN.md`** ⇒ nothing to do here: the decisions are in the spec
docs and `/kerbe:plan` builds the plan from them. Say that at hand-off and go to Step 7.

**A `PLAN.md` exists** ⇒ the decisions reach it here, in this session. A plan that was not
amended is the pre-grilling plan, and the pre-grilling plan is the one the workers build.

**Which decisions are plan changes.** A decision that only sharpens wording in a spec doc is
not one. A decision that adds, drops or redirects a deliverable, changes an acceptance
condition, or changes a seam another task consumes, is. Rule on each decision and report the
split with counts — amended, spec-only — so nothing leaves the list silently.

**Append one dated section at the end of the file**, never a rival plan file:

```markdown
## Amendment {YYYY-MM-DD} — grilling

**Source:** `DECISIONS.md`, grilled {YYYY-MM-DD} — Q6, Q7, Q11

- Task 4 — superseded by Task 9 (Q6): {the ruling, in one line}
- Task 6 — dropped (Q7): {why}
- Tasks 9, 10 — new (Q6, Q11)
- Already built against Task 4: {what exists, or "nothing"} — {the user's call on it}

### Task 9: ...
```

Three rules for what goes inside it:

- **New work is new tasks**, numbered on from the highest existing task and authored to
  `{plugin}/skills/plan/references/plan-spec.md` like any other: `**Files:**`, `**Effort:**`,
  `**Interfaces:**` (seams only), `**Depends:**`, a case table with a `Level` per case,
  bite-sized TDD checkbox steps, a pathspec-scoped commit step. An amendment task that skips
  these is a task `/kerbe:implement` cannot schedule and `check_plan.py` will fail.
- **Superseded work is named, never edited.** Do not touch the body of a frozen task: a worker
  may already have read it, and the ledger measured it. The amendment's list is what says
  Task 4 no longer stands, and every superseded or dropped task names what replaces it or why
  nothing does.
- **Every line cites its question id.** `(Q6)` is what ties the amendment back to
  `DECISIONS.md` — the same traceability a `FIX_PLAN.md` task gets from its ledger id.

**Re-run the structural check over the whole amended file:**

```bash
python3 {plugin}/fixtures/check_plan.py {planning_root}/{slice}/PLAN.md {design_required}
```

It reads the last task's body to end of file, so the amendment prose is checked as part of
it: keep "TBD", "to be decided", "open question" and the rest out of the section wherever
they would sit. Fix what it reports before committing.

**State the two downstream effects at hand-off** — do not leave them to be discovered:

- `/kerbe:implement {slice}` re-derives the tracker from the amended plan, and its
  what-already-exists pass is what keeps finished tasks from being rebuilt; the amendment's
  tasks join the schedule from their `Depends`.
- a `PROMISES.md` beside the plan is now measuring a plan that moved: hand off to
  `/kerbe:coverage {slice}` for a fresh extraction, and keep the old ledger as the diff.

## Step 7 — stamp and commit

Stamp `TIMING.md` row "3. Specify" with `/kerbe:grill` and
`TZ='{kerbe.timezone}' date '+%Y-%m-%d %H:%M'`; note "plan amended" in the row when Step 6
wrote one. Delete `GRILLING_STATE.md`.

Commit **scoped by pathspec** — stage the named paths (`DECISIONS.md`, every spec doc Step 5
touched, `PLAN.md` when Step 6 amended it, `TIMING.md`), check `git diff --cached --stat`, and
commit as `git commit -m "..." -- <the same paths>`. The git index is shared per repository
across concurrent sessions.

## Anti-patterns this catches

| Anti-pattern | What happens | Caught at |
|---|---|---|
| bare `/grill-me` with no brief | rounds interrogate the wrong altitude, or re-derive what the docs already settled | Step 1 |
| pasting doc contents into the brief | burns the context the rounds need, and goes stale the moment a doc changes | Step 1, paths only |
| whole parent `DECISIONS.md` in scope | rounds re-litigate decisions another slice already made | Step 1, ID range |
| dependency state omitted | grilling re-opens a contract that already shipped | Step 1, part 4 |
| user asked a question a grep answers | the human spends attention on a fact, not a decision | Step 2 |
| recording decisions mid-campaign | later rounds reshape earlier answers; the file contradicts itself | Step 1, part 6 |
| campaign dies at the context wall | the frontier is lost and the rounds restart from nothing | Step 3 |
| ruling recorded without its reasoning | the same door gets reopened next month | Step 4 |
| decisions never leave `DECISIONS.md` | the plan is built from the unrevised spec | Step 5 |
| spec docs revised, existing `PLAN.md` left alone | the workers build the pre-grilling plan | Step 6 |
| post-freeze findings pushed to `FIX_PLAN.md` | a remediation file whose tasks must cite ledger ids fills with tasks that cite none | Setup |
| a frozen task edited in place to absorb a decision | a worker may already have read it, and the ledger measured it | Step 6 |
| amendment task without `Depends`, effort or case levels | `/kerbe:implement` cannot schedule it and `check_plan.py` fails | Step 6 |
| plan amended, ledger left as it was | `PROMISES.md` keeps measuring a plan that moved | Step 6 |

## Rules

- **The decisions are the user's; the facts are yours.** Every question put to them must be one
  no amount of reading could answer.
- Never record a decision the user did not make. An inferred ruling in `DECISIONS.md` is worse
  than an open question, because it stops looking like one.
- The frontier empties or the session says it did not. A campaign abandoned mid-tree is
  reported as abandoned, with the open frontier left in `GRILLING_STATE.md`.
- `GRILLING_STATE.md` is never committed and never outlives the campaign.
- **A decision that changes the plan reaches the plan.** It lands as a dated amendment section
  in the slice's own `PLAN.md` — never a rival plan file, never an edit to a frozen task body,
  and never parked in `DECISIONS.md` for someone else to notice.
- This skill writes only under `{planning_root}/` — never application code.
- Any change to this skill must pass the grill gate in `fixtures/ACCEPTANCE.md` before it is
  used on a real project.
