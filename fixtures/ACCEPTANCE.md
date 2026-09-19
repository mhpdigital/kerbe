# Coverage fixtures — the acceptance gate

Any change to `skills/coverage/` (SKILL.md, references, scripts) or `adapters/` must pass
this gate **before** it is used on a real project. The fixtures are the skill's regression
tests: planted, known gaps plus planted decoys.

## Procedure (per fixture: `symfony-mini`, `flutter-mini`)

1. Copy the fixture to a scratch directory (produced files must never dirty the repo copy).
2. Dispatch a **fresh subagent** whose prompt is: read `<repo>/skills/coverage/SKILL.md`
   and execute it end-to-end in **audit** mode on the fixture's slice (`cards` / `gallery`)
   with the scratch copy as the target project root, writing `PROMISES.md` and
   `OUT_OF_SCOPE.md` into the slice folder. The agent may run the extraction and
   verification passes inline (sequentially) when it cannot dispatch its own subagents —
   the gate tests the procedure's output, not its parallelism.
3. Score the output:
   ```bash
   python3 fixtures/score.py fixtures/<fixture>/EXPECTED.json <scratch>/planning/slices/<slice>/PROMISES.md
   python3 skills/coverage/scripts/verdict.py <scratch>/planning/slices/<slice>/PROMISES.md
   ```
4. **Determinism:** run step 2–3 a second time from a fresh scratch copy. The **gap
   portion** of the two verdict blocks must be identical: the same hop-break counts
   (`GAP` / `partial` / `absent` / `unverified`) and the same set of open findings. The
   total `promises` count may differ between independent extractions (agents mint
   `present` rows at slightly different leaf granularity — observed 10 vs 8 on
   symfony-mini with identical gap findings). That looseness is acceptable because in
   production extraction runs **once** and the frozen, committed ledger is the
   denominator; re-verification always reuses it, so granularity variance never enters a
   real run. If the *gap* portion ever differs between runs, the skill wording is not
   binding — fix it.

**Pass = every `require` PASS, every `forbid` PASS on both runs, gap portion identical
across the two runs.**
A failure means the skill/adapter wording is not binding — fix it and rerun; that is the
harness doing its job. Never debug skill changes on a live project.

`GOLDEN.md` in each fixture is a hand-authored correct ledger: it must always score clean
(`score.py` exit 0) and is the reference for how rows should be written.

## kerbe:start gate

Any change to `skills/start/` or the adapter template sets reruns this before real use:

1. Copy `symfony-mini` to a scratch dir. Dispatch a fresh subagent: read
   `<repo>/skills/start/SKILL.md` and execute it on the scratch copy for a NEW slice id
   (e.g. `orders`), telling it "the user has answered design_required: true — reason:
   design-driven, frame exists" (subagents cannot use AskUserQuestion; the pre-supplied
   answer stands in for it and must land verbatim in the SETTINGS Notes row).
2. Score: `python3 fixtures/check_start.py <scratch> orders true` — exit 0 required.
3. Repeat with `design_required: false` (fresh scratch, e.g. slice `cleanup`, reason "no
   UI at all") and score with `false SECURITY.md,DONE_CRITERIA.md` — the optional fourth
   arg names the stack docs the slice's tailoring should produce (an infra slice omits
   ENTITIES/ROUTES); docs outside the named set must not exist.
4. Also confirm the run refused nothing it should create and created nothing it should
   omit beyond what check_start covers (read the agent's report).

## kerbe:figma gate

Any change to `skills/figma/` reruns before real use:

1. `python3 -m unittest tests.test_figma_scripts` — token resolution, URL parsing, and
   offline extraction against the symfony-mini snapshot (every leaf listed with node ids,
   palette/font summaries present, unknown page errors with the page list).
2. Live operations (`grade`, `fetch`, API extraction) cannot run against fixtures — they
   are validated on the next real slice run and the result recorded below. That gap is
   stated, not hidden.

## claude-design adapter gate

Any change to `adapters/design/claude-design.md` or `skills/coverage/scripts/dc_extract.py`
reruns before real use:

1. `python3 -m unittest tests.test_dc_extract` — leaf enumeration with `id` as node id,
   `sc-if`/`sc-for` branch recording, helmet/script exclusion, lint (id-less interactive
   leaf, duplicate id across artboards), dirty-tree refusal, git pin in the manifest.
2. The artifact round-trip (`seed-canvas.mjs --extract` back into the design dir, ids
   surviving a GUI save) cannot run against fixtures — validated on the next real slice
   and recorded below. That gap is stated, not hidden.

## kerbe:plan gate

Any change to `skills/plan/` (SKILL.md or `references/plan-spec.md`) reruns this before
real use:

1. `python3 -m unittest tests.test_check_plan tests.test_portability` — structural checker
   and the portability invariants (no harness mechanism in a skill body, no hardcoded
   project path).
2. Copy `symfony-mini` to a scratch dir and **delete the slice's `PLAN.md` in the scratch
   copy** — the fixture's plan is a coverage stub, and leaving it in place resolves the run
   to remediation mode before the design gate is ever reached, which tests a different
   thing. The fixture slice deliberately ships **no** `SETTINGS.md`: dispatch a fresh
   subagent to read `<repo>/skills/plan/SKILL.md` and run it on the scratch slice `cards`. It
   must **STOP at the design gate** and say the slice never answered the design question. A
   run that proceeds — or defaults `design_required` to false — is a gate failure, and the
   wording needs fixing.
3. In the scratch copy only, write `SETTINGS.md` with `design_required: true` and a dated
   Notes reason, and re-dispatch. It must now demand the Design-sources block, find it
   populated in `UI_ELEMENTS.md`, and write `planning/slices/cards/PLAN.md` (overwriting the
   fixture's plan in the scratch copy is expected — this is a plan-authoring run, not a
   coverage run).
4. Score: `python3 fixtures/check_plan.py <scratch>/planning/slices/cards/PLAN.md true` —
   exit 0 required.
5. Read the report: the plan's Global Constraints must quote the stack adapter's
   `commands.md` full-suite trigger, and every UI task must carry `node=… measured=…`.
6. **Read the code boundary** — the part `check_plan.py` cannot judge. Every task carries an
   effort level; a `standard` or `deep` task states seams and cases and does **not** paste
   implementation bodies the cases and the named pattern already determine; a `low` task
   carries its code in full. Interfaces list only what another task, a specified test or a
   later slice consumes — an internal helper or a locally-caught exception class in an
   Interfaces block is a fail. No task leaves a decision open at `standard` or `low`.
7. **Read the graph and the levels** — also beyond what the script can judge.
   `check_plan.py` proves `**Depends:**` parses, names real tasks and has no cycle; it cannot
   tell whether the edges are *true*. A dependency that is neither a consumed seam nor a
   shared file is serialisation the plan is paying for — a plan whose every task depends on
   its predecessor, on a slice with genuinely independent work, is a fail even though it
   scores clean.
   Then the levels, in both directions:
   - a case whose expectation names a **route, status code, role, or rendered element** but is
     declared `unit` is a fail — that is an acceptance floor being discharged on the cheap
   - a case that asserts pure logic (a guard, a transition allow-list, a normaliser) but is
     declared `kernel` or `http` is a fail — the expensive default this column exists to stop
   - each of the three floor classes present in the slice (audience reachability, action
     chain, HTTP-observable state transition) has at least one `http` case, and an inherently
     client-side claim has a `browser` case

## kerbe:implement gate

Any change to `skills/implement/` reruns this before real use. Implementation itself cannot
run against a fixture (it needs a real toolchain and a real git workspace), so the gate
covers the two things that are checkable offline and the rest is stated as a gap:

1. `python3 -m unittest tests.test_check_progress tests.test_portability`.
2. **Tracker derivation, dry run.** Copy `symfony-mini` to a scratch dir and dispatch a
   fresh subagent: read `<repo>/skills/implement/SKILL.md`, execute Steps 0–3 **only**
   (resolve the workspace, derive the tracker, build the schedule) against the scratch copy
   with `workspace.root` unset, and dispatch nothing. Score:
   `python3 fixtures/check_progress.py <scratch>/claude-progress.md <scratch>/planning/slices/cards/PLAN.md`
   — exit 0 required.

   Then read the report for the schedule, which the script cannot score. It must name the
   **ready queue** and the **lane assignment**, with the graph as its evidence. The fixture
   plan carries a free pair (T3 and T5, disjoint files), a **file-collision trap** (T4 is free
   in the graph the moment T2 lands, but owns T3's template), and a lane-free task (T5, all
   `unit` cases).

   **Read the graph verdict and the dispatch verdict as two separate answers.** The fixture's
   `kerbe.yml` has no `workspace:` block at all, so `lanes` defaults to 1 and
   `worktree_setup_cmds` is unset — this project can host **no** concurrency. A correct report
   therefore says both things at once: *the graph frees T3 and T5 to run together, and this
   config cannot, so they run in lane 0 one after the other.* Marking the serial dispatch a
   failure would fail a correct schedule; so would accepting a report that never noticed the
   pair was free.

   Four failures to watch for, each of which scores clean:
   - **T3 and T5 never identified as independent** — the graph was read as a chain, which is
     the whole defect the per-task `Depends:` line replaced. This is about what the report
     *says about the graph*, not about what it dispatches
   - **concurrency actually promised on this config** — `lanes` 1 and no `worktree_setup_cmds`
     means lane 0, serially, including for the lane-free T5. A report that proposes fan-out
     here has read the graph and ignored the environment
   - **T3 and T4 dispatched together** — the graph says both are free; only reading the files
     they own stops it. This is the check that the file-ownership contract is applied against
     the codebase and not against the plan's own claim about itself
   - **T4 held back with no Ruling recorded** — right move, no stated reason. The hold is an
     ordering constraint the graph did not capture, and an unrecorded one is invisible to the
     next reader

   Note that the fixture's `PLAN.md` is a checkbox stub with no `Interfaces`/`Files` blocks,
   so the **derived** half of Step 3a has nothing to read. A run that says so and degrades to
   declared-only is correct; a run that claims it derived and cross-checked edges it could not
   have is a fail.
3. **The per-task gate is the part that matters most and cannot be fixture-tested.** It is
   validated on the first real slice run: a task touching a global-effect artifact must be
   refused as done until the full-suite output is pasted. Record the result below.
4. **Effort provenance and the deviation protocol**, also first-real-run: every dispatch's
   effort level matches its task's `**Effort:**` line rather than the dispatcher's judgment,
   every brief carries the deviation protocol verbatim, and a task whose plan text did not
   match the codebase produces a *plan said / found / did* entry in the tracker's Deviations
   section rather than a silent conformance. An unattended run with a green suite and an
   empty Deviations section on a plan written before the code existed is the failure this
   gate is looking for.
5. **Level provenance**, first-real-run: the gate compares each task's declared case levels
   against the base classes in the diff. The failure to hunt for is a planned `http` case
   written as a `unit` test — it drops an acceptance floor, and the suite stays green while
   the promise stops being checked, so no other check in this gate can see it.
6. **Lane routing**, first-real-run and only where `workspace.lanes > 1`: each concurrent
   worker's pasted command output shows the lane's own environment, not lane 0's. Two
   workers whose evidence cites the same container are two workers that raced on one
   database, and their green runs mean nothing.

## kerbe:bug gate

1. `python3 -m unittest tests.test_portability` — every stack adapter's `impact.md` covers
   every artifact kind (recipe or explicit n/a).
2. The impact analysis itself is validated on the first real bug: the run must produce the
   check table **before** any fix diff, and the commit must be pathspec-scoped with a
   root-cause message. Record the result below. This gap is stated, not hidden — the same
   standing as `kerbe:figma`'s live operations.

## kerbe:review gate

Any change to `skills/review/` or the `risk-tiers.md` adapters reruns before real use:

1. `python3 -m unittest tests.test_check_review tests.test_portability` — QR structure
   checker, and parity (both stacks ship `risk-tiers.md` defining all three tiers with the
   tier-3 exemption bound to a full-suite run).
2. **Fixture run.** Copy `symfony-mini` to a scratch dir, `git init` it, commit the tree
   as the base, then apply a small planted change set (edit `CardController.php` — add a
   condition to `detail()`; edit `_card.scss`; add a route link in `index.html.twig`).
   Dispatch a fresh subagent: read `<repo>/skills/review/SKILL.md`, review the diff
   against the base commit on the scratch slice `cards`. Score:
   `python3 fixtures/check_review.py <scratch>/planning/slices/cards/REVIEW.md <comma-separated changed files>`
   — exit 0 required. Read the report: the controller edit must be tier 1 with line
   references, the SCSS tier 3, and the QR must note an adversarial pass ran.
3. The judgment half — mis-tiering, spec-deviation findings, severity — cannot be
   structurally checked; it is validated on the first real slice review and recorded
   below. Stated, not hidden.

## kerbe:rwalk gate

Any change to `skills/rwalk/` reruns before real use:

1. `python3 -m unittest tests.test_check_review` — the ID column the walk resumes on is
   part of the QR's recorded structure, so the checker owns it: every business-logic and
   glue row carries a `B<n>`/`G<n>` id, ids are unique, and a row struck by a walk still
   passes (the id cell stays unstruck and addressable).
2. **Turn-discipline run**, on a real REVIEW.md with open rows. The walk must:
   resolve and announce its position before the first turn; present **one** item and stop;
   never mark a row the human did not answer on; write the row's edit at the moment it
   resolves, not at the end; and leave application code untouched. Any of these failing is
   a gate failure — they are the whole skill. Stop the run after three items and inspect
   the file: three rows struck in place with an unstruck bold status and a mechanism
   sentence, every other row byte-identical.
3. **Resume**, immediately after: a second invocation with no arguments must land on the
   fourth row without being told where it was. Resume is derived from the rows themselves,
   so a run that needs a pointer file has already failed this.
4. The judgment half — whether a pre-verdict is worth reading, whether a verdict's
   mechanism sentence would survive the reviewer forgetting — is validated on the first
   real walk and recorded below. Stated, not hidden.

## kerbe:grill gate

Any change to `skills/grill/` reruns before real use:

1. **Brief assembly, inspected before any round runs.** Invoke on a fixture slice and stop at
   the assembled brief. All seven parts present and in order; every document referenced by
   **path**, with zero document contents pasted; each of the slice's own docs annotated with
   its authority; parent material scoped to an ID range rather than a whole file; the
   fact/decision split stated. A brief that names a file the slice does not have, or omits one
   it does, is a gate failure — the brief is the skill.
2. **Fact/decision discipline**, over one real round. Every question put to the user must be
   one no amount of reading could answer. Take the round's questions and try to answer each
   from the planning docs and the code root alone: any that yields to a `grep` should have
   been dispatched to a sub-agent, not asked.
3. **Deferred recording.** Mid-campaign, `DECISIONS.md` must not exist or must be unchanged;
   only `GRILLING_STATE.md` moves. A skill that writes decisions as they are made produces a
   file that contradicts itself once a later round reshapes an earlier answer.
4. **Resume across the context wall.** Kill the session mid-campaign and re-invoke. It must
   rebuild the frontier from `GRILLING_STATE.md` and continue at the right round without being
   told where it was — this is the failure that ended the one real campaign twice, so it is
   not optional.
5. **Recording shape**, on completion: provenance header with the date; sections by topic
   citing question ids; every bullet carrying the ruling **and** its reasoning; known limits
   marked; propagation notes naming their target doc — and each of those followed into that
   doc. `GRILLING_STATE.md` deleted, `TIMING.md` row 3 stamped.
6. **Post-freeze amendment**, on a fixture slice that already carries a `PLAN.md`: run a
   campaign whose decisions include one that adds a deliverable and one that supersedes an
   existing task. The run must append a **dated amendment section to that same `PLAN.md`**,
   cite the question ids, add the new work as tasks numbered on from the last with `Files`,
   `Effort`, `Interfaces`, `Depends` and a case table with levels, and name the superseded
   task **without editing its body** — diff the pre-run file and every frozen task must be
   byte-identical. `python3 fixtures/check_plan.py <the amended PLAN.md>` must print
   `ALL PASS`. Writing a `FIX_PLAN.md`, a second plan file, or leaving the plan untouched is
   a gate failure: routing decisions away from the plan they change is the failure this step
   exists to catch.
7. The judgment half — whether the rounds reached the altitude that matters, whether a
   decision record still reads as a decision in three weeks, whether an amendment reads as
   an instruction to a worker who never saw the rounds — is validated on the first real
   campaign and recorded below. Stated, not hidden.

## Recorded runs

| Date | Fixture | Model | Result |
|---|---|---|---|
| 2026-09-17 | rwalk gate (new skill) + review gate, deterministic half | opus | **PARTIAL — deterministic half PASS, both behavioural halves outstanding and stated.** 88 unit tests green, `test_check_review` extended from 7 to 11 cases for the ID column the walk resumes on (missing id per tier, reused id, and a walked row still passing with its id cell unstruck). The `skills/review/` change is confined to Step 4's output shape (ID column, F-ids on flags) and the `rwalk` handoff sentence — no classification or tiering rule moved — but the review gate's **fixture run (step 2) has not been rerun**, and the rwalk gate's **turn-discipline and resume runs (steps 2–3) have not been run at all**: both need a live walk against a real REVIEW.md, which is the first real use. Recorded as outstanding rather than assumed: the structural checker cannot see whether the skill stops after one item, and that is the whole skill. |
| 2026-09-10 | plan + implement gates: symfony-mini scratch × 5 (stop, authoring ×2, schedule ×2) | sonnet | **PASS on the second pass — the lanes / dependency-graph / case-level change (0.6.x).** Stop run passed first time (halted on the missing `SETTINGS.md`, refused to infer `design_required` from the populated `UI_ELEMENTS.md` beside it). The other two failed first and found **four defects, three of them in the change itself**: (1) the fixture's advertised diamond was fictional — T3/T4 both render onto `detail.html.twig`, so the gate text would have **failed a correct schedule** that held T4 back; (2) file ownership was resolved from the plan's claim about itself rather than the codebase — now bound to the codebase, since `Depends` says what a task *consumes*, never what it *writes*; (3) `UI_ELEMENTS.md` carried node ids but no `measured=` dates, blocking the design gate — **pre-existing**, and since the 2026-09-09 row above records this same gate passing, whether it stops has depended on how strictly the agent read the requirement; (4) two ambiguities raised unprompted — whether a seam dependency is *also* declared in `Depends` (yes: derivation is a cross-check, not a division of labour) and how to handle one element in two acceptance-floor classes (cumulative: `browser` does not subsume `http`). Second pass: authoring run wrote a 188-line, 4-task plan, `check_plan.py` ALL PASS, **zero code fences at `standard` effort**, levels 3 `unit` / 10 `http` / 3 `browser`, floor applied correctly (share popup carries both a `browser` and an `http` case). Schedule run degraded to declared-only and said so, caught the T3/T4 collision, held T4 with a Ruling, and reported lane 0 serial execution rather than promising concurrency the fixture's config cannot host. Four further wording gaps the runs had to paper over, all now bound: a hold-back with no stated tiebreaker; `worktree_setup_cmds`-unset vs the lane-free classification having no stated precedence; `/kerbe:audit` referenced by `implement` Step 1 but **not built** (`ROADMAP.md:51` plans it) with no stated fallback, and no rule for the audit disagreeing with the plan's `[x]` marks; and — the sharpest — the derived-edge rule reading literally as create→modify only, so **two tasks both modifying a pre-existing file fall through it entirely**, which is the single most common collision and precisely the T3/T4 case. Now stated as a mutual exclusion, not a graph edge. Still unfixed and out of scope: `executor.adapter` is required-for-implement but nothing checks it before Step 4; multi-entry `code_roots` with no `{slice}` has no stated resolution rule. |
| 2026-08-20 | symfony-mini | sonnet | PASS — 9/9 checks on both runs; gap portion identical (6 open: download row, filter chips, share popup, dead export link, unimported hover, receipt stub); promise total varied 10 vs 8 (present-row granularity, see criterion above) |
| 2026-08-20 | flutter-mini | sonnet | PASS after harness fix — first run exposed two plants authored `absent` while EXPECTED said `partial` (fixture corrected: unrouted detail screen, undeclared Image.asset; `origin` semantics tightened in ledger.md); two post-fix runs 4/4 checks, verdict blocks byte-identical |
| 2026-08-20 | start gate: symfony-mini scratch × 2 (orders/true, cleanup/false) | sonnet | PASS — 15/15 and 14/14 checks; correct tailoring (infra slice omitted ENTITIES/ROUTES, dropped Panther section, Design row n/a); the false run exposed that check_start.py demanded all stack docs unconditionally — checker gained a per-run expected-docs arg (the run was right, the checker was wrong) |
| 2026-08-20 | (no run) extraction backstop 5 → 12 passes | — | Documented exception, no gate run: the stop condition (two consecutive zero-new passes) is unchanged; only the runaway backstop moved, and both fixtures converge at 3 passes, so the number is unreachable there. Motivated by the first real run (subscription): healthy decay 240 → +22 → +5 needs 6–7 passes and would have been falsely capped at 5. |
| 2026-08-20 | both (gate for constraints seam + slash-only frontmatter) | sonnet | PASS after two wording pins the gate itself surfaced: (1) a planned deliverable is ALWAYS a ledger row — one flutter run had dropped a plan-originated finding to the drop-file; (2) every hop is checked against the promise — GAP upstream never blanks downstream cells. Post-pin: flutter pair 4/4 byte-identical; symfony 3 runs 9/9 each, identical finding sets (leaf granularity varied 8–10 rows as documented). score.py forbid now matches the promise cell only — evidence may cite decoys as context. |
| 2026-08-20 | — (offline gates only) | — | kerbe:plan / kerbe:implement / kerbe:bug ported. Deterministic gates PASS: 52 unit tests green (`check_plan`, `check_progress`, portability invariants — harness-neutrality grep clean, both stack adapters declare every command capability and impact kind). **Pending, stated:** the three subagent fixture runs above (plan design-gate stop + authoring, implement tracker dry run) and the two first-real-run validations (implement per-task full-suite gate, bug impact table). |
| 2026-08-20 | first real run: `kerbe:bug` × 6 blockers (subscription) | opus | **PASS on the method, one gap found.** Impact analysis held across all six: R1-04's table found a second unattached-card site (`setDefault`) the report never mentioned, R1-01's tests followed the link rather than asserting a route name, R1-03 distinguished a scheduled cancel from a lapsed one. Commit discipline held — four pathspec-scoped commits with root-cause bodies, three entangled defects on one path deliberately committed together. **Gap: every commit cited per-file evidence (17/17, 19/19, 21/21 in the file) and no full-suite run.** The diffs changed `SubscriptionLifecycle::reactivate()` and `SubscriptionPlanRepository`, both consumed well outside the diff, yet the Symfony global-effect list is artifact-shaped (entity/migration/config/fixtures) and did not name them. Adapter hardened with a behavioural row (callers outside the diff, grep before deciding). |
| 2026-08-20 | first real run, part 2: the implement/bug full-suite gate (subscription) | opus | **Gap from the run above closed, and a second trap found.** Full suite green — `--testsuite 'Project Test Suite'` 1480 tests / 5438 assertions, no errors, no failures. The first attempt looked red (76 errors) because a bare `php vendor/bin/phpunit` runs *every* suite the config declares, including a Browser suite of 81 Panther tests that cannot run in that container (dead ChromeDriver) and hit a pre-existing `profession_id` FK. Zero errors outside `Tests\Browser`, and the four fix commits touch no entity and no migration, so no regression. Adapter hardened: `commands.md` now carries **Which suite is the gate** — name the suite explicitly, report a browser/e2e suite as a separate claim with its own prerequisites. A gate command that quietly includes an unrunnable suite reads as broken code; one that quietly excludes e2e hides real failures. |
| 2026-09-09 | plan gate: symfony-mini scratch × 2 (stop + authoring) | sonnet | **PASS — the code-boundary change.** Effort level is now a per-task plan field and sets how much code the task carries (full at `low`, seams + cases at `standard`/`deep`); Interfaces carry seams only; Step 1 carries a case table, not a test file; expected output is a shape, not a count. Offline: 57 tests green. **Stop run:** resolved build mode, stopped at the missing `SETTINGS.md`, refused to default `design_required` to false on a slice that visibly has UI. **Authoring run:** `ALL PASS`, 476 lines, effort spread 5 `standard` / 1 `low` / 1 `deep`, and the only fenced code in the plan is the `low` task's two-line Sass import — the boundary held without a rule per task. Two fixes the runs produced: (1) the gate's stop step now deletes the fixture's coverage-stub `PLAN.md` first, since leaving it resolves the run to remediation mode before the design gate is reached; (2) **`deep` was a parking space** — the authoring run legitimately escalated a task whose open question ("who is the member?") no spec doc answered, which is correct, but nothing stopped a planner from parking a *product* question there and freezing anyway. Spec and skill now bind the `deep` Decisions escape to questions the **codebase** can answer; a question needing a human goes back through `/kerbe:start`. |
| 2026-08-25 | — (offline gates only) | — | kerbe:review ported from the frozen suite. Deterministic gates PASS: 60 tests green (`check_review` structure checks — QR sequence, five sections with Flags last, tier-1 line refs + ATOMIC-ITEM Open cells, coverage-vs-changed-files, strikethrough hygiene; parity — both stacks ship `risk-tiers.md`, all three tiers, tier-3 exemption bound to full-suite). §1.4 fix carried into the port: the tier-3 "trust the tests" skip does not apply when a global-effect diff shows only a scoped run. **Pending, stated:** the subagent fixture run (step 2) and first-real-review validation of the judgment half. |
| 2026-09-16 | coverage: symfony-mini × 2, flutter-mini × 4; plan: symfony-mini scratch × 2 (stop + authoring); review: symfony-mini scratch × 2 | sonnet | **PASS — plan rows are seams, not approach (ledger.md), decision provenance (plan-spec 5a), review authority order.** Coverage: symfony 9/9 on both runs, gap portion identical (6 open). Flutter: the **first pair failed** P2 (the plan-only detail screen was routed to the drop-file under the first wording, which named "another task's Consumes" as the only consumer); rewording named the user as a consumer — a screen, route, command, endpoint or download a user reaches is always a seam — and the second pair scored 4/4 twice with identical gap portions (3 open, P-004 `plan:T3` kept). Plan: stop run halted at the design gate with the required sentence; authoring run `check_plan.py` ALL PASS, zero fenced code in any task, every Produces names its consumer, every Decisions line cites a REQ or reads worker's call. Review: the **first-ever step-2 fixture run** (pending since 2026-08-25) failed `check_review.py` on Branch/Date/Diff — the skill's format block never listed the metadata lines the checker requires; added, rerun ALL PASS with the planted `isGranted` guard at tier 1, SCSS and Twig tier 3, adversarial pass ran. First plant (a bare not-found guard) was correctly tier 2 per the adapter — the gate's "controller edit must be tier 1" presumes an auth/ownership condition; plant one. Judgment half of review still validates on the first real slice review. |
