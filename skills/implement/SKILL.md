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

## Step 3 — build the schedule (from the plan's graph, not from a label)

Two **orthogonal** axes. Never conflate them.

**Isolation — one worker per task, always.** Each task goes to a fresh worker that does its
own red → green → commit and reports back briefly. "Sequential" is a statement about task
*order*, not about running tasks in the main loop. The only exception is a trivial plan
(≤2 tasks), where the overhead outweighs the benefit — and the `inline` executor adapter
already describes what you give up.

**Concurrency — computed from a dependency graph.** There is no per-plan chain/group label:
one word for a whole plan cannot say that tasks 2 and 3 are independent while 4→5→6 is a
genuine chain, and reading it as a chain serialises the pair for nothing.

### 3a — build the graph

Take the **union** of two sources, and never just one:

- **declared** — each task's `**Depends:**` line
- **derived** — task B depends on A when B's `Interfaces: Consumes` names anything in A's
  `Interfaces: Produces`, or B's `Files: Modify` names anything in A's `Files: Create`

The union is the safe direction: a missing edge causes a race, a spurious edge only costs
serialisation. Where the two disagree, record a **Ruling** naming the task and the edge and
carry on — it is a plan defect worth reading. A derived-but-not-declared edge means the
planner missed a dependency; a declared-but-not-derived edge is either a real ordering
constraint with no named seam (legitimate) or caution that cost concurrency.

**When the derivation cannot run, say so — never simulate it.** A task source that carries no
`Interfaces` or `Files` blocks (a checkbox stub, a remediation fix list) gives the derived
half nothing to read. Degrade to the declared edges alone and record that you did, in one
line. Inferring edges by eye from prose and then reporting them as *derived* is worse than
not deriving: it presents a guess with the authority of a cross-check, and the disagreement
Ruling — the thing that makes the union worth computing — becomes noise.

A **cycle is a hard stop**, not a Ruling: the tasks are not independently deliverable and the
plan needs re-cutting.

### 3b — resolve the lanes

A **lane** is an isolated verification environment — a worktree plus what it takes to run the
tests against it. Lane 0 is the workspace from Step 0. Resolve `workspace.lanes` (default
`1`), `workspace.lane_setup_cmds`, and `workspace.worktree_setup_cmds`.

- **`lanes > 1` and `stack.exec` has no `{lane}`** ⇒ **hard stop**, naming the key. Every
  lane would route its commands to the same environment, and a worker that can edit files
  while verifying nothing is the exact failure this design exists to prevent.
- **`worktree_setup_cmds` unset** ⇒ run every task in lane 0 and **say why**. A fresh git
  worktree has source and no installed dependencies, so a worker there cannot run its test
  command at all.

A task is **lane-free** when every case in its table is `unit`; it needs a worktree and
`worktree_setup_cmds`, nothing more. Any other task is **lane-bound**.

### 3c — dispatch from a ready queue, never in waves

A wave — compute everything ready, run it all, barrier, repeat — makes every task wait for
the slowest in its wave. That is the same waste this schedule exists to remove.

1. `ready` = tasks whose dependencies are all complete and which have not started.
2. Dispatch every lane-free ready task concurrently, each in its own worktree, no lane.
3. Dispatch lane-bound ready tasks up to the number of free lanes.
4. When a worker completes **and its gate passes**, recompute `ready` and refill immediately.
   Do not wait for its siblings.

The **file-ownership contract** governs whatever is running at one time: each worker's brief
names the files it owns, no two concurrent workers own the same file, a template and the
styles and controller serving it belong to one worker, and end-to-end browser tests always
come last, after the features they exercise work. Where two ready tasks would own the same
file, hold one back and record a Ruling — it is an ordering constraint the graph did not
capture.

**Resolve ownership against the codebase, not against the plan's claim about itself.** A plan
asserting that two tasks "touch different files" was written before the code existed; the
files decide. Two tasks that both render onto one template collide however independent the
graph says they are, and the graph will not tell you — `Depends` describes what a task
*consumes*, never what it *writes*. Step 1's audit is where you learn this, so carry its
reading into the schedule: dispatching on the graph alone is how two workers end up editing
one template concurrently and the second one's merge quietly wins.

## Run to completion — the session does not pause

An implementation run is dispatched to finish, not to narrate. Between tasks there is no
"should I continue?", no progress summary addressed to the user, no confirmation request —
the user asked for the plan to be executed, so execute it. The tracker is the narration.

**Rulings, not stalls.** Ambiguities, plan defects, conflicts between a finding and the
plan text — decide them and keep going. The spec is the binding authority, the plan is its
argument, and your judgment settles what neither answers. Record every such decision in the
tracker as a Ruling: what you decided, why, and what it costs if wrong. A wrong ruling
costs rework the user can see and undo; a session parked on a question costs the whole run.

A **Ruling** is yours — a judgment the plan and spec left open. A **Deviation** is a
worker's — a place the plan simply did not match the code. They go in different sections
because they are read for different reasons: rulings tell the user what you chose, deviations
tell them what the plan got wrong.

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

Per the executor adapter, one worker per task, with a **self-contained** brief. **Effort
level per task, stated explicitly on every dispatch** (the adapter maps it to a model —
never leave the model to inherit). **Read it off the task's `**Effort:**` line in the plan**:
the planner set it with the whole slice in view, and it also fixes how much code that task
carries, so overriding it at dispatch hands a typist's brief to a designer or the reverse. A
task with no effort line is a plan defect — dispatch it `standard`, and record a Ruling
saying which task and what you assumed.

- the workspace path and the branch it must stay on — and, when the task runs outside lane 0,
  its worktree path and the `stack.exec` wrapper with `{lane}` already resolved, so the
  worker never has to work out which environment it is verifying against
- the task's own text, quoted from the frozen plan — its `Interfaces`, its case table **with
  the `Level` column intact**, its `Decisions` block, its `node=` design origin and its
  `REQ-` targets. The declared level is binding: a worker may add cases at any level, but
  moving a planned case to a cheaper level is a deviation to report, never a quiet
  substitution
- the exact files it may create or modify — and that it may touch nothing else
- the project conventions it must follow, from the stack adapter
- the verification commands with the expected output shape, quoted from `commands.md`
- every `kerbe.constraints` line, plus `kerbe.constraints_by_skill.implement`, verbatim
- the two git rules: stage the named paths only (never `git add -A`, `git add .`,
  `git add *`), and commit scoped by pathspec (`git commit -m "..." -- <paths>`), because
  the git index is shared across concurrent sessions and a bare commit takes another
  session's staged work with it
- **the deviation protocol** (below), stated in the brief, not assumed
- what to report: files changed, commands run **with pasted output**, deviations, anything it
  could not do

### The deviation protocol — every brief carries it verbatim

A plan is written before the code exists, so parts of it will be wrong by the time a worker
reads it. The worker needs one rule for that moment, or it will either copy the plan into a
mismatch or diverge silently — and a silent divergence turns every later "verified against
the plan" into a check against fiction.

> Where the plan and the codebase disagree, **the codebase wins on mechanism and the case
> table wins on behaviour.** Implement what actually compiles and passes, then report the
> deviation as three lines — *plan said* / *found* / *did* — and carry on. Do not stop, do not
> ask, do not quietly conform.
>
> **Case values are not yours to change.** Add cases freely, name and structure the test
> however the harness requires, but a value the plan specified stays. If it cannot pass,
> that is a deviation to report, never a test to edit.
>
> Anything the plan does not name is yours: internal helpers, private methods, exception
> classes caught inside your own task, local structure. Names in the task's `Interfaces`
> block are seams other tasks depend on — those stay exactly as written.

Deviations are the run's most valuable output. Copy each one into the tracker's Deviations
section as the task lands, so the morning read is a short list of what the plan got wrong
rather than a diff review. A worker that reports none on a task that clearly diverged is a
worker whose diff you read line by line.

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
4. **Check the case values, not just the colour of the run.** A green suite proves the tests
   that exist pass, not that they are the tests the plan asked for. Compare the task's case
   table against the diff: a case missing, or a value changed to something the worker could
   make pass, is a deviation whether or not it was reported. Added cases are fine.
5. **Check the declared level against the harness the worker actually used.** The diff says
   which base class each test extends; the case table says which level the plan bought. A
   mismatch is a deviation, reported rather than absorbed. The dangerous direction is
   **declared `http`, written as `unit`** — that silently drops an acceptance floor, and the
   suite stays green while the promise stops being checked. The reverse (declared `unit`,
   written against the framework) is waste rather than risk, but it is still a deviation:
   the plan costed that task as lane-free and it was not.
6. Tick the tracker **as each task completes**, not in bulk at the end, and record blockers
   and deviations where they happen. Do not stop to ask whether to continue.

## Step 6 — integrate

1. Verify no two workers touched the same file; resolve overlaps before merging.
2. Merge concurrent workers' branches back into the slice branch.
3. Run the full suite on the merged result **in lane 0** — the per-task gate does not make
   this optional, because merges create interactions no single task's run could see, and a
   per-lane green is a claim about that lane's tree only.
4. Failures: attribute to the worker whose change caused them. Small ones you fix in the
   workspace; a large one gets a focused fix worker with the same brief discipline.
5. Run `workspace.lane_teardown_cmds` for every lane above 0. Lane 0 is the workspace and is
   never torn down here.
6. Update the tracker, and stamp `TIMING.md`'s implement row with
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
- Effort comes from the plan's task, never from preference at dispatch, and never inherited.
- Concurrency comes from the dependency graph, never from a label and never from appetite.
  A cycle stops the run; a disagreement between declared and derived edges is a Ruling.
- A case's level is the plan's decision. A worker that writes a planned `http` case as a
  `unit` test has dropped an acceptance floor, and a green suite cannot show it — the gate
  reads the base class in the diff, not the report.
- A worker may add cases; a case value the plan specified is changed only by reporting a
  deviation. An edited case value that arrives unreported is the one failure mode a green
  suite cannot show you.
- Deviations are recorded in the tracker as they land — *plan said / found / did*. They are
  what the next human reads instead of the diff.
- Commit scoped by pathspec; check `git diff --cached --stat` before committing and leave
  anything you did not stage alone.
- Never add features the plan does not call for. An improvement noticed mid-task is a note
  in the tracker, not a diff.
- The session runs to completion per **Run to completion** above — questions the user must
  answer are collected and asked once, at the stop, not sprinkled through the run.
- Any change to this skill or its references must pass the implement gate in
  `fixtures/ACCEPTANCE.md` before it is used on a real project.
