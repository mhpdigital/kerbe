# Executor adapter: codex

How a **read-only reviewer** is dispatched to an OpenAI model through the Codex CLI. It is
a routing target, not a session executor: a project points one task class at it through
`executor.routing` (e.g. `review-critic: codex@deep`) and keeps `executor.adapter` as the
session's own. The point is a second model family. A critic from the same family as the
first pass shares its blind spots; a different one shares fewer.

## Capabilities

| Capability | Supported | Notes |
|---|---|---|
| isolated worker (fresh context) | yes | each call is a new `codex exec` process with `--ephemeral`; it sees only the brief |
| filesystem-isolated worker | **n/a** | the worker is read-only (`-s read-only`), so there is nothing to isolate |
| concurrent workers | **n/a** | one call at a time; the critic loop is sequential by design |
| effort levels | `low` / `standard` / `deep` | map to `gpt-5.6-luna` medium / `gpt-5.6-sol` medium / `gpt-5.6-sol` high. Chosen for a personal ChatGPT plan: `gpt-6-astra` is stronger but spends the plan's allowance far faster. This table is the one place to change the mapping |
| structured completion output | no | the worker's last message is prose, written to a file with `-o` |

## Invoke

The brief goes in on stdin; the last message comes back in a file. Run from the session's
shell, never through a subagent:

```bash
codex exec -m <model> -c model_reasoning_effort=<reasoning> \
  -s read-only --ephemeral -C <workspace> [--add-dir <planning_root>] \
  -o <out file> - < <brief file>
```

- `<workspace>` is the slice's code workspace. Add `--add-dir <planning_root>` when the
  spec docs live outside it, or the critic cannot cross-check them.
- Write the brief and out file to the system temp directory (`mktemp`), never to a hidden
  folder in the project, and delete both after reading the result.
- The brief is self-contained: the diff range, the draft QR verbatim, the spec doc paths,
  and the critic's checklist from the skill. The worker has none of the session's history.

## Session roots

`-s read-only` lets the worker read anything the OS lets it read, and write nothing.
`-C` and `--add-dir` set where it starts and which roots it is told about; a root it is
not told about it will rarely look in. Pass every root the brief cites.

## Output contract

The out file holds the critique: each problem with the file and line it cites, and the
change it wants to the draft. The orchestrator verifies each claim against the code before
revising the draft. A critic from another model family is still a reader, not an
authority.

## Limits

- **Needs the Codex CLI signed in** (`codex login`) on the machine running the session.
  When the call fails (not installed, signed out, plan allowance used up), run the critic
  through the session's own adapter instead and record which one ran, e.g.
  `**Adversarial pass:** ran (claude@deep — codex unavailable: <reason>)`. Never skip the
  pass because the routed executor failed.
- **Plan allowance is the budget.** Each critic round is one call against the personal
  plan. Route only the critic here, not workers that write code.
- **Read-only.** It cannot fix what it finds; the orchestrator revises the draft.
- **No session signals.** It never emits the session's completion markers; its output is
  data for the orchestrator.
