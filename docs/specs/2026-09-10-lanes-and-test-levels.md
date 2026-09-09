# Parallel lanes and declared test levels — specification

> Decided 2026-09-10. Two changes that arrived as separate complaints and turned out to
> share a root: `PLAN.md` describes a slice's *shape* too coarsely for anything downstream
> to schedule it, and describes a task's *tests* not at all.

## The two defects

**1. Concurrency is a per-plan label, not a per-task fact.** `plan-spec.md` has the planner
emit one word for the whole plan — **chain** (workers run one at a time) or **group**
(workers run concurrently) — and `kerbe:implement` turns that word into one of two dispatch
modes. A plan is therefore fully serial or fully parallel. A plan where tasks 2 and 3 are
independent but 4→5→6 is a genuine chain has no way to say so, and gets scheduled as a
chain: the independent pair is serialised for nothing.

**2. The plan never says what level a test runs at.** `grep -n "Unit\|Functional\|TestCase"`
across `skills/plan/references/plan-spec.md` and `adapters/stack/symfony/commands.md`
returns nothing. Step 1 has the planner "name the test file and class and list the cases",
so the level is whatever filename the planner happens to type. The path of least resistance
is a functional test extending `WebTestCase`, because that base class can assert anything —
status code, HTML, database row — without the planner having to decide what the seam is.
Nothing in the skill pushes back.

The two are connected: level determines what infrastructure a task needs to verify itself,
and that is exactly what a scheduler needs to know before it can place the task.

## Measured evidence

Taken on the reference project's `subscription` slice workspace (`symfony/`), 2026-09-10,
in its `<test-container>`:

| Run | Tests | Time | Per test |
|---|---|---|---|
| `tests/Unit` (pure `TestCase`) | 300 | 0.390 s | 1.3 ms |
| `tests/Service/SubscriptionLifecycleTest` (`KernelTestCase`) | 30 | 2.389 s | 79.6 ms |
| `--testsuite 'Project Test Suite'` (the gate; `tests` minus `tests/Browser`) | 1779 | 347.2 s | 195 ms |

Decomposing that last row against the first:

| | Tests | Share of tests | Time | Share of runtime |
|---|---|---|---|---|
| pure unit | 300 | 16.9 % | 0.39 s | **0.11 %** |
| kernel / HTTP | 1479 | 83.1 % | 346.8 s | **99.89 %** |

Level composition in that slice's neighbourhood: 61 pure-unit methods against 513
kernel- or HTTP-bound ones. Repo-wide: 300 `Unit` methods, 178 `KernelTestCase`, 1286
`WebTestCase`.

**61× per test**, and a gate suite in which a sixth of the tests cost a thousandth of the
time. That is the shape of the opportunity. The honest reading of it is narrower than the
numbers suggest, and the spec is scoped to the honest reading — see the next section.

**Why this is the number that matters.** `kerbe:implement`'s per-task gate requires the full
suite whenever a task touches a global-effect artifact, and `adapters/stack/symfony/commands.md`
lists entities, migrations, service wiring, security config and shared fixtures among those.
On a slice of any substance that is most tasks. Every one of them pays 5 m 47 s.

## What is actually waste

Three reasons a test boots the kernel. Only the third is waste.

1. **The wiring is the claim.** `tests/Functional/ArticleBodySanitizerTest.php` boots the
   kernel to fetch `html_sanitizer.sanitizer.*` because the sanitizer's *configuration* is
   the requirement under test. Correct as written.
2. **The database is the claim.** Repository tests, schema tests, and the computed
   `isPremium` read that `SubscriptionLifecycleTest` flushes in order to observe. Correct as
   written — this is why that class cannot simply be moved wholesale, despite its own
   docblock calling `SubscriptionLifecycle` "a pure state machine".
3. **The kernel is booted only to reach a service that could have been constructed
   directly**, to assert pure logic. `tests/Functional/RevisionDiffHtmlPurifierTest.php`
   boots the kernel to `get(RevisionDiffService::class)` while `tests/Unit/RevisionDiffServiceTest.php`
   already tests the same class properly. Same subject, ~60× the cost, no additional claim.

### The rule

> **Boot the kernel only when the kernel is part of the claim.** If the test would pass with
> `new Thing(...)` and stubbed collaborators, it is a unit test. If what is asserted is the
> wiring, the mapping, the security configuration, the SQL, or the HTTP response, it needs
> the kernel and stays.

This rule cannot endanger an acceptance test, because acceptance tests assert precisely
categories 1 and 2 plus reachability. It only reclaims category 3.

**A note on expected yield.** Applying this to `SubscriptionLifecycleTest` moves about 6 of
30 methods (the `expectException(InvalidSubscriptionTransition::class)` guards, which throw
before touching the database) and saves roughly half a second. Per class the win is small.
The change is worth making because it is systemic and because it compounds at plan time,
not because any single class is expensive.

## Non-goal, stated so it is not re-argued

An earlier draft justified the unit-test push on the grounds that unit tests need no
container and therefore fan out freely. **That argument is withdrawn.** The operator is
willing to run 3–4 Docker environments per slice, so lane scarcity is not the binding
constraint and must not be used to justify test-level decisions. The unit push stands on
speed and failure precision alone. Levels still inform scheduling (below), but scheduling
never justifies a level.

---

## Design

### 1. Lanes

A **lane** is an isolated verification environment: a git worktree plus whatever the project
needs to run its tests against it (container, port, test database). Lane 0 is the slice
workspace that `kerbe:implement` Step 0 already resolves. Lanes 1..N-1 are additional.

`kerbe.yml` gains, under `workspace`:

| Key | Type | Default | Meaning |
|---|---|---|---|
| `lanes` | int | `1` | How many isolated verification environments this project can run for one slice. |
| `lane_setup_cmds` | list of strings | unset | Run once when a lane is created — containers, database, seed data. `{lane}` interpolates the lane index; `{slice}` interpolates as it already does elsewhere. |
| `lane_teardown_cmds` | list of strings | unset | Run when the slice's run ends. |
| `worktree_setup_cmds` | list of strings | unset | Run once in **every** fresh worktree, lane-bound or not — the language's dependency install (`composer install`, `dart pub get`). Distinct from `lane_setup_cmds` because a lane-free worker needs this and nothing else. |

**`worktree_setup_cmds` is not optional in practice and is easy to miss.** A fresh git
worktree contains source and no `vendor/`, so even a pure-unit worker cannot run
`php vendor/bin/phpunit` in it until dependencies are installed. Omitting this key while
running lane-free workers produces exactly the failure mode this design is meant to prevent:
a worker that edits files and verifies nothing. If a project declares no
`worktree_setup_cmds`, `kerbe:implement` runs every task in lane 0 and says why.

`stack.exec` gains `{lane}` alongside its existing `{slice}`, so a command can be routed to
the right environment:

```yaml
stack:
  exec: "docker exec -w /var/www/html/symfony <project>-{slice}-l{lane}-web-test-1 {cmd}"
```

**kerbe does not do port arithmetic.** Port, container name and database name are entirely
the project's business, expressed in its own `lane_setup_cmds` template. kerbe supplies
`{lane}` and nothing else. This keeps the lane model portable to stacks that need no
containers at all.

Lane 0 is never torn down by this mechanism — it is the workspace, and Step 0 owns it.

**Precondition, checked before dispatch.** With `lanes > 1`, `stack.exec` must contain
`{lane}`. Otherwise every lane would route its commands to the same environment, which is
the failure this whole design exists to prevent: workers that can edit files and verify
nothing. Missing `{lane}` with `lanes > 1` is a hard stop naming the config key to fix.

### 2. Per-task dependencies

`plan-spec.md`'s task structure gains one line, beside `**Effort:**`:

```
**Depends:** none | 2, 3
```

Task numbers only, referring to tasks in the same plan.

`kerbe:implement` does not trust it alone. It **independently derives** edges from material
the plan already carries:

- task B depends on A if B's `Interfaces: Consumes` names anything in A's `Interfaces: Produces`
- task B depends on A if B's `Files: Modify` names anything in A's `Files: Create`

The graph used for scheduling is the **union** of declared and derived edges — the safe
direction, since a missing edge causes a race and a spurious edge only costs serialisation.
Any disagreement between the two sets is recorded as a Ruling naming the task and the edge,
because it is a plan defect worth reading: a derived-but-not-declared edge means the planner
missed a dependency; a declared-but-not-derived edge is either an ordering constraint with
no named seam (legitimate, and the plan should say why) or over-serialisation out of caution.

A cycle is a hard stop, not a Ruling. It means the plan's tasks are not independently
deliverable and the plan needs re-cutting.

### 3. Scheduling: a ready queue, not waves

The obvious model is waves — compute every task whose dependencies are satisfied, run them
all, barrier, repeat. **Do not implement that.** A barrier makes every task in a wave wait
for the slowest one, which is the same class of waste this spec exists to remove.

The scheduler is a greedy ready queue:

1. Build the dependency graph (union, above). Hard stop on a cycle.
2. `ready` = tasks whose dependencies are all complete and which have not started.
3. Partition `ready` by lane requirement (§4): lane-free tasks and lane-bound tasks.
4. Dispatch every lane-free ready task concurrently, each in its own worktree, no lane —
   but only where `worktree_setup_cmds` is declared. Undeclared, a lane-free task is treated
   as lane-bound, because a worktree without dependencies installed cannot verify itself.
5. Dispatch lane-bound ready tasks up to the number of free lanes.
6. When any worker completes and its gate passes, recompute `ready` and refill immediately —
   do not wait for its siblings.

**The file-ownership contract survives unchanged**, but now applies to the concurrently
running set rather than to a statically declared group: no two tasks running at the same
time may own the same file. A template and the styles and controller serving it belong to
one task. End-to-end browser tests come last, after the features they exercise work. Where
two ready tasks would overlap on a file, the scheduler holds one back — an ordering
constraint the graph did not capture, recorded as a Ruling.

### 4. Declared test levels

The case table in Step 1 gains a leading **Level** column:

```markdown
| Level | Precondition | Expectation | @req |
|---|---|---|---|
| unit | status = cancelled | `reactivate()` throws `InvalidSubscriptionTransition` | REQ-SUB-LIFE-004 |
| unit | active, `cancelAt` set | `reactivate()` clears `cancelAt`, status unchanged | REQ-SUB-LIFE-004 |
| http | POST `/account/reactivate` as a member | 302, and `cancelAt` cleared | REQ-SUB-LIFE-004 |
```

Levels, stack-neutral in the plan and mapped by the stack adapter:

| Level | Means | Symfony mapping |
|---|---|---|
| `unit` | subject constructed directly, collaborators stubbed, no framework | `extends TestCase` |
| `kernel` | needs DI wiring, configuration, or the database — but not HTTP | `extends KernelTestCase` |
| `http` | needs a request through the framework | `extends WebTestCase` |
| `browser` | needs a real browser (client-side behaviour) | Panther |

A **task's lane requirement** falls out: a task all of whose cases are `unit` is lane-free
and schedules against the dependency graph alone; any other task needs a lane.

Deciding per case rather than per task is the point. It is what forces a planner to justify
each case that reaches for a kernel, and it lets one task honestly carry twelve unit cases
and one HTTP case — which is the shape most tasks should have and none currently declare.

### 5. The acceptance-test floor

The clause that makes the unit push safe. Three promise classes **must** carry at least one
`http` case, and a planner may not discharge them with unit cases. They are taken from
`docs/validation/2026-08-20-subscription-comparison.md`, because they are the classes whose
absence produced real missed blockers:

1. **Audience reachability** — a promised route must be reachable by the promised audience.
   Asserted through the security configuration, which only a request exercises.
2. **Action chain** — a promised CTA must reach a route that exists and acts on the promised
   object. One hop, followed for real.
3. **State transition observable through HTTP** — where the promise is that a user can reach
   a state, the transition's precondition must be shown producible through the interface,
   not merely that a method with the right name exists.

A fourth floor, `browser`, applies where the claim is inherently client-side (a payment
element mounting, a dropdown opening). It is not covered by the three above and is not
satisfiable at any lower level.

These floors are judgment calls, so they are gate-read rather than script-checked (§7).

### 6. Enforcement at the per-task gate

`kerbe:implement`'s Step 5 gate already reads the worker's diff. It additionally compares the
**declared level against the base class the worker actually used**. Declared `unit`, wrote
`WebTestCase` ⇒ a deviation, reported rather than absorbed — same treatment as a changed case
value. The reverse (declared `http`, wrote `TestCase`) is the more serious direction, because
it silently drops an acceptance floor.

### 7. Gates

`fixtures/check_plan.py` gains, per task:

- `**Depends:**` present, and its value parses as `none` or a comma-separated task-number list
- every task number referenced by `Depends` exists in the plan
- the declared graph is acyclic
- every case table carries a `Level` column, and every level is one of the four values

`fixtures/ACCEPTANCE.md`:

- **plan gate** gains a read step: the acceptance floors of §5 are honoured, and no task
  declares `unit` for a case whose expectation names a route, a status code, a role, or a
  rendered element. Judgment, not script.
- **implement gate** step 2's dry run must now report the **ready queue and lane assignment**
  with the graph evidence for it, replacing "the execution shape (chain vs group)".
- both fixtures (`symfony-mini`, `flutter-mini`) grow a plan with a genuine diamond — two
  independent tasks between a common ancestor and a common descendant — so that a scheduler
  that still serialises everything fails the gate visibly.

### 8. Back-compatibility

`lanes` defaults to `1`, `worktree_setup_cmds` defaults to unset, and a plan with no
`**Depends:**` lines derives its graph from `Interfaces` and `Files` alone.

An existing project that upgrades and changes no config therefore gets: one lane, no
`worktree_setup_cmds`, and so **every task in lane 0, one at a time** — today's chain
behaviour. It does *not* silently start fanning lane-free tasks out into worktrees, because
without `worktree_setup_cmds` those worktrees could not verify anything. Opting in is two
keys, and the ordering matters: `worktree_setup_cmds` alone buys concurrency for unit-only
tasks; `lanes` buys it for the rest.

The chain/group vocabulary is removed from
`plan-spec.md` rather than deprecated: leaving both would let a plan declare a shape that
contradicts its own graph.

## Out of scope

- **Retrofitting existing tests.** This spec changes how new plans are written. Moving
  `RevisionDiffHtmlPurifierTest` and its cohort is separate work, and should be justified by
  measurement on its own terms.
- **Cross-slice parallelism.** Lanes belong to one slice's run.
- **Recall.** The missed blockers in the 2026-08-20 validation were single-hop verification
  failures at every level, not a consequence of the unit/acceptance ratio — the cancel →
  reactivate round trip is tested at `SubscriptionLifecycleTest.php:520` and passes. Nothing
  in this spec improves coverage recall, and it must not be presented as if it does.

## Files this touches

| File | Change |
|---|---|
| `skills/coverage/references/config.md` | `workspace.lanes`, `lane_setup_cmds`, `lane_teardown_cmds`, `{lane}` in `stack.exec` |
| `skills/plan/references/plan-spec.md` | `**Depends:**`, the Level column, the kernel rule, the acceptance floors; remove chain/group |
| `skills/plan/SKILL.md` | Step 3 and the Rules list follow the spec above |
| `skills/implement/SKILL.md` | Step 3 becomes the ready queue; Step 5 gains the level check; Step 6 integrates per-worktree branches |
| `adapters/executor/claude.md` | lane-aware dispatch; `{lane}` routing; the `lanes > 1` precondition |
| `adapters/stack/symfony/commands.md` | a "which level" section beside "which suite is the gate" |
| `adapters/stack/flutter/commands.md` | the same level mapping for Dart |
| `fixtures/check_plan.py` | the four structural checks of §7 |
| `fixtures/ACCEPTANCE.md` | plan-gate read step; implement-gate wording; diamond fixtures |

`~/.claude/skills/sdlc-implementation-plan/` is the superseded wrapper over
`superpowers:writing-plans` and is left alone.
