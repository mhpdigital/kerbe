# How a `PLAN.md` is written

Self-contained authoring spec — no external skill required. Write for an implementer with
**zero context** for this codebase: they see their own task and nothing else, and they cannot
ask. Everything they need is in the task, or it does not reach them.

*How much* they are told is set by the task's effort level, because a task can be dispatched
to a typist or to a designer and the two need opposite things. *What* they are told never
varies: the seams, the cases, the constraints, and the commands.

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

## Effort per task — decided here, not at dispatch

Every task carries `**Effort:** low | standard | deep`. It is a planning decision: the
planner is the only party who can weigh a task's risk against the whole slice, and the value
stays reviewable while the plan is still being read. `/kerbe:implement` reads it off the task
and the executor adapter maps it to a model or reasoning level.

**How much code the plan carries is a function of who executes the task, not of the slice.**

| Effort | The task | What the plan owes the worker |
|---|---|---|
| `low` | mechanical — fixtures, seed data, generated boilerplate, doc stubs, a file that follows an existing one line for line | **the code, in full.** A low-effort worker is a typist; anything it has to invent is a defect at this level. |
| `standard` | ordinary implementation against a settled interface | the seams and the cases (below), plus any fragment where the *how* is itself a decision. Not the bodies. |
| `deep` | tier-1 business logic, a data-model change, a shared guard, a security boundary | everything `standard` gets, plus the questions this task must settle and report. Never a body: code written against an imagined codebase makes a designer's job worse, not easier. |

`standard` is the default. Choosing `deep` is what makes a task expensive; choosing `low` is
what makes a plan long. Both are deliberate, and both are visible in review.

## The seam rule — what the plan owns

The plan owns the **seams between workers**; the worker owns everything inside a seam. A
worker runs in a fresh context and cannot ask, so anything that crosses a seam must be fixed
here. Anything that never leaves the task is the worker's to name.

A name belongs in **Interfaces → Produces** when, and only when, it is one of:

- consumed by another task in this plan
- asserted by a test the plan specifies
- read by a later slice, a route table, a schema, or a payload someone else parses

Everything else stays out: internal helpers, private methods, an exception class caught
inside the same task, local data shapes, constructor wiring. Listing them costs the plan its
reviewability and buys nothing, because no second worker can observe them.

Sparse form per seam: name, inputs, output shape, failure behaviour. Where the *how* is
itself a decision a worker could plausibly get wrong — a normalisation library, an ordering
guarantee, a locking strategy — write the two or three deciding lines and one sentence on
why. A fragment, not a file.

**The test to apply:** would two competent workers, given the interface and the cases, write
materially different code here? If no, leave it out and say "implement to pass the cases;
follow the pattern in `<existing file>`". If yes, and the difference matters, write the lines
that decide it.

## Step 1 carries cases, not a test file

The plan owns **what must be true**; the worker owns the harness that proves it. A test
written before any code exists is largely a guess about fixtures, container access, login
helpers and database reset — and when that guess is wrong the worker edits the test, which
rewrites the spec with nobody watching.

So Step 1 names the test file and class and lists the cases as a table: input or
precondition, expectation, and the `@req` it discharges. Write the test code in full only
where the harness **is** the requirement (a security boundary, a cross-tenant assertion, a
serialisation contract), and at `low` effort, which gets everything in full.

A case value is a decision the plan made. A worker may add cases, and may name and structure
the test however the harness demands, but may never change a case value — that is a
deviation, and `/kerbe:implement` has it reported rather than absorbed.

## Expected output is a shape, not a count

`OK (4 tests, 7 assertions)` is wrong the moment a worker adds an assertion the plan
welcomed. The worker then either edits the test back to match the plan or learns that
expected output is decorative. Both are worse than saying nothing. State what must be
observable:

- ✅ "zero failures, and `DdxTextTest` appears in the run"
- ✅ "`[OK] Successfully migrated`, on dev and on test"
- ✅ "the failure is a missing class, not an assertion failure"
- ❌ "OK (4 tests, 7 assertions)"

Counts are welcome as evidence *after* a run, in the tracker. They are not a gate.

## Task structure

````markdown
### Task N: {deliverable}

**Effort:** low | standard | deep
**Files:**
- Create: `exact/path/to/file`
- Modify: `exact/path/to/existing:123-145`
- Test: `exact/path/to/test`

**Interfaces:**
- Consumes: the seams this task uses from earlier tasks — exact signatures
- Produces: the seams later tasks, tests or slices rely on — exact names, parameters,
  return shapes, failure behaviour. Seams only; internal names are the worker's.

**Requirements:** `REQ-...` ids this task satisfies (the spec's testable clauses)
**Design:** `node=<id> measured=<YYYY-MM-DD>` — required for every UI-bearing task
**Decisions:** the rulings this task must not re-litigate, each with its answer. Empty is the
normal state at `low` and `standard`; at `deep`, an open item names what the worker is to
settle and report — and it must be answerable **from the codebase**, by someone reading it.
Say what is already settled alongside it, so the open ground is bounded.

- [ ] **Step 1: Write the failing test** — the case table (the test code itself at `low`, or
      where the harness is the requirement)
- [ ] **Step 2: Run it, confirm it fails** — the command, and the shape of the failure
- [ ] **Step 3: Minimal implementation** — the code at `low`; at `standard` and `deep`, the
      deciding fragments and the existing pattern to follow
- [ ] **Step 4: Run it, confirm it passes** — the command, and the observable shape
- [ ] **Step 5: Full suite** — only when this task touches a global-effect artifact; paste
      the summary line as the evidence
- [ ] **Step 6: Commit** — `git add` the named paths only, then
      `git commit -m "..." -- <the same paths>`
````

Each step is one action of a few minutes. Every step says what must be true when it is done.

## Commit steps, always this shape

Stage the files this task touched, by name, and **scope the commit to the same pathspec**.
The git index is shared per repository across concurrent sessions: a bare `git commit -m`
commits the whole index, including another session's staged work. Never `git add -A`,
`git add .`, `git add *`, `git commit -a`.

## No placeholders

These are plan failures, not shorthand:

- "TBD", "TODO", "implement later", "fill in details"
- "add appropriate error handling", "add validation", "handle edge cases"
- "write tests for the above" with neither a case table nor test code
- "similar to Task N" — repeat it; tasks are read out of order and in isolation
- a step that says what to do without saying what must be true when it is done
- a reference to a type, function or route defined in no task
- an unresolved question parked in the plan ("open question", "to be decided", "decide
  later") — the plan is where questions get answered, and at freeze there are none left. A
  `deep` task's `Decisions` block is the one legal home for open ground, and it says what the
  worker settles and reports, not what nobody got to.

**Not a placeholder:** "implement to pass the cases; follow the pattern in `<existing file>`"
at `standard` or `deep` effort. The cases say what must be true and the named file says what
it must look like — that is an instruction, not a gap. The same sentence at `low` effort **is**
a placeholder: a typist has nothing to type.

## Self-review before freezing

Run this yourself — it is a checklist, not a dispatch:

1. **Spec coverage** — walk each spec section and point at the task that implements it. List
   what has no task, then add the tasks.
2. **Promise coverage** — every design leaf and requirement clause the slice promises is
   tasked, or explicitly deferred with a reason. (`/kerbe:coverage` pre-impl verifies this
   independently; do the pass anyway — it is cheaper to fix before the freeze.)
3. **Placeholder scan** — search the plan for every pattern above.
4. **Seam consistency** — names, signatures and property names used in later tasks match
   what earlier tasks **declare in Interfaces**. `clearLayers()` in Task 3 and
   `clearFullLayers()` in Task 7 is a bug already written down. Only seams can be checked
   this way, which is the second reason internal names stay out of Interfaces.
5. **Effort and code boundary** — every task carries an effort level; every `low` task
   carries its code in full; no `standard` or `deep` task carries a body that its cases and
   its named pattern already determine.
6. **Open decisions** — every `Decisions` block at `low` or `standard` is answered. A
   question left for the worker at those levels is an unanswered planning question wearing a
   task's clothes, and unattended runs cannot answer it. Settle it, or raise the task to
   `deep` and say what the worker is to settle and report.

   **`deep` is not a parking space.** An open item there must be answerable from the
   codebase by someone reading it — which repository owns this lookup, which of two existing
   patterns fits, where an existing value comes from. A question that needs a *human* to
   choose — scope, a product rule, a policy, a value nobody has decided — is a **spec gap**,
   and raising the effort level does not convert it into work. Send it back to the spec
   (`/kerbe:start`) and freeze the plan without that task, or freeze with the task's answer
   in hand. Escalating a product question to `deep` puts it in front of the one reader who
   cannot ask anyone: a worker at 3am.
7. **Command provenance** — every command quoted appears in the stack adapter's
   `commands.md`.

Fix inline and move on; no second review pass.
