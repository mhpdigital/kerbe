# Executor adapter: inline

Fallback for a harness with no subagent mechanism (or a session where dispatch is
unavailable). Tasks run **in the main loop**, one at a time, in plan order.

## Capabilities

| Capability | Supported | Notes |
|---|---|---|
| isolated worker (fresh context) | **n/a** | there is one context; it accumulates |
| filesystem-isolated worker | **n/a** | all tasks share the workspace |
| concurrent workers | **n/a** | strictly sequential |
| effort levels | **n/a** | whatever the session runs at |
| structured completion output | n/a | you are the worker and the orchestrator |

## Invoke

For each task, in order: read the task from the frozen plan → write the failing test → run
it and paste the failure → implement → run it and paste the pass → run the task's
verification commands → commit scoped by pathspec → tick the progress ledger.

## Session roots

Whatever confines file access in the harness running you applies unchanged — there is no
worker to grant anything to. Resolve every root the task needs before starting, and if one
is out of reach, say which path needs granting and stop.

## Limits — say these out loud when this adapter is in use

- **Context is the constraint.** A long plan will exhaust it; compact at ~50% and keep the
  progress ledger current, because after a compaction the ledger is what survives.
- **No per-task review checkpoint by a fresh reader.** You review your own work, which is
  weaker. Compensate with a whole-branch review before integration.
- Only choose this adapter deliberately: a trivial plan (≤2 tasks), or a harness that has
  no worker mechanism. It is not the default and never a preference — running tasks inline
  because it feels faster is how a long plan stalls halfway.
