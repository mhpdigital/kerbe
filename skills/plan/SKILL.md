---
name: plan
description: >-
  Use when a slice's spec docs and design are in place and the next step is a task-by-task
  TDD implementation plan. Runs twice: first it drafts PLAN.md and lists the decisions the
  draft surfaced for /kerbe:grill; after grilling it freezes the plan with the answers
  folded in. Also writes a remediation plan for a fix list from a coverage run.
---

# kerbe:plan — draft the task list, then freeze it

Turns a slice's spec docs into `PLAN.md`: **frozen instructions — the HOW, with code**, one
task per independently testable deliverable. Everything project-specific resolves through
`kerbe.yml` (`{plugin}/skills/coverage/references/config.md`).

**Drafting and freezing are two runs, with `/kerbe:grill` between them.** Writing the tasks
is what surfaces most of a slice's real decisions — which table a task writes, what a case
asserts, which of two routes a seam uses — and a spec read on its own cannot see them. So
the first run writes the whole plan but **does not settle a decision a human owns**: it
lists it, with a recommended answer, and stops. Grilling then puts those questions to the
person who owns them, and the second run freezes the plan with the answers folded into the
task bodies. Freezing first would lock guesses in and turn every later answer into an
amendment; grilling first has only the thin spec to ask about.

```
kerbe:figma → kerbe:plan (draft) → kerbe:grill → kerbe:plan (freeze) → kerbe:coverage pre-impl
```

`PLAN.md` is not a tracker. The live tracker (`claude-progress.md`) is derived from it by
`/kerbe:implement`, at the workspace, with its own lifecycle. Never merge the two: a plan
that gets edited while it runs stops being a denominator, and `kerbe:coverage` needs a
denominator.

## Setup

1. Read `kerbe.yml` at the project root. Missing ⇒ **hard stop**: point at
   `kerbe.yml.example`.
2. Resolve the slice: explicit argument, else the current `{workspace.branch_prefix}*`
   branch, else ask. One slice per run.
3. Resolve the stack adapter (`adapters/stack/{name}/commands.md` for every verification
   command the plan will quote) and the design adapter.
4. **Mode — computed from the slice, never a flag and never a question.** Read the plan
   header's `**Status:**` line:
   - **no `PLAN.md` in the slice folder ⇒ draft mode.** Steps 1–6 below.
   - **`PLAN.md` with `**Status:** draft` ⇒ freeze mode.** See the Freeze mode section.
   - **`PLAN.md` with `**Status:** frozen`, or with no Status line (a plan written before
     the draft step existed) ⇒ remediation mode.** A frozen plan is not rewritten, so the
     only legal output is `FIX_PLAN.md`. See the mode section at the end. Remediation is for
     **ledger rows**: a decision out of `/kerbe:grill` has no ledger id and never arrives
     here — that skill appends it to the same `PLAN.md` as a dated amendment section
     (its Step 6), per the amendment rule in Rules below.
   - The user overrides all three by saying so ("re-plan from scratch, the scope changed") —
     and then say what it costs before writing: a replaced frozen `PLAN.md` invalidates the
     ledger's plan hop and needs a fresh coverage extraction to mean anything again.

   State the mode, and the evidence for it, in one line before you start.

**Fact-gathering delegations** (an Explore or general-purpose agent sent to read code,
adapters or precedents for the plan) run at effort `standard` — pass `model: sonnet`
explicitly. Reading is not where the plan's judgement lives; an unset model inherits the
session's, which under Night Shift routing is the costliest tier for a read-only pass.

## Step 1 — the spec must exist

The slice's spec docs exist. If the doc set is missing, run `/kerbe:start` first. Open
questions in those docs do **not** stop a draft: they become entries in its
`## Open decisions` section (Step 3), alongside the ones the tasks surface, so grilling
gets them all in one round. What stops a draft is a spec too thin to task at all — no
requirement a task could cite — and that goes back to `/kerbe:start`.

## Step 2 — the design gate (blocking)

`PLAN.md` is frozen instructions. Freezing a UI task against an unmeasured or stale design
is how a slice gets built from a cached guess, so the gate sits **here**, before the freeze
— `/kerbe:implement` never looks at the design at all.

Read `{planning_root}/{slice}/SETTINGS.md` and branch on `design_required`:

- **No `SETTINGS.md`, or the key missing / not exactly `true` or `false`** ⇒ **STOP.** Do
  not guess, do not default, do not read absent as `false`. The slice never answered the
  design question: run `/kerbe:start` for it to settle it. An unanswered question blocking
  is the entire purpose of the setting.
- **`design_required: false`** ⇒ proceed. Record in the plan header that the slice has no
  design leg **and cite the reason** from the `SETTINGS.md` Notes row — "no UI at all" and
  "has UI, no design yet" read identically in a header and only the second is worth
  re-checking before you freeze.
- **`design_required: true`** ⇒ `UI_ELEMENTS.md` must exist with its **Design sources**
  block populated: file key, page, and one row per screen carrying a **node id** and a
  `measured=` date. Then check freshness the way the design adapter defines it (for
  `figma`: compare the file's `lastModified` against the oldest `measured=`; for
  `claude-design`: compare each artboard's last commit date, `git log -1 --format=%cs --
  <design dir>/<file>`, against its row's `measured=`, and run `dc_extract.py --lint` —
  a failing lint counts as an unfilled block).
  - block unfilled or node ids missing ⇒ **STOP**, run the adapter's extraction
    (`/kerbe:figma extract`, or `dc_extract.py` for `claude-design`) and fill it
  - any `measured=` older than the design's last modification ⇒ **STOP**, the design moved
    since it was measured; re-measure and re-date before planning
  - fresh ⇒ proceed

**Carry the node id into the plan.** Every UI-bearing task names its origin as
`node=<id> measured=<YYYY-MM-DD>`. This is the hand-off with no other owner: implement has
no design step and no instruction to re-measure, so a UI task without a node id is a task
someone will build from whatever the template already says.

## Step 3 — author the plan

Follow `references/plan-spec.md` — the required header, the file-structure map, task
right-sizing, the per-task effort level and the code boundary it sets, the per-task
`**Depends:**` line, the seam rule, case tables with their `Level` column, bite-sized TDD
steps, and the no-placeholder rules. It is self-contained: this skill has **no external
skill dependency**.

**Two fields decide how the slice actually gets built, so write them deliberately:**

- **`**Depends:**`** is the scheduler's input. `/kerbe:implement` runs everything the graph
  leaves free at the same time, so a dependency you declare out of caution is concurrency you
  have spent. Declare consumed seams and shared files; justify anything else in a line.
- **the case `Level`** decides what infrastructure has to exist before that case can be
  proven. Choose it per case against the rule in the spec — boot the framework only when the
  framework is part of the claim — and keep the acceptance floor: audience reachability,
  action chains and HTTP-observable state transitions each need a real request, and a
  client-side claim needs a browser.

**Separate what you can find out from what someone has to choose.** A question the codebase
or the spec docs answer — which repository owns a lookup, which existing pattern fits, what
a column is called — you answer by reading, and write the answer in. A question a person has
to choose — scope, a product rule, a policy, a limit, a route shape, a value nobody has set
— you do **not** answer, however obvious your pick looks. Write it as an open decision:

- in the plan header, `**Status:** draft`
- an `## Open decisions` section **before the first task**, one entry per decision:

  ```markdown
  ### OD-1: {the question, one line}
  **Affects:** Task 2, Task 4
  **Options:** {the real alternatives, each with its cost}
  **Recommended:** {your pick} — {why, citing the spec, the code or a sibling slice}
  ```

- in every task the answer changes, a `**Decisions:**` line `OD-1 (open) — {what it
  decides here}`, and the task body written for the recommended answer. The freeze then
  only has to change the tasks whose answer differed.

A recommendation is not a decision. The draft is where a planner is *allowed* to be unsure,
and saying so is the job: an open decision left out of the section is one grilling never
asks, and the freeze reads it as settled.

**Decide each task's effort level as you write it**, and let it set how much code the task
carries: `low` is a typist and gets the code in full; `standard` and `deep` get seams, cases
and deciding fragments, never bodies. A plan of pasted implementations is not a safer plan —
it is a plan whose every body was written against a codebase that does not exist yet, and
whose reviewer stops reading. The plan-spec's Effort and seam-rule sections are the authority.

Author with `references/plan-spec.md` only. Do not delegate to another planning skill:
`superpowers:writing-plans`, for one, requires full code in every step (against the seam
rule), names its own executor in the plan header (competing with `/kerbe:implement`), and
saves to a dated file in a docs directory.

**Name and location, always:**

1. **Name** — the plan is `PLAN.md`, never a date-stamped filename. A per-slice folder holds
   exactly one plan, and dumb orchestration must be able to locate it without searching.
2. **Location** — `{planning_root}/{slice}/PLAN.md`. Never a docs directory, and **never a
   hidden dotfolder** (`.superpowers/`, `.claude/`, any tool's `.<name>/`): working state
   lives in the open and git-tracked.

## Step 4 — Global Constraints must carry these

Every task inherits this section, so anything a worker could get wrong by omission belongs
here, with exact values:

- the **base branch** to cut the slice branch from (`workspace.base_branch` unless the
  slice says otherwise) — `/kerbe:implement` reads it from here first
- the stack's **full-suite trigger**, copied from the adapter's `commands.md`
  "Global-effect artifacts": a task touching one of those is not done until the full suite
  has run and its output is pasted; a scoped run is never a no-regression claim
- the verification commands themselves, quoted from the adapter — never invented
- every line of `kerbe.constraints`, plus `kerbe.constraints_by_skill.implement`
  (the workers building this plan inherit them), verbatim
- version floors, naming and copy rules, and platform requirements from the spec docs

## Step 5 — self-review, then draft or freeze

Run the self-review in `references/plan-spec.md` (spec coverage, placeholder scan, seam
consistency, effort and code boundary, open decisions, command provenance), then the
structural check:

```bash
python3 {plugin}/fixtures/check_plan.py {planning_root}/{slice}/PLAN.md {design_required}
```

Fix what it reports; it checks structure, not judgment. Then branch on what the draft left
open:

- **One or more open decisions ⇒ leave it a draft.** `**Status:** draft`, the section
  filled. Do not freeze.
- **Nothing open ⇒ freeze now, in this run.** Set `**Status:** frozen`, remove the empty
  section, re-run the check. There is nothing for a grill round to ask, and a second run to
  flip one line is ceremony.

**Freezing is what closes the decisions.** A plan is frozen so workers can be dispatched
against it, including into unattended runs where nobody is awake to answer a question. So an
unresolved decision does not freeze: it is an open decision in the draft, or — only when the
codebase answers it — a `deep` task whose `Decisions` block says what the worker is to settle
and report. "The implementer can decide" is a plan that has moved a planning question into a
night session — the one place it cannot be asked.

**The `deep` route is only for questions the codebase answers.** A question that needs a
person to choose — scope, a product rule, a policy, a value nobody has set — is an open
decision, and no effort level converts it into work.

Commit the plan **in the planning repo, scoped by pathspec** —
`git -C {planning_repo} commit -m "..." -- <slices>/{slice}/PLAN.md`
(`{planning_repo}` = `git -C {planning_root} rev-parse --show-toplevel`, paths relative to
it; see `config.md` → `planning_root`) — because the git index is shared across concurrent
sessions and a bare commit sweeps up another session's staged work.

Stamp `TIMING.md` — timestamp only, no effort estimate, from
`TZ='{kerbe.timezone}' date '+%Y-%m-%d %H:%M'`: the "Plan draft" row for a draft; both the
"Plan draft" and "Plan impl." rows when this run froze it.

## Step 6 — hand off

**Left as a draft** ⇒ list every open decision in the final message — id, question,
recommended answer — and name the one next step: `/kerbe:grill {slice}`, which takes the
draft's open decisions as its first round. Then `/kerbe:plan {slice}` again to freeze. **Do
not answer them yourself**, and do not treat a recommendation nobody objected to as a ruling:
running unattended, stop here and say a person is needed.

**Frozen** ⇒ state both next steps explicitly:

1. `/kerbe:coverage {slice}` in **pre-impl** mode — does the plan task everything the design
   and spec promise? This is the cheapest moment to find a dropped promise: before anyone
   builds.
2. `/kerbe:implement {slice}` — derives `claude-progress.md` from this plan and dispatches
   the work.

## Freeze mode — fold the answers in

Entered automatically when `PLAN.md` carries `**Status:** draft` (Setup step 4). The draft
is not frozen yet, so its task bodies may be edited — that is the whole point of drafting
first: every answer lands in the task it changes, not in an amendment beside it.

1. **Every open decision needs a recorded answer.** For each `OD-n` in the draft's section,
   find its ruling in `{planning_root}/{slice}/DECISIONS.md` — `/kerbe:grill` records it
   under that same id. Any `OD-n` without one ⇒ **STOP**: name the unanswered ids, hand off
   to `/kerbe:grill {slice}`, change nothing. Never fill one in from its `**Recommended:**`
   line: a recommendation nobody ruled on is exactly the inferred decision this split
   exists to prevent.
2. **Fold each answer in.** In every task carrying `OD-n (open)`, replace the marker with
   the citation (`DECISIONS.md OD-n — {the ruling}`), and where the ruling differs from the
   recommendation the task was written for, rewrite what it changes — files, interfaces,
   cases, steps, `Depends`. A ruling that adds or drops a deliverable adds or drops a task.
   Decisions grilling settled beyond the listed ones (a new `Q` id) are folded in the same
   way, wherever they bite.

   Two things the fold may turn up, and neither is yours to settle:
   - **A ruling adds UI the Design-sources block does not measure** ⇒ **STOP** before
     writing that task: run `/kerbe:figma` (or the adapter's extraction) for the new leaf.
     Never write a node id, a size or a `measured=` date yourself — a measurement the
     planner typed is the cached guess Step 2 exists to refuse.
   - **Applying a ruling raises a question it does not answer** (the ruling says "filter by
     category"; the design's chips are not categories) ⇒ **do not freeze.** Add it to
     `## Open decisions` as the next `OD-n`, with options and a recommendation, mark the
     task `OD-n (open)`, keep `**Status:** draft`, and hand back to `/kerbe:grill`. Picking
     the reading that makes the ruling "hold" is minting a decision.
3. **Re-run the self-review over the tasks that moved** — seam consistency and the
   dependency graph above all, since a changed route or seam ripples into its consumers.
4. **Freeze.** Delete the `## Open decisions` section, set `**Status:** frozen`, and run
   `check_plan.py` again; it fails a frozen plan that still marks anything open. Commit
   scoped by pathspec, stamp "Plan impl." in `TIMING.md`, and hand off as Step 6 does for a
   frozen plan.

## Remediation mode — planning fixes, not features

Entered automatically when the slice already has a frozen `PLAN.md` (Setup step 4 —
`**Status:** frozen`, or no Status line). The authoring rules are unchanged; what differs is
the source, the scope and the exit.

**Source — resolved, not asked.** The open rows of the frozen ledger are the work list
(`{plugin}/skills/coverage/scripts/verdict.py` prints them). When a fix list sits beside the
ledger — tickable rows citing ledger ids — use it, and re-derive its ticks from the ledger
rather than trusting them: a row ticked in a fix list but still open in the ledger was never
re-verified.

**Scope — everything actionable, minus two classes you exclude by construction and name in
the report:**

| Class | Why it is not a plan task |
|---|---|
| design-only rows (`spec GAP`) | a spec decision first — add the leaf to the spec docs, or record a dated decision to drop it. Only then does it become work. |
| rows the repository cannot evidence (operational, cutover, live-service) | verified by hand against the real system; a plan task would be fiction |

Honour a narrower scope when the user names one in the invocation ("only the partials", "the
blockers from the addendum"). Either way, report the split with counts — planned, excluded
as spec decision, excluded as manual — so nothing leaves the list silently.

Then, four changes to the authoring rules:

- Write `FIX_PLAN.md` beside the ledger, not `PLAN.md`. The slice's `PLAN.md` stays frozen —
  it is the plan hop the ledger already measured, and rewriting it destroys that record. A
  second remediation round appends a dated section to the same `FIX_PLAN.md`; it does not
  start a rival file.
- Every task **cites the ledger ids it closes**. A task closing no row does not belong here;
  it is new scope and needs its own slice.
- Skip Step 2's freshness gate only for rows whose fix is not design-sourced. A design-only
  row is a **spec decision first**: either add the leaf to the spec docs and then build it,
  or record a dated decision to drop it. Do not plan a build task against a design leaf the
  spec never accepted.
- The exit condition is the ledger, not the plan: after the fixes land, re-verify the cited
  rows against the **same frozen ledger** and recompute the verdict with
  `{plugin}/skills/coverage/scripts/verdict.py`.

## When NOT to use

- Spec docs missing ⇒ `/kerbe:start` first (open questions in them are fine — the draft
  lists them)
- A draft is waiting on its open decisions ⇒ `/kerbe:grill`, then this skill again
- `SETTINGS.md` missing or `design_required` unanswered ⇒ `/kerbe:start`
- `design_required: true` and the Design-sources block is empty or stale ⇒ `/kerbe:figma`
  (or `dc_extract.py` under the `claude-design` adapter)
- The plan exists and you are building it ⇒ `/kerbe:implement`
- Checking what is built against what was promised ⇒ `/kerbe:coverage`

## Rules

- The planner lists decisions; it does not make them. A choice a person owns goes in the
  draft's `## Open decisions` with a recommendation, never into a task as if settled — and
  the freeze folds in only rulings `DECISIONS.md` records.
- A draft's tasks may be rewritten; a frozen plan's may not. `**Status:**` is what says
  which one a file is.
- A frozen plan is amended by **writing a dated amendment section at its end**, never by
  editing a task a worker may already have read. New work in an amendment is a new task,
  numbered on from the last and authored to `references/plan-spec.md` like any other;
  superseded work is named in the amendment, not edited out. `/kerbe:grill` Step 6 is the
  one that writes them.
- Every task carries an effort level, and the level sets the code boundary: full code at
  `low`, seams and cases at `standard` and `deep`.
- Every task carries `**Depends:**`, and every case carries a `Level`. There is no per-plan
  chain/group label — a single word for a whole plan cannot say that two tasks are
  independent while three others are a genuine chain.
- A case is `unit` unless the framework is part of its claim. The acceptance floor is the
  limit on that: audience reachability, action chains and HTTP-observable state transitions
  keep their `http` cases, and a client-side claim keeps its `browser` case.
- Interfaces carry **seams only** — what another task, a specified test, or a later slice
  consumes. An internal helper or an exception class caught inside the same task is the
  worker's to name, and listing it is a defect, not thoroughness.
- No placeholders. "TBD", "handle edge cases", "similar to Task 3", an unanswered question,
  a test step with neither cases nor code — each is a plan defect, not a shortcut.
- The plan quotes commands from the stack adapter. A command that appears nowhere in
  `commands.md` is either a gap in the adapter (fix it there) or an invention (drop it).
- Any change to this skill or `references/plan-spec.md` must pass the plan gate in
  `fixtures/ACCEPTANCE.md` before it is used on a real project.
