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

## kerbe:plan gate

Any change to `skills/plan/` (SKILL.md or `references/plan-spec.md`) reruns this before
real use:

1. `python3 -m unittest tests.test_check_plan tests.test_portability` — structural checker
   and the portability invariants (no harness mechanism in a skill body, no hardcoded
   project path).
2. Copy `symfony-mini` to a scratch dir. The fixture slice deliberately ships **no**
   `SETTINGS.md`: dispatch a fresh subagent to read `<repo>/skills/plan/SKILL.md` and run it
   on the scratch slice `cards`. It must **STOP at the design gate** and say the slice never
   answered the design question. A run that proceeds — or defaults `design_required` to
   false — is a gate failure, and the wording needs fixing.
3. In the scratch copy only, write `SETTINGS.md` with `design_required: true` and a dated
   Notes reason, and re-dispatch. It must now demand the Design-sources block, find it
   populated in `UI_ELEMENTS.md`, and write `planning/slices/cards/PLAN.md` (overwriting the
   fixture's plan in the scratch copy is expected — this is a plan-authoring run, not a
   coverage run).
4. Score: `python3 fixtures/check_plan.py <scratch>/planning/slices/cards/PLAN.md true` —
   exit 0 required.
5. Read the report: the plan's Global Constraints must quote the stack adapter's
   `commands.md` full-suite trigger, and every UI task must carry `node=… measured=…`.

## kerbe:implement gate

Any change to `skills/implement/` reruns this before real use. Implementation itself cannot
run against a fixture (it needs a real toolchain and a real git workspace), so the gate
covers the two things that are checkable offline and the rest is stated as a gap:

1. `python3 -m unittest tests.test_check_progress tests.test_portability`.
2. **Tracker derivation, dry run.** Copy `symfony-mini` to a scratch dir and dispatch a
   fresh subagent: read `<repo>/skills/implement/SKILL.md`, execute Steps 0–3 **only**
   (resolve the workspace, derive the tracker, choose the execution shape) against the
   scratch copy with `workspace.root` unset, and dispatch nothing. Score:
   `python3 fixtures/check_progress.py <scratch>/claude-progress.md <scratch>/planning/slices/cards/PLAN.md`
   — exit 0 required, and the report must name the execution shape (chain vs group) with the
   plan evidence for it.
3. **The per-task gate is the part that matters most and cannot be fixture-tested.** It is
   validated on the first real slice run: a task touching a global-effect artifact must be
   refused as done until the full-suite output is pasted. Record the result below.

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

## Recorded runs

| Date | Fixture | Model | Result |
|---|---|---|---|
| 2026-08-20 | symfony-mini | sonnet | PASS — 9/9 checks on both runs; gap portion identical (6 open: download row, filter chips, share popup, dead export link, unimported hover, receipt stub); promise total varied 10 vs 8 (present-row granularity, see criterion above) |
| 2026-08-20 | flutter-mini | sonnet | PASS after harness fix — first run exposed two plants authored `absent` while EXPECTED said `partial` (fixture corrected: unrouted detail screen, undeclared Image.asset; `origin` semantics tightened in ledger.md); two post-fix runs 4/4 checks, verdict blocks byte-identical |
| 2026-08-20 | start gate: symfony-mini scratch × 2 (orders/true, cleanup/false) | sonnet | PASS — 15/15 and 14/14 checks; correct tailoring (infra slice omitted ENTITIES/ROUTES, dropped Panther section, Design row n/a); the false run exposed that check_start.py demanded all stack docs unconditionally — checker gained a per-run expected-docs arg (the run was right, the checker was wrong) |
| 2026-08-20 | (no run) extraction backstop 5 → 12 passes | — | Documented exception, no gate run: the stop condition (two consecutive zero-new passes) is unchanged; only the runaway backstop moved, and both fixtures converge at 3 passes, so the number is unreachable there. Motivated by the first real run (subscription): healthy decay 240 → +22 → +5 needs 6–7 passes and would have been falsely capped at 5. |
| 2026-08-20 | both (gate for constraints seam + slash-only frontmatter) | sonnet | PASS after two wording pins the gate itself surfaced: (1) a planned deliverable is ALWAYS a ledger row — one flutter run had dropped a plan-originated finding to the drop-file; (2) every hop is checked against the promise — GAP upstream never blanks downstream cells. Post-pin: flutter pair 4/4 byte-identical; symfony 3 runs 9/9 each, identical finding sets (leaf granularity varied 8–10 rows as documented). score.py forbid now matches the promise cell only — evidence may cite decoys as context. |
| 2026-08-20 | — (offline gates only) | — | kerbe:plan / kerbe:implement / kerbe:bug ported. Deterministic gates PASS: 52 unit tests green (`check_plan`, `check_progress`, portability invariants — harness-neutrality grep clean, both stack adapters declare every command capability and impact kind). **Pending, stated:** the three subagent fixture runs above (plan design-gate stop + authoring, implement tracker dry run) and the two first-real-run validations (implement per-task full-suite gate, bug impact table). |
| 2026-08-20 | first real run: `kerbe:bug` × 6 blockers (subscription) | opus | **PASS on the method, one gap found.** Impact analysis held across all six: R1-04's table found a second unattached-card site (`setDefault`) the report never mentioned, R1-01's tests followed the link rather than asserting a route name, R1-03 distinguished a scheduled cancel from a lapsed one. Commit discipline held — four pathspec-scoped commits with root-cause bodies, three entangled defects on one path deliberately committed together. **Gap: every commit cited per-file evidence (17/17, 19/19, 21/21 in the file) and no full-suite run.** The diffs changed `SubscriptionLifecycle::reactivate()` and `SubscriptionPlanRepository`, both consumed well outside the diff, yet the Symfony global-effect list is artifact-shaped (entity/migration/config/fixtures) and did not name them. Adapter hardened with a behavioural row (callers outside the diff, grep before deciding). |
| 2026-08-20 | first real run, part 2: the implement/bug full-suite gate (subscription) | opus | **Gap from the run above closed, and a second trap found.** Full suite green — `--testsuite 'Project Test Suite'` 1480 tests / 5438 assertions, no errors, no failures. The first attempt looked red (76 errors) because a bare `php vendor/bin/phpunit` runs *every* suite the config declares, including a Browser suite of 81 Panther tests that cannot run in that container (dead ChromeDriver) and hit a pre-existing `profession_id` FK. Zero errors outside `Tests\Browser`, and the four fix commits touch no entity and no migration, so no regression. Adapter hardened: `commands.md` now carries **Which suite is the gate** — name the suite explicitly, report a browser/e2e suite as a separate claim with its own prerequisites. A gate command that quietly includes an unrunnable suite reads as broken code; one that quietly excludes e2e hides real failures. |
| 2026-08-25 | — (offline gates only) | — | kerbe:review ported from the frozen suite. Deterministic gates PASS: 60 tests green (`check_review` structure checks — QR sequence, five sections with Flags last, tier-1 line refs + ATOMIC-ITEM Open cells, coverage-vs-changed-files, strikethrough hygiene; parity — both stacks ship `risk-tiers.md`, all three tiers, tier-3 exemption bound to full-suite). §1.4 fix carried into the port: the tier-3 "trust the tests" skip does not apply when a global-effect diff shows only a scoped run. **Pending, stated:** the subagent fixture run (step 2) and first-real-review validation of the judgment half. |
