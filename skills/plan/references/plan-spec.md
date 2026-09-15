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

Order tasks by dependency, and **declare each task's dependencies on its own `**Depends:**`
line** — `none`, or the task numbers it consumes. `/kerbe:implement` builds a graph from
these and schedules everything the graph leaves free to run at once, so the declaration is
what decides whether two independent tasks are actually built in parallel.

There is no per-plan "chain" or "group" label any more, and there must not be one: a single
word for a whole plan cannot say that tasks 2 and 3 are independent while 4→5→6 is a genuine
chain, so it serialises the pair for nothing.

**Declare every real dependency, including the ones the derivation would find anyway.**
`/kerbe:implement` also derives edges independently — from `Interfaces` (one task's
`Consumes` naming another's `Produces`) and from `Files` (one task modifying what another
creates) — and schedules on the **union** of declared and derived. That derivation is a
**cross-check, not a division of labour**: it is only worth running if both sides are
independently complete, and a reader of the frozen plan should be able to see the graph
without simulating the derivation in their head. So a task that consumes an earlier task's
seam names it in `Depends` even though `Interfaces` already implies it.

What `Depends` adds beyond the derivation is the edge no field can express — a real ordering
constraint with no named seam and no shared file (a migration that must land before a test
touching the schema). Say those where they are not obvious, because they are the ones a
reviewer cannot check against anything else. Put the justification in a line **beneath** the
field, never on it: `**Depends:**` carries the value and nothing else, and a trailing comment
on that line is a structural failure.

**Two tasks that both modify a file neither creates are not a dependency.** This is the
common case — two tasks adding to one existing template — and it has no direction, so it is
not a `Depends` edge and inventing one is over-serialisation. It is a **mutual exclusion**:
they may not run at the same time. `/kerbe:implement` resolves that with the file-ownership
contract, holding one back and recording a Ruling. Your job is to make it visible: name the
exact file in both tasks' `Files: Modify` so the collision is derivable from the plan rather
than discovered by a worker's merge.

Declare what is real, not what feels safe: over-declaring costs concurrency, and
under-declaring costs a race that the union usually, but not always, catches.

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

**Each Produces entry names its consumer** — `→ Task 7`, `→ case 4`, `→ <later slice>`,
`→ route table`. An entry with no consumer to name is internal by definition and comes out.
This is also what `/kerbe:coverage` reads: only a Produces entry with a consumer, and a case
citing a requirement, become ledger rows; the rest of the task is approach the worker and
the review may revise.

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

So Step 1 names the test file and class and lists the cases as a table: **level**, input or
precondition, expectation, and the `@req` it discharges. Write the test code in full only
where the harness **is** the requirement (a security boundary, a cross-tenant assertion, a
serialisation contract), and at `low` effort, which gets everything in full.

### The Level column — decided per case, not per file

| Level | Means | Symfony | Flutter |
|---|---|---|---|
| `unit` | subject constructed directly, collaborators stubbed, no framework | `extends TestCase` | plain `test()` |
| `kernel` | needs DI wiring, configuration, or the database — but not HTTP | `extends KernelTestCase` | needs bindings//DB |
| `http` | needs a request through the framework | `extends WebTestCase` | widget + router |
| `browser` | needs a real browser (client-side behaviour) | Panther | integration_test |

**The rule: boot the framework only when the framework is part of the claim.** If the case
would pass with the subject constructed directly and its collaborators stubbed, it is `unit`.
If what is asserted is the wiring, the mapping, the security configuration, the SQL, or the
HTTP response, it needs the framework and stays.

Level is chosen **per case**, which is the point: one task honestly carries twelve `unit`
cases and one `http` case, and that is the shape most tasks should have. A whole table set
to `http` because the base class can assert anything is the default this column exists to
stop — on a real slice that habit produced a gate suite where a sixth of the tests cost a
thousandth of the runtime, and every task touching a global-effect artifact paid the rest.

### The acceptance floor — three promise classes that `unit` cannot discharge

A planner may not satisfy these with `unit` cases. Each needs at least one `http` case,
because each is a claim about something only a real request exercises:

1. **Audience reachability** — a promised route is reachable by the promised audience.
   The assertion is against the security configuration, not the controller.
2. **Action chain** — a promised CTA reaches a route that exists and acts on the promised
   object. Followed one hop, for real.
3. **State transition observable through HTTP** — where the promise is that a user can reach
   a state, the transition's precondition is shown producible *through the interface*. That a
   method with the right name exists is not the promise.

A fourth floor: a claim that is inherently client-side needs a `browser` case and is not
satisfiable at any lower level. The obvious members are behavioural — a payment element
mounting, a dropdown opening — but **a styling claim belongs here too**, and it is the one
that gets missed. "The card lifts on hover" is not discharged by an `http` case asserting
`.card-hover` appears in the markup: the class name is present whether or not the stylesheet
defining it is ever imported into the bundle, so that case passes with the rule dead. If the
promise is that the user *sees* something, the case has to observe the computed result, not
the hook it hangs on.

**The floors are cumulative, not a classification.** One element routinely lands in two
classes, and each class keeps its own case — a "share by email" control that opens a popup
*and* posts to a route is a client-side claim (floor 4 ⇒ a `browser` case for the popup
opening) *and* an action chain (floor 2 ⇒ an `http` case for the send reaching a route that
acts on the card). Two promises, two cases. Picking the higher level and calling one case
sufficient is the mistake: `browser` does not subsume `http`, because a browser case that
drives the UI proves the popup opened, not that the route it posts to exists and is
reachable by that audience.

These floors are why pushing cases down to `unit` is safe. They are the cases that catch the
defects nothing else catches, and they stay.

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
**Depends:** none | 2, 3
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
**Decisions:** the rulings this task must not re-litigate, **each citing where it was
decided** — a `DECISIONS.md` id, a `REQ-` id, or a dated spec-doc clause. The planner does
not mint decisions: a choice that no doc records and that a human could reasonably make
differently (a policy, a limit, a boundary, a format) is a spec gap — send it back to the
specification step (a grilling round, or `/kerbe:start`) and freeze with the answer in
hand, or write it as `worker's call` and let the worker choose. Empty is the normal state
at `low` and `standard`; at `deep`, an open item names what the worker is to settle and
report — and it must be answerable **from the codebase**, by someone reading it. Say what
is already settled alongside it, so the open ground is bounded.

- [ ] **Step 1: Write the failing test** — the case table, `Level` column first (the test
      code itself at `low`, or where the harness is the requirement)
- [ ] **Step 2: Run it, confirm it fails** — the command, and the shape of the failure
- [ ] **Step 3: Minimal implementation** — the code at `low`; at `standard` and `deep`, the
      existing pattern to follow (a file path) and, only where the seam rule's test says two
      competent workers would diverge, the two or three deciding lines — never a fenced block
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
- a case table with no `Level` column, or `**Depends:**` omitted — both are read by the
  scheduler, and a missing one is not a default, it is a task that cannot be placed
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
   its named pattern already determine. Mechanically: a fenced code block inside a
   `standard` or `deep` task fails the freeze; a `Produces` entry without a named consumer
   fails the freeze.
5a. **Decision provenance** — every line in every `Decisions` block cites a `DECISIONS.md`
   id, a `REQ-` id or a dated spec clause, or reads `worker's call`. A ruling with no
   citation is one the planner made up; it goes back to the specification step before
   the freeze, because once frozen it will be read as if a human had decided it.
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
8. **Dependency graph** — every task carries `**Depends:**`; every number names a task that
   exists; there is no cycle. Then read it for *over*-declaration: a dependency that is not
   a consumed seam and not a shared file is serialisation you are paying for, so either
   justify it in a line or drop it.
9. **Levels** — every case carries a level, and every case that reaches for `kernel`, `http`
   or `browser` needs what that level provides. Walk the `http` cases against the acceptance
   floor in both directions: a floor promise with no `http` case is a hole, and an `http`
   case that asserts nothing about wiring, audience or a real request is a `unit` case
   wearing an expensive harness.

Fix inline and move on; no second review pass.
