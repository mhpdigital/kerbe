---
name: bug
description: >-
  Use when a bug is reported or a change touches a data model, shared guard, migration or
  data flow — runs the impact analysis that finds every downstream consumer before the fix
  is written, so one commit closes the whole class instead of three chasing it.
disable-model-invocation: true
---

# kerbe:bug — impact analysis before the fix

The goal is **one commit that fixes everything the root cause broke**, not three commits
chasing cascading failures. The method is stack-agnostic; every concrete check comes from
the stack adapter's `impact.md`. Config seam:
`{plugin}/skills/coverage/references/config.md`.

## When to invoke

- a bug is reported (an error, missing data, a broken page or screen)
- you are adding, renaming or removing a data-model field
- you are touching a schema migration or generated model code
- you are changing a setter/constructor signature (nullability, type)
- you are changing data flow between models (copy/publish/draft, sync, cache)
- you are changing a permission boundary or a state-transition guard

## Setup

Read `kerbe.yml` (hard stop if missing). Resolve the workspace the same way
`/kerbe:implement` Step 0 does — a `{review_prefix}{slice}` workspace supersedes the slice
one; with `workspace.root` unset the resolved `stack.code_roots` entry is the workspace.
Load `adapters/stack/{name}/impact.md` (the checks) and `commands.md` (the commands), and
honour `kerbe.constraints` plus `kerbe.constraints_by_skill.bug`. Run the same preflight:
when the workspace resolves outside the project root, the fix commits in the workspace while
the finding it closes lives in the planning repo — confirm the session can write to both
first, and stop naming the path to grant if it cannot.

## Step 1 — root cause, and nothing else yet

Read the error, trace it to the exact line, name the root cause in one sentence. **Do not
fix it yet.** The value of this skill is entirely in what happens between knowing the cause
and writing the fix; a fix written at this point is the first of the three commits.

## Step 2 — impact analysis

Classify the root cause by **artifact kind** — data model, permission boundary, state
transition, schema migration — and run every check that kind lists in the adapter's
`impact.md`. Each check is a grep or a read with a stated reason.

Record the result as a short table: check, what you found, whether it needs a change. A
check you skipped is written down as skipped, with why. This table is what makes the
single-commit fix possible, and it is also the first thing a hurried session drops.

Three checks generalise past any one stack, so run them whatever the adapter says:

1. **Evidence locality** — the code you are about to call "the consumer" must live in the
   chain that actually ships the broken surface. Evidence from a neighbouring screen is not
   evidence about this one.
2. **One hop, followed** — a control that promises an action must reach a destination that
   exists **and** admits the intended audience **and** acts on the intended object. A link
   to a route the user cannot enter is as broken as a missing route.
3. **Both sides of a transition** — for "the user can do X in state S", check the guard and
   check that some real path produces S in the shape the guard accepts. Guards and producers
   drift apart silently; neither half's own test can see it.

## Step 3 — migration and generated-artifact safety

When the fix touches a schema or generated sources, follow the adapter's schema-migration
recipe before writing code: no second migration may touch the same column; an uncommitted
migration is edited in place while a committed one gets a successor; regenerate what is
generated and commit it with the change. Where the adapter declares this **n/a**, say so
rather than skipping it silently.

## Step 4 — write the fix and the tests in one pass

Fix everything Steps 2–3 found, together, and write the tests from the adapter's "required
test paths" table — populated **and** null/absent, create and update, both sides of any
transition. Keep the two fixture builders the adapter describes (fully populated, minimal)
and run both through every path.

Tests come first where the failure is reproducible: a test that fails for the reported
reason, then the fix, then the same test green. A fix with no failing test to its name is a
fix nobody can prove.

## Step 5 — validate before staging

Run, from the adapter's `commands.md`:

- the stack's global validation when the diff touches a **global-effect artifact** (for a
  schema stack: migration applied to dev **and** test, then schema validation)
- the **full** test suite — not a scoped run. A data-model change is observable through
  other components' tests, which is exactly why the scoped run comes back green
- static analysis / lint where the project configures it

All must pass, with output pasted into your report. Schema validation failing here means
Step 2 missed something — go back to Step 2 rather than patching forward.

## Step 6 — commit

One commit, **scoped by pathspec**: stage the named paths (never `git add -A`, `git add .`,
`git add *`), check `git diff --cached --stat`, and commit as
`git commit -m "..." -- <the same paths>`. The git index is shared per repository across
concurrent sessions; a bare commit sweeps up work another session staged and is not ready to
ship.

The message names the **root cause**, not the symptom:

```
fix: mirror the {field} onto {twin} + null-safe setter + migration

Root cause: {field} was added to {model} without its mirror on {twin}.
Impact: error on edit (missing property), error on publish (null), wrong
column on a fresh deploy.
```

## Step 7 — close the loop

If the bug came from a coverage fix list, re-verify the ledger rows it closed against the
**same frozen ledger** and recompute the verdict
(`{plugin}/skills/coverage/scripts/verdict.py`). If it came from a report, say which
findings it closed and which it did not.

## Anti-patterns this catches

| Anti-pattern | What happens | Caught at |
|---|---|---|
| field added to one model, not its twin | every surface using the twin errors | Step 2, mirror check |
| setter rejects null | a workflow path that legitimately produces null throws | Step 2, nullability |
| mapping points at a column a migration dropped | works locally, missing column on deploy | Step 2, migration exists |
| generated sources not regenerated | compiles, then fails at the first real payload | Step 3 |
| tests only cover the happy path | null/absent values break in production | Step 4 |
| CTA points at a route its audience cannot enter | the user pays, then gets a 403 | Step 2, one hop followed |
| cancel writes a flag the reactivate guard never accepts | the user is locked out of their own account | Step 2, both sides |
| scoped test run reported as "no regressions" | the suite was already broken elsewhere | Step 5 |
| three commits for one root cause | noisy history, broken intermediate deploys | Step 4 |

## Rules

- Analysis before code. The fix is written once, after the table exists.
- A check that cannot run is reported, never assumed clean.
- Never widen the fix into a refactor: everything in the commit traces to the root cause.
- Any change to this skill must pass the bug gate in `fixtures/ACCEPTANCE.md` before it is
  used on a real project.
