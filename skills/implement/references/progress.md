# The progress tracker

One file, at the workspace root, named by `kerbe.workspace.progress_file` (default
`claude-progress.md`). Derived from the frozen plan; carries status only. Visible,
git-tracked, and editable by the user — their edits stand.

## Shape

```markdown
# {Slice Name} — Implementation Progress

**Slice:** {slice-id}
**Workspace:** {path}  ·  **Branch:** {branch}
**Plan:** {planning_root}/{slice}/PLAN.md  ·  **Started:** {YYYY-MM-DD}
**Executor:** {adapter}  ·  **Lanes:** {n} ({lane-free tasks run in a worktree, no lane})
**Tests:** {n} passing, {n} failing  ({command}, {date})

## Position
| Plan task | Depends | Lane | Status | Worker | Evidence |
|---|---|---|---|---|---|
| Task 1: {deliverable} | none | 0 | done | W-A | {commit} · full suite pasted {date} |
| Task 2: {deliverable} | 1 | 1 | in progress | W-B | — |
| Task 3: {deliverable} | 1 | none | todo | — | — |

`Depends` is copied from the plan task, not re-derived here — the tracker records what was
scheduled so a resumed session rebuilds the same queue. `Lane` is `none` for a lane-free
(all-`unit`) task, `0` for the workspace, `1..n` for an extra lane.

Status vocabulary: `todo` · `in progress` · `done` · `blocked` · `parked`.
`done` requires evidence in the row — a commit, and for a global-effect task the full-suite
result. No evidence, not done.

## Worker {letter}: {domain}
- [ ] {plan task or fix id}
- [ ] {plan task or fix id}
**Owns:** the exact files this worker may touch — no other worker may name the same file

## Blockers
- {what, where it was hit, what it needs} — noted, moved on

## Deviations
- {plan task} — plan said {X} · found {Y} · did {Z}

## Rulings
- {decision} — {why} — {what it costs if wrong}

## Files touched this session
- {path}
```

## Rules

- Ticked **as each task completes**, never in bulk at the end. A tracker updated in bulk is
  a tracker that was wrong for the whole session.
- A blocker is recorded and stepped around, not retried in a loop.
- A **deviation** is where the plan and the codebase disagreed and the codebase won. Record
  it as the task lands, in the worker's own three parts. On an unattended run this section is
  what the next human reads instead of the diff, and an empty one on a run that clearly
  diverged means the diff still needs reading.
- In remediation mode the "Plan task" column carries **ledger ids** instead, so a closed row
  can be re-verified against the frozen ledger without reconstructing what was fixed.
- Never a second tracker, never a hidden dotfolder, never task-tracking tooling in place of
  this file: it must survive a compaction and a fresh session, and be readable by a human
  who was not here.
