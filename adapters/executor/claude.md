# Executor adapter: claude

How a **task worker** is dispatched when the harness is Claude Code. Skill bodies state
worker *intent* only — "run this task in an isolated worker, fresh context, structured
completion report". This file owns the mechanism, so the lifecycle stays harness-neutral.

## Capabilities

| Capability | Supported | Notes |
|---|---|---|
| isolated worker (fresh context) | yes | one worker per task; it never inherits the orchestrator's history |
| filesystem-isolated worker | yes | `isolation: "worktree"` — a private git worktree per worker. Files only: see **A worktree is not a lane** below |
| concurrent workers | yes | dispatch all independent workers in **one** message so they run at once. How many is decided by the plan's dependency graph and `workspace.lanes`, not by this adapter |
| background workers | yes | `run_in_background: true`; the orchestrator is re-invoked on completion |
| effort levels | `low` / `standard` / `deep` | map to `model: haiku` / `sonnet` / `opus`. The level comes from the plan task's `**Effort:**` line, not from the dispatcher — it also fixed how much code that task carries. Never omit `model`: a worker with no model inherits the session's, which under Night Shift's routing may be the dearest tier — `deep` is Opus, not "whatever the orchestrator runs on" |
| structured completion output | no | workers return prose. The orchestrator re-derives every claim from the diff — see limits |

## Invoke

Dispatch with the built-in Agent tool:

```
Agent({
  description: "<task id>: <deliverable>",
  subagent_type: "general-purpose",
  model: "<per effort level>",
  isolation: "worktree",          // ONLY for file-independent workers running concurrently
  run_in_background: true,        // when several run at once
  prompt: "<the self-contained worker brief>"
})
```

**`isolation: "worktree"` is for concurrency, not for hygiene.** Two tasks that the graph
forces into sequence run one at a time in the shared workspace — giving each of those its own
worktree only adds merges. Use it when two or more workers run at the same time and could
touch the same tree.

**A worktree is not a lane.** `isolation: "worktree"` gives a worker its own *files*; it does
not give it anywhere to run the tests. A fresh worktree has source and no installed
dependencies, and on a stack whose test command is bound to a container it has no runner at
all. So a dispatch carries both:

| Task | Gets |
|---|---|
| lane-free (every case `unit`) | a worktree + `workspace.worktree_setup_cmds`. No lane, no container. |
| lane-bound (any `kernel`/`http`/`browser` case) | a worktree + a lane index, and every command wrapped in `stack.exec` with `{lane}` resolved to that index |

The orchestrator resolves `{lane}` before the brief is written — a worker must never be left
to work out which environment it is verifying against. With `workspace.lanes > 1` and no
`{lane}` in `stack.exec`, do not dispatch at all: every lane would route to the same
environment, producing workers that edit files and verify nothing.

A worker brief is self-contained: workspace path (and its worktree path and resolved lane
wrapper when it runs outside lane 0), the task's own text from the frozen plan with its case
table and `Level` column intact, the exact files it may create/modify, the project
conventions it must follow, the verification commands with their expected output shape,
`kerbe.constraints` verbatim, the deviation protocol (what to do when the plan and the
codebase disagree — the lifecycle skill owns its wording), and the two git rules (stage named
paths only; commit scoped by pathspec).

## Session roots

This harness confines file access to the session's working roots. A two-root topology —
planning docs in one repository, the slice's code in a sibling workspace — needs **both**
granted before any task runs, and a worker inherits exactly the roots the session has:
dispatching does not widen them.

- in-session: `/add-dir <path>`
- at launch: `claude --add-dir <path>`
- persistently, for a project run this way every time: an `additionalDirectories` entry in
  the project's settings

The directories existing on disk is not the same as the session being scoped to them: a
path outside the session's roots is not blocked, it is **approved action by action**. That
is survivable when someone is watching and fatal to an unattended run, which stalls on the
first prompt with half its work done. Resolve every root the run needs before dispatching
anything, and name the exact path to grant rather than working around the gap.

## Session signals for unattended runs

Claude Code sessions are often run under an outer loop (the user's harness automation)
that reads the session's **last line** to decide what happens next. The convention lives
in the user's instructions, not here — commonly a pair of sentinels such as
`<task-complete/>` (everything done, tests green, nothing open) and `<waiting-for-user/>`
(stopped on input the user must provide). When the session's user instructions define such
markers:

- the **orchestrator** emits them — exactly one, on its own line, as the very last output
  of the turn that stops. Workers never emit them; a worker's report is data, not a
  session signal.
- the *complete* marker is a verified claim: every task done, evidence recorded, tests
  green. Emitting it over open tasks or failing tests defeats the automation it feeds.
- the *waiting* marker means "nothing unblocked remains and a human decision is needed" —
  not "I have a question mid-run". Work everything workable first, then stop once with
  all the questions together.
- a progress-file convention in the user's instructions (e.g. autonomous mode triggered by
  the tracker existing at the project root) applies to the whole run — honour it from the
  first task, not from the point where someone notices.
- **the guard attaches to the harness, not the model.** A Stop-hook enforcing these markers
  runs client-side against the local transcript, so swapping the model provider under
  Claude Code (an Anthropic-compatible endpoint via `ANTHROPIC_BASE_URL` — see Provider
  routing below) inherits it for free; only swapping the *harness* costs anything. Workers
  never fire the session Stop event at all — a worker ending is a subagent event, and its
  contract is enforced by the orchestrator reading the report, per the output contract.
  Expect a cheaper routed model to trip a marker guard more often than a frontier one; that
  is the guard working, not misconfiguration.

## Output contract

The worker's final message is its completion report and must carry: what it changed
(paths), the verification commands it ran with **pasted output**, every **deviation** from
the plan as *plan said / found / did*, anything it could not do, and any ruling it made.
Intent is not evidence — a report with no pasted command output is an **unverified** task,
and the orchestrator treats it as such.

Deviations carry the most information per line in the whole report: the plan was written
before the code existed, so the places it was wrong are exactly what the next reader needs.
A worker that conforms silently to a plan that did not match the codebase produces a green
run and a false record.

## Limits

- **No structured output.** Reports are prose and can be optimistic; the orchestrator reads
  the diff itself before ticking anything off.
- **A worker cannot ask a question mid-flight.** Everything it needs goes into the brief.
- **A worker cannot dispatch its own workers.** Nested fan-out is the orchestrator's job.
- **Workers do not write the progress ledger.** They report; the orchestrator records. Two
  writers on one file is how a tracker starts lying.
- Hooks and permission prompts apply inside workers too — a worker blocked on a permission
  reports a failure it cannot itself resolve.

## Provider routing (optional)

A project may route routine workers to a cheaper Anthropic-compatible endpoint by exporting
`ANTHROPIC_BASE_URL` / `ANTHROPIC_AUTH_TOKEN` before dispatch. Resolve the token the same
way the design leg resolves its own: from an env var, or from a command the project
configures — **never a literal token, path, or vendor account in a skill, brief, ledger,
report or summary.** Keep the final whole-branch review, architecture rulings, and any
security-sensitive task on the session's strongest model.
