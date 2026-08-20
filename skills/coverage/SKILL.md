---
name: coverage
description: >-
  Use when you need to know whether a slice is finished — before implementing (does the
  plan task everything the design and spec promise?) or before sign-off (is everything
  promised actually built and wired?) — or when the user asks what is missing, whether
  anything was dropped between design, spec, plan and code, or for a to-build inventory.
disable-model-invocation: true
---

# kerbe:coverage — is anything promised missing from the build?

This skill answers exactly one question: **is anything that was designed, specified, or
planned missing from the build?** It exists so nobody discovers missing functionality by
stumbling over it later. It is not a code review, not a doc-accuracy audit, not a test
audit — those belong to other skills.

The relay is **design → spec → plan → code**, checked as pairwise two-column hops
accumulated in one artifact: the **promise ledger** (`PROMISES.md`, format in
`references/ledger.md`). One row per leaf-level promise; a row's status is where the relay
breaks. The verdict is **computed by `scripts/verdict.py` from the ledger — never asserted
by you or any agent.**

## The admission rule (structural)

A finding either **is a ledger row** with a real `promised-by` citation, or it goes to
`OUT_OF_SCOPE.md` beside the ledger, uncounted (format in `references/ledger.md`).
Seriousness is not the test; a promise is.

| Observation | Verdict |
|---|---|
| A designed "Update card" link is in no template | row — promised, absent |
| A button renders but its route is unwired | row — `partial` (present but functionally missing) |
| Two live payment-API calls inside an open DB transaction | drop-file → review skill |
| A doc is stale about a thing that exists | drop-file → audit skill |
| A test asserts nothing | drop-file → review skill |
| Unticked checkboxes for built features | drop-file — ledger hygiene, not a missing feature |

"Present but functionally missing" — stub, unwired route, dead link, unimported
stylesheet, class mismatch — **is** in scope: that is how a feature ships as a shell.

## Setup

1. Read `kerbe.yml` at the target project root. Missing ⇒ **hard stop**: tell the user to
   create one from the plugin's `kerbe.yml.example`. Field meanings: `references/config.md`.
2. Resolve the slice folder (`{planning_root}/{slice}`), the design adapter
   (`adapters/design/{name}.md`) and stack adapter (`adapters/stack/{name}/verify.md`).
3. Mode: obey the user if stated; else probe `stack.code_roots` for the slice's artifacts —
   substantially none ⇒ `pre-impl`, else `audit`.
4. If `kerbe.constraints` is set — plus `kerbe.constraints_by_skill.coverage` when
   present — append those lines verbatim to every extractor and verifier prompt you
   dispatch. Constraints bound what agents may do to the environment
   (e.g. no test commands); they never narrow what is searched.
5. State mode, adapters, and paths in one line before starting. One slice per run;
   cross-slice observations go to the drop-file.

## Phase A — EXTRACT the promise ledger

Goal: `PROMISES.md` in the slice folder — the frozen denominator. Extraction is bounded by
the source documents, so a stop-when-nothing-new loop is safe **here and only here**.

1. **Freeze the sources.** Design: follow the design adapter (snapshot once; reuse an
   existing snapshot). Docs and plan: record `git log -1 --format=%h -- <slice folder>` as
   the `docs@` pin. Write the ledger header with `STATUS: EXTRACTING`.
2. **Dispatch one extractor per source class** (design / spec docs / plan) with
   `model: sonnet`, using this prompt with the placeholders filled:

   ```text
   You are an extraction pass for kerbe:coverage on slice {slice} in {project_root}.
   Read first: {plugin}/skills/coverage/references/ledger.md (the row schema) and
   {plugin}/adapters/design/{design_adapter}.md.
   Your frozen sources (read nothing else): {source file list}.
   Propose promise rows: one row per LEAF-LEVEL promise a user could recognize —
   every interactive design leaf, every requirement clause, every plan-task
   deliverable. A page or section is never one row; its leaves are the rows.
   Return ONLY a markdown table: | promise | promised-by |. Real citations only.
   Do not verify anything, do not read application code, do not invent promises.
   ```

3. **Merge and dedupe** (same `promised-by` + same leaf = one row). Assign ids `P-001…`.
   Fill `spec`/`plan`/`code` with `?` (or per obvious source: a design row's `spec` stays
   `?` until verified; a spec-originated row gets `spec: origin`).
4. **Safety passes:** dispatch a fresh extractor over ALL sources with the same prompt.
   Add whatever is new. Stop after **two consecutive passes that add zero rows** — that is
   the only stop condition, however many passes it takes; healthy discovery decays
   (e.g. 240 → +22 → +5 → 0 → 0). A runaway backstop of **12 passes** exists solely to
   halt a loop that never decays: hitting it means a source is moving or the granularity
   rules are churning — record `EXTRACTION: capped (passes=12)`, say so, and never present
   a capped ledger as a converged denominator.
5. **Freeze:** set `STATUS: FROZEN`, record `EXTRACTION:` outcome, commit the ledger (and
   snapshot) to the planning repo. After this point rows are verified, corrected, or
   demoted — the denominator does not grow or shrink silently.

## Phase B — VERIFY every row (no loop)

1. **Batch rows** (≤20 per agent) and dispatch verifiers with `model: haiku`:

   ```text
   You are a verification pass for kerbe:coverage. Verify ONLY rows {ids} of
   {ledger path}. Read first: {plugin}/skills/coverage/references/ledger.md and
   {plugin}/adapters/stack/{stack}/verify.md (the wiring recipes).
   Sources: the slice's spec docs and plan in {slice folder}; code under
   {code_roots}. Match plan tasks by reading the task BODY, not the title.
   For each row fill spec, plan, code, evidence per the vocabulary. `present`
   requires existence AND wiring evidence (file:line for both). If a check
   cannot run, leave `?` and say why in evidence.
   Anything real you notice that has no promise row: return it on a separate
   OUT-OF-SCOPE list — never as a row.
   Return ONLY: your rows as a full markdown table, then the OUT-OF-SCOPE list.
   ```

   Verifiers return rows; **you merge them into the ledger** (they never edit the file —
   no write races; re-running a row is always safe). Append their out-of-scope lines to
   `OUT_OF_SCOPE.md` with routing tags.
2. **Quality pass** (one fresh agent, `model: haiku`): re-verify every `GAP` / `absent` /
   `partial` row **including that the `promised-by` citation really promises it** — a
   stretched promise is the one way a non-finding sneaks in — and spot-audit 10% (min 5)
   of `present` rows. It returns confirm/demote/correct per row with evidence.
3. Apply the quality pass: demoted rows are **deleted** (id retires, finding moves to the
   drop-file with the demotion reason); corrections update cells.
4. In `pre-impl` mode label expected absences `to-build`, and verify the `spec` and `plan`
   hops with full rigor — that is the mode's deliverable.

## Verdict

Run `python3 {plugin}/skills/coverage/scripts/verdict.py PROMISES.md` and **paste its
output verbatim** into your summary, followed by the open rows (id, promise, evidence) and
a pointer to `OUT_OF_SCOPE.md`. Never restate, adjust, or recompute its numbers. Exit 2
means fix the ledger format. Commit the final ledger and drop-file.

After fixes land, re-verify the affected rows against the **same frozen ledger** and rerun
the script — the denominator moves only when the user asks for a new extraction (design
changed, scope changed), which produces a new ledger whose diff against the old one is the
record of what moved.

## Rules

- **Report only.** Never edit application code or docs in any mode; closing gaps is a
  separate, user-approved step.
- **No row, no count.** Everything else goes to the drop-file, routed, uncounted.
- Docs are read as the record of **what must exist** — never audited for accuracy.
- A sibling slice's feature is never this slice's gap (drop-file).
- Every `present` cites existence AND wiring. `?` is honest; silent ✓ is not.
- No `|` inside ledger cells. Ids never reused.
- Any change to this skill, its references, adapters, or scripts must pass
  `fixtures/ACCEPTANCE.md` (planted gaps found, decoys uncounted, verdict stable across
  two runs) **before** it is used on a real project.
