---
name: plan
description: >-
  Use when a slice's spec docs are settled and the next step is a task-by-task TDD
  implementation plan — the step between specifying a slice and building it. Produces the
  slice's frozen PLAN.md, or a remediation plan for a fix list from a coverage run.
disable-model-invocation: true
---

# kerbe:plan — freeze the task list

Turns a slice's settled spec docs into `PLAN.md`: **frozen instructions — the HOW, with
code**, one task per independently testable deliverable. Everything project-specific
resolves through `kerbe.yml` (`{plugin}/skills/coverage/references/config.md`).

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
4. **Mode — computed from the slice, never a flag and never a question:**
   - **no `PLAN.md` in the slice folder ⇒ build mode.** Steps 1–6 below.
   - **`PLAN.md` exists ⇒ remediation mode.** A frozen plan is not rewritten, so the only
     legal output is `FIX_PLAN.md`. See the mode section at the end.
   - The user overrides both by saying so ("re-plan from scratch, the scope changed") — and
     then say what it costs before writing: a replaced `PLAN.md` invalidates the ledger's
     plan hop and needs a fresh coverage extraction to mean anything again.

   State the mode, and the evidence for it, in one line before you start.

## Step 1 — the spec must be settled

The slice's spec docs exist and their open questions are resolved. If the doc set is
missing, run `/kerbe:start` first; if questions are open, settle them first. A plan written
on an unsettled spec churns, and it churns after it has been frozen and handed to workers.

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
right-sizing, bite-sized TDD steps with real code and real expected output, and the
no-placeholder rules. It is self-contained: this skill has **no external skill dependency**.

*If `superpowers:writing-plans` is installed you may use it to author instead* — it covers
the same ground — but apply the two overrides below and the kerbe-specific additions from
`references/plan-spec.md` (Global Constraints content, node ids, `@req` targets,
adapter-sourced verification commands). Without it, nothing is missing.

**The two overrides, always:**

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

## Step 5 — self-review, then freeze

Run the self-review in `references/plan-spec.md` (spec coverage, placeholder scan, type
consistency), then the structural check:

```bash
python3 {plugin}/fixtures/check_plan.py {planning_root}/{slice}/PLAN.md
```

Fix what it reports; it checks structure, not judgment. Commit the plan **scoped by
pathspec** — `git commit -m "..." -- {planning_root}/{slice}/PLAN.md` — because the git
index is shared across concurrent sessions and a bare commit sweeps up another session's
staged work.

Stamp `TIMING.md`'s plan row with `TZ='{kerbe.timezone}' date '+%Y-%m-%d %H:%M'` —
timestamp only, no effort estimate.

## Step 6 — hand off

State both next steps explicitly:

1. `/kerbe:coverage {slice}` in **pre-impl** mode — does the plan task everything the design
   and spec promise? This is the cheapest moment to find a dropped promise: before anyone
   builds.
2. `/kerbe:implement {slice}` — derives `claude-progress.md` from this plan and dispatches
   the work.

## Remediation mode — planning fixes, not features

Entered automatically when the slice already has a frozen `PLAN.md` (Setup step 4). The
authoring rules are unchanged; what differs is the source, the scope and the exit.

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

- Spec docs incomplete or questions open ⇒ `/kerbe:start` and specify first
- `SETTINGS.md` missing or `design_required` unanswered ⇒ `/kerbe:start`
- `design_required: true` and the Design-sources block is empty or stale ⇒ `/kerbe:figma`
  (or `dc_extract.py` under the `claude-design` adapter)
- The plan exists and you are building it ⇒ `/kerbe:implement`
- Checking what is built against what was promised ⇒ `/kerbe:coverage`

## Rules

- A frozen plan is amended by **writing a dated amendment section at its end**, never by
  editing a task a worker may already have read.
- No placeholders. "TBD", "handle edge cases", "similar to Task 3", a code step with no code
  — each is a plan defect, not a shortcut.
- The plan quotes commands from the stack adapter. A command that appears nowhere in
  `commands.md` is either a gap in the adapter (fix it there) or an invention (drop it).
- Any change to this skill or `references/plan-spec.md` must pass the plan gate in
  `fixtures/ACCEPTANCE.md` before it is used on a real project.
