---
name: implement
description: >-
  Use when a slice's frozen plan is ready to build — resolves the workspace, derives the
  live progress tracker from the plan, dispatches one isolated worker per task, and gates
  each task on real verification evidence. Also runs remediation from a coverage fix list.
disable-model-invocation: true
---

# kerbe:implement — build the slice from its frozen plan

Task source: the slice's frozen `PLAN.md` (or a remediation fix list — see the mode at the
end). Live status: the progress tracker at the workspace root. Everything project-specific
resolves through `kerbe.yml` (`{plugin}/skills/coverage/references/config.md`).

You **orchestrate**. Workers implement, one task each, in their own context; you read their
diffs, run the gate, and record. Executing tasks yourself in the main loop burns the context
the orchestration needs and stalls long plans halfway.

## Setup

1. Read `kerbe.yml` at the project root (hard stop if missing). Resolve `planning_root`,
   `stack`, `workspace`, `executor`, and the constraints that apply to this skill
   (`constraints` plus `constraints_by_skill.implement`).
2. Load the stack adapter's `commands.md` (every command you or a worker runs comes from
   there, wrapped in `stack.exec` when configured) and the executor adapter
   (`adapters/executor/{name}.md` — it owns the dispatch mechanism; this skill states worker
   intent only).
3. **Resolve the task source — computed, never a flag:** the user's statement wins; else
   `FIX_PLAN.md` when one exists with unticked tasks (remediation mode, the section at the
   end); else `PLAN.md`. Neither present ⇒ stop and run `/kerbe:plan` — deriving tasks from
   spec docs on the fly is how an unreviewed plan gets built. State which source you are
   building from before anything else.

## Step 0 — resolve the workspace (deterministic; never ask)

**Preflight: the roots this run needs.** Resolve the planning root and the workspace, then
check whether they sit under one root or two. When the workspace resolves **outside** the
project root — the topology `code_roots` with `{slice}`, or a `workspace.root` elsewhere,
both describe — this run writes in two places: the tracker and code in the workspace, the
plan and any ledger in the planning repo. Confirm the session can write to both **before
dispatching anything**, per the executor adapter's session-roots section; if it cannot,
stop and name the exact path to grant. Discovering it mid-run leaves half the work
committed in one repo and the other half waiting on approvals.

Check what exists before creating anything — run this **in the repository the code lives
in** (the repo containing the resolved `stack.code_roots` path), not in the planning repo:

```bash
git worktree list
```

The workspace is a checkout root; `stack.code_roots` points at the app inside it. Commands
run against the app root, wrapped in `stack.exec` when configured — never guess a path
between the two, resolve both from the config.

- **`workspace.root` is unset** ⇒ there is no worktree convention: the resolved
  `stack.code_roots` entry (with `{slice}` interpolated) **is** the workspace. Verify it
  exists and, when it is a git checkout, that it is on the slice's branch. Wrong branch or
  missing path is a hard stop, never a silent build in the wrong tree.
- **A `{workspace.review_prefix}{slice}` workspace exists** ⇒ **that is the target.** It has
  already absorbed the slice branch and moved past it; the slice branch is stale by
  definition. Do not create, check out, or rebase the slice workspace. Go straight to plan
  materialisation.
- **Only `{workspace.branch_prefix}{slice}` exists** ⇒ use it.
- **Neither exists** ⇒ create it at `{workspace.root}/{workspace.prefix}{slice}` on branch
  `{workspace.branch_prefix}{slice}`, cut from the base named in `PLAN.md`'s Global
  Constraints (it wins), else `workspace.base_branch`.

Then, once:

1. **Materialise the plan if the workspace lacks it — unconditional, never a question.**
   Only applies when `workspace.planning_branch` is set (planning lives in the code repo on
   another branch): bring the slice's planning folder across from that branch. When the
   planning root is its own repository, there is nothing to materialise — read the plan
   where it lives.
2. Run `workspace.setup_cmds` to stand the environment up (containers, database, seed data).
   Skip on an existing workspace, and say that you skipped them.

This step is mechanical. Never raise branch topology as a question.

## Step 1 — the audit that precedes the tracker

Before writing any tracker, establish what already exists: run `/kerbe:audit` if the slice
has prior work, otherwise read the workspace for the plan's artifacts. The result is a
DONE / PARTIAL / MISSING position per plan task. A tracker written without this restarts
finished work and reports it as progress.

## Step 2 — derive the progress tracker

Write `{workspace.progress_file}` (default `claude-progress.md`) at the **workspace root**,
from `references/progress.md`. It is the single source of truth for status: visible,
git-tracked, user-editable, and the thing that survives a compaction.

`PLAN.md` and the tracker relate as plan↔execution: the plan (in the slice folder) defines
the tasks and is frozen; the tracker (at the workspace) carries status, current task,
blockers, and files touched. Never merge them, never keep a second tracker, and never put
tracking state in a hidden dotfolder — not `.superpowers/`, `.claude/`, `.cloud/`, or any
other tool's `.<name>/`, however insistently a sub-skill asks. If you delegate to a
sub-skill that ships its own ledger convention, **override it**: status goes in the tracker,
briefs and reports go in the slice's visible planning folder.

If the user edits the tracker — reorders, removes, rewrites — those edits stand.

## Step 3 — choose the execution shape (from the plan, not from preference)

Two **orthogonal** axes. Never conflate them.

**Isolation — one worker per task, always.** Each task goes to a fresh worker that does its
own red → green → commit and reports back briefly. "Sequential" is a statement about task
*order*, not about running tasks in the main loop. The only exception is a trivial plan
(≤2 tasks), where the overhead outweighs the benefit — and the `inline` executor adapter
already describes what you give up.

**Concurrency — read it off the plan's dependency structure.**

| Plan shape | Dispatch |
|---|---|
| **chain** — each task consumes an earlier task's output (backend, migration, importer slices) | workers run **one at a time, in order**, in the shared workspace. Do not fan out: they would serialise anyway and collide. |
| **group** — tasks touch disjoint files (pages, templates, styles, endpoints) | workers run **concurrently**, each filesystem-isolated per the executor adapter, dispatched together in one go. |

Group membership is a **file-ownership contract**: each worker's brief names the files it
owns, no two workers own the same file, a template and the styles and controller serving it
belong to one worker, and end-to-end browser tests always come last, after the features
they exercise work.

## Run to completion — the session does not pause

An implementation run is dispatched to finish, not to narrate. Between tasks there is no
"should I continue?", no progress summary addressed to the user, no confirmation request —
the user asked for the plan to be executed, so execute it. The tracker is the narration.

**Rulings, not stalls.** Ambiguities, plan defects, conflicts between a finding and the
plan text — decide them and keep going. The spec is the binding authority, the plan is its
argument, and your judgment settles what neither answers. Record every such decision in the
tracker as a Ruling: what you decided, why, and what it costs if wrong. A wrong ruling
costs rework the user can see and undo; a session parked on a question costs the whole run.

**A blocked subtask is noted and stepped around, never retried in a loop.** Record it in
the tracker where it happened, move to the next unblocked task, and keep working until
nothing unblocked remains.

**Only these stop the session mid-run:** an irreversible or destructive operation; a
security-sensitive action; a side effect beyond the workspace that norms say to ask about
first (a merge, a push to a shared branch, a publish); a decision that is genuinely the
user's (scope, sequencing between slices, dropping a promise); or a plan so broken that
every path forward is a guess.

**Ending the run.** When the session's user instructions define end-of-run markers for
unattended operation (see the executor adapter's session-signals section), emit exactly
one, on its own line, as the last thing: the *waiting* marker when stopped on a user
decision — with the open questions and every unblocked task already worked; the *complete*
marker only when every task is done, the full-suite evidence is in the tracker, and
nothing is left open. Never the complete marker over failing tests or unfinished tasks,
and never neither — a run that just trails off strands the automation watching it.

## Step 4 — dispatch

Per the executor adapter, one worker per task, with a **self-contained** brief:

- the workspace path and the branch it must stay on
- the task's own text, quoted from the frozen plan (including its `node=` design origin and
  `REQ-` targets)
- the exact files it may create or modify — and that it may touch nothing else
- the project conventions it must follow, from the stack adapter
- the verification commands with expected output, quoted from `commands.md`
- every `kerbe.constraints` line, plus `kerbe.constraints_by_skill.implement`, verbatim
- the two git rules: stage the named paths only (never `git add -A`, `git add .`,
  `git add *`), and commit scoped by pathspec (`git commit -m "..." -- <paths>`), because
  the git index is shared across concurrent sessions and a bare commit takes another
  session's staged work with it
- what to report: files changed, commands run **with pasted output**, anything it could not
  do

## Step 5 — the per-task gate (this is the step that catches the expensive class)

A task is done when its evidence says so, not when its report does.

1. **Read the diff.** A report describes intent; the diff is what happened.
2. **Scoped runs prove scoped things.** If the diff touches any **global-effect artifact**
   listed in the stack adapter's `commands.md`, the task is not done until the stack's
   global step has run (for a schema stack: migration applied to **both** dev and test, then
   schema validation) **and the full suite has been run with its summary pasted**. A scoped
   test run is never accepted as a no-regression claim.

   Why this rule exists: a change whose effect is only observable through *other*
   components' tests cannot be validated by a scoped run. One mapped column, added and
   migrated but never applied to the test database, has taken a suite from green to 46
   failures with an implementation report stating "no new test failures introduced" — and
   the report was honest about what it ran.
3. **Blocked runner ⇒ repair it, never bypass it.** If the stack's global command refuses
   because of an unrelated pre-existing failure, fix the runner and say what you fixed. A
   documented bypass is a defect entrenched in every future session.
4. Tick the tracker **as each task completes**, not in bulk at the end, and record blockers
   where they happen. Do not stop to ask whether to continue.

## Step 6 — integrate

1. Verify no two workers touched the same file; resolve overlaps before merging.
2. Merge concurrent workers' branches back into the slice branch.
3. Run the full suite on the merged result — the per-task gate does not make this optional,
   because merges create interactions no single task's run could see.
4. Failures: attribute to the worker whose change caused them. Small ones you fix in the
   workspace; a large one gets a focused fix worker with the same brief discipline.
5. Update the tracker, and stamp `TIMING.md`'s implement row with
   `TZ='{kerbe.timezone}' date '+%Y-%m-%d %H:%M'` (timestamp only, no effort).

## Step 7 — hand off

`/kerbe:coverage {slice}` in **audit** mode: is everything the design, spec and plan
promised actually built and wired? Then review. Implementation reporting itself complete is
not the same as the slice being finished, and only the ledger can tell those apart.

## Remediation mode — building from a coverage fix list

When the task source is a fix list from a coverage run (rows citing frozen ledger ids)
rather than a plan:

- The slice's `PLAN.md` and `PROMISES.md` stay **frozen**. The ledger is the denominator;
  fixing rows does not move it, which is exactly what makes progress measurable.
- Work the list in its stated order — blockers first. Each fix cites the ledger ids it
  closes; the tracker carries those ids so a half-finished session is resumable.
- A defect whose fix could break other components (a data-model change, a shared guard, a
  state transition) goes through `/kerbe:bug` first — impact analysis before the fix, so one
  commit closes the whole class instead of three chasing it.
- A design-only row is a **spec decision before it is work**: add the leaf to the spec docs
  and then build it, or record a dated decision to drop it. Never build straight from a
  design leaf the spec never accepted.
- Exit condition: re-verify the closed rows against the same frozen ledger and recompute
  `{plugin}/skills/coverage/scripts/verdict.py` — the verdict, not your summary, says how
  much closer the slice is.

## Rules

- One tracker, at the workspace root, never a hidden dotfolder, never a second file.
- Workers report; the orchestrator records. Two writers on one tracker is how it starts
  lying.
- Every task's file list is its contract — a worker that edits outside it gets reverted, not
  rationalised.
- Commit scoped by pathspec; check `git diff --cached --stat` before committing and leave
  anything you did not stage alone.
- Never add features the plan does not call for. An improvement noticed mid-task is a note
  in the tracker, not a diff.
- The session runs to completion per **Run to completion** above — questions the user must
  answer are collected and asked once, at the stop, not sprinkled through the run.
- Any change to this skill or its references must pass the implement gate in
  `fixtures/ACCEPTANCE.md` before it is used on a real project.
