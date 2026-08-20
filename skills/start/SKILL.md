---
name: start
description: >-
  Use when starting a new feature slice — create its folder, populate the spec docs from
  the lifecycle and stack-adapter templates, and register it in the slice index — or when
  asked for slice status, the slice list, or to advance a slice's lifecycle stage.
disable-model-invocation: true
---

# kerbe:start — open a slice

Creates a slice folder with a tailored, template-derived doc set, registers it in the
index, and settles the one blocking decision (`design_required`) before anything else is
written. Everything project-specific resolves through `kerbe.yml`
(`references/../coverage/references/config.md` documents the fields); templates ship with
the plugin — lifecycle-neutral ones in this skill's `templates/`, stack-flavored ones in
`adapters/stack/{adapter}/templates/`.

## Setup

1. Read `kerbe.yml` at the project root. Missing ⇒ **hard stop**: point at
   `kerbe.yml.example`. Resolve `planning_root`, `design.adapter`, `stack.adapter`,
   `timezone`, and optional `legacy_root`.
2. The registry is `{planning_root}/INDEX.md`. If it does not exist, create it from this
   skill's `templates/INDEX.md` and say so.

## `/kerbe:start` with no arguments — status

Read `{planning_root}/INDEX.md` and show a summary table of all slices with their current
status. Nothing is created.

## `/kerbe:start <slice-id-or-feature-name>` — create

1. Derive the slice id (kebab-case). Check `INDEX.md`: if the slice exists, report its
   status and stop — never recreate.
2. **Settle `design_required` — ask, never assume.** This step is blocking.
   - If the project's `design.adapter` is `none`, record `design_required: false` with the
     Notes reason "project has no design adapter" — that is a recorded project decision,
     not an inference.
   - Otherwise use `AskUserQuestion`. Do **not** infer the answer from the slice name or
     whether a design file happens to exist — inference is exactly the forgetting this
     setting exists to stop. You may attach a recommendation, clearly labelled as such.
   - Frame the options by what they oblige: `true` = design-driven, `UI_ELEMENTS.md` is
     created with an unfilled Design-sources block and `/kerbe:plan` will refuse until
     `/kerbe:figma` fills it; `false` = no design leg, `UI_ELEMENTS.md` omitted, and the
     Notes row must say **which kind** of false — "no UI at all" vs "has UI, no design
     yet" (the second is a design question to raise, and flips to `true` when the frame
     lands).
3. Create `{planning_root}/{slice-id}/` and copy `templates/SETTINGS.md`, writing the
   chosen value into the settings block and a dated Notes row with the reason.
4. **Create the doc set, tailored to the slice — never produce docs that don't apply:**
   - From this skill's `templates/`: `REQUIREMENTS.md` always; `UI_ELEMENTS.md` only when
     `design_required: true`; `TIMING.md` always (substitute `{kerbe.timezone}`).
   - From `adapters/stack/{adapter}/templates/`: `ENTITIES.md`, `ROUTES.md`,
     `SECURITY.md`, `DONE_CRITERIA.md` — omit `ENTITIES.md`/`ROUTES.md` for infra slices;
     drop `DONE_CRITERIA.md`'s browser/widget-test section for slices with no UI.
   - Legacy-migration docs (`IMPORT.md`, `CODEMAP.md`): only when `kerbe.legacy_root` is
     configured AND a legacy counterpart actually exists there — **verify by looking**,
     never infer "no legacy" from the slice type.
5. Substitute `{Slice Name}` in every copied template; leave other `{placeholders}` for
   the filling phase. Every `UI_ELEMENTS.md` feature section with 5+ elements must end
   with a `_Review code: {NNNN}_` line — random 4-digit, unique per section (audit uses
   them to verify human review).
6. Stamp `TIMING.md` row "1. Start" with `TZ='{kerbe.timezone}' date '+%Y-%m-%d %H:%M'`.
   If `design_required: false`, write `n/a (design_required: false)` in the "2. Design"
   row so a skipped step is distinguishable from one not yet run.
7. Add the slice to `INDEX.md` with status `planning` and today's date.
8. When the config places the slice's code outside the project root (a `{slice}` code root,
   or a `workspace.root` elsewhere), name the workspace path this slice's code will live in
   — it does not exist yet and this skill never creates it, but the build session will need
   access to both roots and this is where that becomes visible.
9. Report what was created, state the recorded `design_required` value back to the user
   (it decides whether `/kerbe:figma` is mandatory next or skipped), and give the fill
   order: UI_ELEMENTS (leaf-level — one row per interactive leaf with node id; this is
   the granularity the coverage ledger will verify) → ENTITIES → ROUTES → SECURITY →
   DONE_CRITERIA → REQUIREMENTS (a `REQ-<DOMAIN>-<NNN>` for every testable requirement,
   sourced from the docs above — these become the `@req` targets).

## Lifecycle stage transitions

When asked to advance a slice's stage: update `INDEX.md`. Statuses:
`planning → scoped → ready → in-progress → in-review → done | dropped | parked`.
Advancing to `in-progress` ⇒ remind the user to run `/kerbe:audit` first to generate the
progress ledger with verification questions, reviewed by the user before agents implement.

## Rules

- **Every slice gets `SETTINGS.md`, every key explicit, every value dated with a
  reason.** Never create a slice folder with the settings question unanswered.
- Never delete slice folders — mark them `dropped` in `INDEX.md` with a reason.
- Always use today's date for lifecycle entries; git history is the audit trail.
- This skill writes only under `{planning_root}/` — never application code.
- Any change to this skill or its templates must pass the start checks in
  `fixtures/ACCEPTANCE.md` before use on a real project.
