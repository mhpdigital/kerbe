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
**Executor:** {adapter}  ·  **Shape:** chain | group
**Tests:** {n} passing, {n} failing  ({command}, {date})

## Position
| Plan task | Status | Worker | Evidence |
|---|---|---|---|
| Task 1: {deliverable} | done | W-A | {commit} · full suite pasted {date} |
| Task 2: {deliverable} | in progress | W-B | — |
| Task 3: {deliverable} | todo | — | — |

Status vocabulary: `todo` · `in progress` · `done` · `blocked` · `parked`.
`done` requires evidence in the row — a commit, and for a global-effect task the full-suite
result. No evidence, not done.

## Worker {letter}: {domain}
- [ ] {plan task or fix id}
- [ ] {plan task or fix id}
**Owns:** the exact files this worker may touch — no other worker may name the same file

## Blockers
- {what, where it was hit, what it needs} — noted, moved on

## Rulings
- {decision} — {why} — {what it costs if wrong}

## Files touched this session
- {path}
```

## Rules

- Ticked **as each task completes**, never in bulk at the end. A tracker updated in bulk is
  a tracker that was wrong for the whole session.
- A blocker is recorded and stepped around, not retried in a loop.
- In remediation mode the "Plan task" column carries **ledger ids** instead, so a closed row
  can be re-verified against the frozen ledger without reconstructing what was fixed.
- Never a second tracker, never a hidden dotfolder, never task-tracking tooling in place of
  this file: it must survive a compaction and a fresh session, and be readable by a human
  who was not here.
