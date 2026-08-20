---
name: figma
description: >-
  Use when fetching or analysing a slice's Figma design — grading it against the handoff
  gates, extracting UI elements with measurements, comparing the design against
  UI_ELEMENTS.md, filling a slice's Design-sources block, or checking design provenance
  and freshness of built UI.
disable-model-invocation: true
---

# kerbe:figma — the design leg

Fetch and analyse the design file for a slice: grade the handoff, extract elements at
leaf granularity, compare against the spec, and write the Design-sources block that
`/kerbe:plan` blocks on. Everything project-specific resolves through `kerbe.yml`.

## Setup

1. Read `kerbe.yml` at the project root (hard stop if missing). Resolve
   `design.file_key`, token (`design.token_env` else export
   `KERBE_FIGMA_TOKEN_CMD="<design.token_cmd>"`), `planning_root`, `timezone`, and the
   optional `design.checklist` and `design.freshness_cmd`.
2. If `design.adapter` is `none`, stop: this project has no design leg by decision.
3. Scripts live in this skill's `scripts/`. A `--file` argument or pasted URL from the
   user overrides the config file key (accepts bare keys and figma.com/design|file URLs).

## Operations

### `grade` — handoff gates

```bash
python3 {skill}/scripts/grade.py --file <key> [--page "<page name>"]
```

Gate-by-gate pass/fail (auto-layout, semantic names, variant naming, groups-as-
containers; API-unverifiable gates are printed as such, never guessed). When
`design.checklist` is configured, read that doc and report against its wording too.

### `extract` — full element table

```bash
python3 {skill}/scripts/extract_elements.py --file <key> [--page "<page name>"]
# offline, from a committed snapshot (no token, no network):
python3 {skill}/scripts/extract_elements.py --from-json <slice>/design-cache/file.json [--page "<page name>"]
```

Hierarchical table with node ids, colours, fonts, spacing, radii, layout, plus colour and
font summaries. Prefer `--from-json` against the slice's snapshot when one exists —
same-input-same-output, and it keeps analysis consistent with what coverage verifies.

### `compare` — design ↔ UI_ELEMENTS.md

Extract, then diff against the slice's `UI_ELEMENTS.md` at **leaf level**: colour, font,
size and spacing mismatches; leaves in the design missing from the spec; spec rows with no
design counterpart. Report per leaf with node ids.

### `fetch` — raw data / metadata

```bash
python3 {skill}/scripts/fetch.py --file <key> [--node "1:23"] [--depth N] [--metadata]
```

### Provenance tags and freshness

Every UI file that implements a design carries
`@figma file=<fileKey> node=<id> frame=<name> measured=YYYY-MM-DD` — pin the **node id**,
never just the frame name (files carry stale iterations of the same frame). The design
file is the source of truth; `UI_ELEMENTS.md` and code are a cache — re-measure the live
node before UI layout work and update `measured=`.

Freshness check: if `design.freshness_cmd` is configured, run it (coverage = changed UI
files with no tag; staleness = `measured=` older than the file's `lastModified`, which
`fetch.py --metadata` provides). If it is not configured, do the check manually — grep
`@figma` tags under the stack's UI roots and compare dates — and **say the tooling is
missing** rather than silently skipping.

## Writing the Design-sources block back (per-slice runs)

When a run is for a specific slice, **update that slice's `UI_ELEMENTS.md` Design-sources
block as part of the run** — file key, page, one row per screen with node id and today's
date as `measured=`. Never print a table and leave the copying manual: an unfilled block
is exactly what `/kerbe:plan` blocks on, and the manual copy is where the design leg
historically got dropped.

Check the slice's `SETTINGS.md` first (`design_required:`):

- `true` → fill the block; this run is what unblocks the plan step.
- `false` → the slice is recorded as having no design leg. Say so, and ask whether the
  setting should flip before writing into a doc the slice is not meant to have.
- missing/unanswered → STOP and send the user to `/kerbe:start`. Never create the block
  against an unanswered setting.

Then stamp the slice's `TIMING.md` "2. Design" row with
`TZ='{kerbe.timezone}' date '+%Y-%m-%d %H:%M'`.

## Rules

- Never guess a file key — config, argument, or ask.
- API-unverifiable properties (variables, shared styles) are reported as unverifiable,
  confirmed only by designer certification.
- Extraction and comparison work at **leaf level** with node ids — the granularity the
  spec templates and the coverage ledger use.
- Any change to this skill or its scripts must pass the figma checks in
  `fixtures/ACCEPTANCE.md` before use on a real project.
