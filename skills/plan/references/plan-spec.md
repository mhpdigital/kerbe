# How a `PLAN.md` is written

Self-contained authoring spec — no external skill required. Write for an implementer who is
a skilled developer with **zero context** for this codebase: they see their own task and
nothing else. Everything they need is in the task, or it does not reach them.

DRY. YAGNI. TDD. Frequent commits.

## Scope check first

If the spec covers several independent subsystems, it is more than one slice. Say so and
split it — each plan must produce working, testable software on its own. A plan that only
works once three other plans land is a phase, not a slice.

## Required header

```markdown
# {Slice Name} — Implementation Plan

**Goal:** one sentence: what this builds.
**Architecture:** 2–3 sentences: the approach, and the one decision a reader would
otherwise get wrong.
**Stack:** the adapter and the key libraries this slice touches.
**Spec:** the slice folder — the plan argues *from* the spec, so the spec travels with it.
**Design:** `design_required: true|false`; when false, the reason from SETTINGS.md; when
true, the file key + page and the date the design was measured.

## Global Constraints

One line each, exact values, copied verbatim — every task's requirements implicitly
include this section:
- base branch to cut from
- the full-suite trigger for this stack (from the adapter's `commands.md`)
- verification commands, quoted from the adapter
- every `kerbe.constraints` line
- version floors, naming/copy rules, platform requirements from the spec
```

## File-structure map

Before the tasks, map which files are created or modified and what each is responsible for.
This is where decomposition gets locked in: units with clear boundaries, one responsibility
each, files that change together living together. In an existing codebase follow its
patterns rather than restructuring under cover of a feature.

## Task right-sizing

A task is the smallest unit that carries its own test cycle and is worth a fresh reviewer's
gate. Fold setup, configuration, scaffolding and docs into the task whose deliverable needs
them; split only where a reviewer could reject one task while approving its neighbour. Each
task ends with an independently testable deliverable.

Order tasks by dependency, and say which is which: a task consuming an earlier task's output
is a **chain** (workers run one at a time); tasks touching disjoint files are a **group**
(workers run concurrently). `/kerbe:implement` reads this to choose how to dispatch, so
state it rather than leaving it to be inferred from the prose.

## Task structure

````markdown
### Task N: {deliverable}

**Files:**
- Create: `exact/path/to/file`
- Modify: `exact/path/to/existing:123-145`
- Test: `exact/path/to/test`

**Interfaces:**
- Consumes: what this task uses from earlier tasks — exact signatures
- Produces: exact names, parameter and return types later tasks rely on

**Requirements:** `REQ-...` ids this task satisfies (the spec's testable clauses)
**Design:** `node=<id> measured=<YYYY-MM-DD>` — required for every UI-bearing task

- [ ] **Step 1: Write the failing test** — the actual test code, not a description
- [ ] **Step 2: Run it, confirm it fails** — the command, and the failure you expect
- [ ] **Step 3: Minimal implementation** — the actual code
- [ ] **Step 4: Run it, confirm it passes** — the command, and the expected output
- [ ] **Step 5: Full suite** — only when this task touches a global-effect artifact; paste
      the summary line as the evidence
- [ ] **Step 6: Commit** — `git add` the named paths only, then
      `git commit -m "..." -- <the same paths>`
````

Each step is one action of a few minutes. Code steps carry code.

## Commit steps, always this shape

Stage the files this task touched, by name, and **scope the commit to the same pathspec**.
The git index is shared per repository across concurrent sessions: a bare `git commit -m`
commits the whole index, including another session's staged work. Never `git add -A`,
`git add .`, `git add *`, `git commit -a`.

## No placeholders

These are plan failures, not shorthand:

- "TBD", "TODO", "implement later", "fill in details"
- "add appropriate error handling", "add validation", "handle edge cases"
- "write tests for the above" with no test code
- "similar to Task N" — repeat it; tasks are read out of order and in isolation
- a step that says what to do without showing how
- a reference to a type, function or route defined in no task

## Self-review before freezing

Run this yourself — it is a checklist, not a dispatch:

1. **Spec coverage** — walk each spec section and point at the task that implements it. List
   what has no task, then add the tasks.
2. **Promise coverage** — every design leaf and requirement clause the slice promises is
   tasked, or explicitly deferred with a reason. (`/kerbe:coverage` pre-impl verifies this
   independently; do the pass anyway — it is cheaper to fix before the freeze.)
3. **Placeholder scan** — search the plan for every pattern above.
4. **Type consistency** — names, signatures and property names used in later tasks match
   what earlier tasks define. `clearLayers()` in Task 3 and `clearFullLayers()` in Task 7 is
   a bug already written down.
5. **Command provenance** — every command quoted appears in the stack adapter's
   `commands.md`.

Fix inline and move on; no second review pass.
