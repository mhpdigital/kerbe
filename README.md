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

## Repository layout

- `skills/` — the plugin skills (`skills/coverage/SKILL.md`, references, scripts)
- `adapters/` — design adapters (`figma`, `none`) and stack adapters (`symfony`, `flutter`)
- `fixtures/` — mini projects with planted, known gaps; the standing acceptance gate for
  every change to a skill (`fixtures/ACCEPTANCE.md`)
- `docs/` — specs and implementation plans
