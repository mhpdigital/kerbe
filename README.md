# Kerbe

Portable slice-based SDLC skills for Claude Code, with stack and design adapters. The
lifecycle is stack-agnostic; everything project- or stack-specific lives in a `kerbe.yml`
config and swappable adapter files — never in a skill body.

*Kerbe* (German): a notch cut through the full thickness of the material — the geometry of a
thin vertical slice. See `ROADMAP.md` for the full project plan and naming rationale.

## Install (local, while in development)

Point Claude Code at this repository as a local plugin (marketplace metadata is in
`.claude-plugin/`). Skills are invoked as `/kerbe:<skill>`.

## Skills

### `kerbe:coverage`

Answers exactly one question: **is anything that the approach documentation promises missing
from the build?** Two phases — EXTRACT a frozen, committed promise ledger (`PROMISES.md`, one
leaf-level promise per row), then VERIFY each row against the code with wiring evidence. The
verdict is computed by `scripts/verdict.py` from the ledger; no agent ever asserts
completeness. Design and spec: `docs/specs/2026-08-20-coverage-skill.md`.

Usage: from a project with a `kerbe.yml` (copy `kerbe.yml.example`), run
`/kerbe:coverage <slice>` — before implementing, it checks the plan tasks everything the
design and spec promise (`pre-impl`); after, it checks everything promised is built and
wired (`audit`).

**Contributors:** any change to `skills/coverage/` or `adapters/` must pass the fixture
gate in `fixtures/ACCEPTANCE.md` (planted gaps found, decoys uncounted, verdict stable
across two runs) before it is used on a real project.

### `kerbe:start` · `kerbe:figma`

Open a slice (tailored doc set from lifecycle + stack templates, `design_required` settled
by asking, never inferring) and run its design leg (grade, extract at leaf level, compare
against the spec, fill the Design-sources block `kerbe:plan` blocks on).

### `kerbe:plan`

Freezes the slice's task list as `PLAN.md` — the HOW, with code, one task per independently
testable deliverable. Blocking design gate before the freeze: an unanswered
`design_required`, an unfilled Design-sources block, or a design measured before its last
modification each stop the run rather than resolving quietly. Plan authoring is specified
in-repo (`skills/plan/references/plan-spec.md`), so the lifecycle has **no external skill
dependency**; `superpowers:writing-plans` is used when installed, under the same two
overrides (fixed name, slice-folder location).

### `kerbe:implement`

Builds the slice from the frozen plan: resolves the workspace deterministically (a review
workspace supersedes the slice one; no worktree convention configured ⇒ the code root *is*
the workspace), derives the live tracker (`claude-progress.md`, never a hidden dotfolder),
dispatches one isolated worker per task, and gates each task on evidence. The gate that
earns the skill: a diff touching a **global-effect artifact** — anything whose effect is
only observable through *other* components' tests, listed per stack in the adapter's
`commands.md` — is not done until the full suite has run and its output is pasted. A scoped
run is never a no-regression claim. Also runs **remediation mode** against a coverage fix
list, where the frozen ledger stays the denominator and `verdict.py` is the exit condition.

### `kerbe:bug`

Impact analysis *before* the fix, so one commit closes the whole class: classify the root
cause by artifact kind, run the stack adapter's `impact.md` checks, plus three that hold on
any stack — evidence locality, one hop followed (does the promised action reach a
destination that exists, admits the audience, and acts on the object?), and both sides of a
state transition. Then fix and test in one pass, validate with the full suite, commit scoped
by pathspec with a root-cause message.

### `kerbe:review`

Risk-tiered code review of a slice's diff, run **after** the coverage verdict: tier 1
business logic read line by line with per-row open commands (`editor_cmd` from the
config), tier 2 glue read for flow, tier 3 boilerplate trusted only behind a
**full-suite** run — when a global-effect diff shows only a scoped run, the tier-3 skip
does not apply. An adversarial pass tries to break the draft review before it is
recorded as a sequential QR in the slice's `REVIEW.md` (plus a human `REVIEW_GUIDE.md` on
the first review). Classification rules live per stack in `adapters/stack/*/risk-tiers.md`;
findings route to `kerbe:bug`, never into the coverage ledger.

### Executors

Skill bodies name worker **intent** only; the dispatch mechanism lives in
`adapters/executor/` (`claude`, `inline`). A grep guard in `tests/test_portability.py` keeps
it that way, so the lifecycle stays portable to another harness.

## The lifecycle in one picture

`docs/lifecycle.md` carries the whole flow as a mermaid diagram: a project cut into slices,
Loop 1 (build, with its three stop-rather-than-guess gates), the frozen promise ledger that
measures the result, and Loop 2 (remediation, repeating until `verdict.py` reports nothing
open). `docs/render-lifecycle.sh` prints it to a single-page PDF sized to the diagram's own
aspect ratio.

## Repository layout

- `skills/` — the plugin skills (`coverage`, `start`, `figma`, `plan`, `implement`, `bug`, `review`)
- `adapters/` — design adapters (`figma`, `claude-design` — git-committed `*.dc.html`
  artboards, node id = element `id`, no API — and `none`), stack adapters (`symfony`, `flutter`:
  `verify.md` / `commands.md` / `impact.md` / `risk-tiers.md`), executor adapters (`claude`, `inline`)
- `fixtures/` — mini projects with planted, known gaps; the standing acceptance gate for
  every change to a skill (`fixtures/ACCEPTANCE.md`)
- `docs/` — specs and implementation plans
