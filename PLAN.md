# Kerbe — portable slice-based SDLC plugin with stack adapters

> Plan created 2026-07-30, revised same day. Source: consistency analysis of the 13 `sdlc-*`
> user-level skills plus `slice-start` in `~/.claude/skills/`.
>
> **Goal:** a publishable Claude Code plugin whose lifecycle is stack-agnostic and whose
> stack/tool specifics live in swappable adapters — built alongside the existing `sdlc-*`
> suite, never on top of it, and proven on two real stacks.

**Placeholder convention.** This repo is public, so client-identifying values are written as
`<placeholder>` and the private Symfony build the suite was grown on is called **the reference
project**. The concrete values live in a gitignored `SCRUB_TARGETS.local.md`, so Phase 5.1's
checklist stays greppable without those strings entering public history. `file:line` citations
into `~/.claude/skills/sdlc-*` are kept — they point at private local skills and are what makes
the checklist actionable.

---

## Naming

**`kerbe`** — German *Kerbe*, a notch or groove cut into material. Same word as English
*kerf*: Old English *cyrf* / *ceorfan* "to cut, carve", German *kerben* from Old High German
*kerban*, one Germanic root. The metaphor is a precise cut through the full thickness of the
material — the geometry of a thin vertical slice.

Chosen over `kerf` (a programming language + tick database at `kevinlawler/kerf`, a CAD system
at `vul-os/kerf` shipping `kerf-sdk` on PyPI, `github.com/kerf` taken), `sashimi` (the dominant
documented meaning is DeGrace's *sashimi waterfall model* — wrong methodology), and
`thinslice` (Thinslices is a 130-person software product firm). Verified free across all 276
entries in `anthropics/claude-plugins-official`. No software tool named Kerbe.

**Runner-up if `kerbe` is dropped:** `falz` (a rabbet — the groove cut along an edge). Emptiest
namespace of everything checked; searches return only surnames.

### The brand is a namespace, not a vocabulary

"Slice" stays the domain noun everywhere. It is already the industry's word (vertical slice,
thin slice), it is understood on sight, and there are ~3 months of the reference project's
artifacts built on
it (`planning/<product>/slices/`, `INDEX.md`, `slice/*` + `review/*` branches, `SLICE_GUIDE.md`,
`SLICE_EXTRACTION_PLAYBOOK.md`, `SCOPE.md` lifecycle rows). Renaming the concept costs a
migration for zero gain — Docker owns the brand, "container" is still the noun.

`kerbe` appears in exactly five places: plugin slug, skill prefix, config filename, repo name,
README. Skill bodies say *slice*, `{planning_root}/{slice}/`, `slice/{id}`.

**Skill names shed the redundant prefix** — `sdlc:sdlc-audit` stutters:

```
kerbe:start      kerbe:figma      kerbe:scaffold    kerbe:plan
kerbe:implement  kerbe:audit      kerbe:coverage    kerbe:flowmap
kerbe:split      kerbe:review     kerbe:bug         kerbe:help
```

---

## Strategy: parallel suites, frozen source, validated extraction

The `sdlc-*` skills are load-bearing on a live client build. They are **never edited** by this
project. Kerbe is built beside them by copying, and the old suite is retired only after a
side-by-side comparison proves the new one behaves identically.

```
~/.claude/skills/sdlc-*   FROZEN. Still drives the reference project.   /sdlc-audit
~/projects/kerbe/         NEW repo. The plugin.                         /kerbe:audit
```

Namespacing makes the overlap unambiguous — different strings, no guessing which skill fires.

### The freeze rule (non-negotiable during overlap)

> `sdlc-*` gets **bug fixes only — no new features.** Every bug fix must also land in Kerbe,
> or be consciously recorded as not applicable.

Without this, parallel becomes a permanent fork and the invariants drift. The things that will
drift are the suite's real IP: `sdlc-audit`'s un-pre-fillable verification questions,
`sdlc-coverage`'s two-consecutive-clean-rounds convergence rule, `sdlc-scaffold`'s
non-skippable manifest contract, `sdlc-audit`'s scope-conflation guard.

### Ordering: contract first, then BOTH adapters concurrently

Two earlier drafts got this wrong. Draft 1 sequenced Flutter first (to dodge scrub work) —
but extraction-by-copy already avoids touching the frozen source, so Flutter-first only cost
designing the abstraction against the least-known stack. Draft 2 sequenced Symfony first with a
one-time validation gate — safer, but its "sanity-check the contract against Flutter **on
paper**" step was the weak link: writing a field down is not the same as building against it.

**Both adapters are built concurrently, against a contract settled first.**

Why concurrent wins:

- **The contract gets real pressure from both sides at once.** With two adapters under
  construction you physically cannot leave a field Symfony-shaped — Flutter pushes back
  immediately. Paper review does not achieve this.
- **Neither track blocks the other.** Symfony extraction doesn't wait on the mobile app
  existing; the mobile app doesn't wait on extraction finishing.
- **The frozen `sdlc-*` suite becomes a standing baseline, not a gate.** It sits there,
  diff-able at any moment, as often as wanted.
- **The two tracks compete less for attention than it appears** — Symfony extraction is
  grinding work, Flutter is discovery work. Different modes.

Concurrency's real risk is failure attribution, and the standing baseline solves exactly that:

| Symptom | Diagnosis |
|---|---|
| Symfony-via-Kerbe diverges from Symfony-via-`sdlc-*` | extraction bug |
| Symfony matches baseline, Flutter is painful | contract gap or Flutter adapter gap |

### Two rules that make concurrency safe

1. **Settle the contract before filling either adapter in** — by **stubbing both at once**
   (`ADAPTER.md` + `layout.md` + `doc-set.md` for Symfony *and* Flutter, no `scaffold.md` /
   `verify.md` content yet). Cheap, real, and it surfaces Symfony-shaped fields immediately.
2. **Contract-change protocol.** When one stack forces a contract change, the *other* adapter is
   updated **in the same commit** and the baseline comparison re-runs. Without this, two
   adapters drift apart and the abstraction is fiction.

---

## §0 Why adapters (the decision everything rests on)

The suite already separates into three layers; today they are fused into single files.

| Layer | Nature | Examples |
|---|---|---|
| **Lifecycle** | invariant across any stack | slice concept, 7-step flow, INDEX registry, planned-vs-built audit, design→req→plan→code coverage relay, split-smell scoring, human-review codes, timing stamps |
| **Stack adapter** | one per framework | scaffold templates, source layout, risk-tier rules, test/lint/build commands, "is it wired?" recipes, which planning docs apply |
| **Integration adapter** | one per external tool | feedback source (monday.com), design source (Figma), editor open-command, CI/deploy topology |

### Verified constraint that decides the packaging

The plugin format has **no dependency mechanism**. Every schema key in use across all 276
entries of the official directory:

```
author, category, description, displayName, homepage, keywords,
lspServers, name, skills, source, strict, tags, version
```

No `dependencies`, no `requires`. A plugin cannot auto-install a sibling, and the core cannot
reliably detect whether an adapter plugin is present.

**Rejected:** *plugin-per-adapter* (`kerbe-core` + `kerbe-flutter` + …) — N manual installs, and
with two plugins both exposing `scaffold`, `/scaffold` is genuinely ambiguous. Revisit only if
the format gains dependencies. *Adapters only in the consuming repo* — max flexibility, zero
sharing; **kept as an override path**, not the distribution path.

### Chosen shape: one plugin, adapters as on-demand reference files

```
kerbe/
├── .claude-plugin/
│   ├── plugin.json                  # version, author, license
│   └── marketplace.json             # self-servable
├── skills/
│   └── <name>/SKILL.md              # lifecycle only — no stack specifics
├── adapters/
│   ├── ADAPTER_CONTRACT.md
│   ├── stack/{symfony,flutter}/
│   └── integration/{figma,github-issues,monday}/
├── templates/kerbe.config.md        # copied into a consuming repo
├── README.md
└── LICENSE
```

Each skill reads the consuming repo's `kerbe.config.md`, learns which adapters apply, then
loads only those files. Progressive disclosure — the pattern the built-in skills use with
`references/`. SKILL.md stays small; adapter files can be as long and opinionated as needed.

### The second axis: harness adapters

Stack adapters are one axis. **Harness adapters are the same pattern on a different axis** — and
the good news is that `SKILL.md` has become the de-facto common format, so the canonical
`skills/` directory is shared and each harness needs only a thin root-level manifest.

Verified state (July 2026):

| Harness | Skills live at | Manifest | Invocation | Distribution |
|---|---|---|---|---|
| **Claude Code** | `skills/<n>/SKILL.md`; `~/.claude/skills/` | `.claude-plugin/plugin.json` + `marketplace.json` | `/kerbe:audit` | marketplace repo (self-host or official directory) |
| **Codex CLI** | `~/.codex/skills/<n>/`, project `.codex/skills/`, `~/.agents/skills/` | `.codex-plugin/` + `skills/*/agents/openai.yaml` | `$kerbe-audit` | portal archive, or PR to a plugins repo |
| **ZCode** (Z.ai / GLM) | `~/.zcode/skills/<n>/SKILL.md` | none | `$kerbe-audit` | **no mechanism** — users *import* from Claude Code / Codex / OpenClaw / Augment / Windsurf, as symlink or copy |
| **Gemini CLI** | `skills/` | `gemini-extension.json` (`contextFileName: GEMINI.md`) | — | extension install |
| **Pi** | `package.json` → `pi.skills`, `pi.extensions`; keyword `pi-package` | `package.json` | — | npm-shaped |
| **opencode** | `.opencode/plugins/<n>.js` via `package.json` `main` | `package.json` | — | npm-shaped |

**Reference implementation already on disk:** superpowers 6.2.0 ships one `skills/` tree plus
`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `gemini-extension.json`, `package.json` (`pi` + opencode
keys), `.codex-plugin/`, `scripts/package-codex-plugin.sh` and
`scripts/sync-to-codex-plugin.sh`. Read it at
`~/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/` before designing anything
here — it is the same problem, already solved once.

#### What actually differs per harness (the content of a harness adapter)

1. **Subagent tool names — the single biggest portability risk.** Claude Code's `Agent` tool
   with `isolation: "worktree"` has no direct equivalent. Codex uses `spawn_agent` /
   `wait_agent` / `close_agent`, and only when `[features] multi_agent = true` is set in
   `~/.codex/config.toml`. This hits `implement` hardest, then `coverage` (parallel adversarial
   verifiers) and `review` (fresh-context critic).
2. **Isolation primitives.** Git worktrees may be unavailable: a Codex sandbox can be a detached
   HEAD in an externally managed worktree that cannot branch or push. Superpowers'
   `references/codex-tools.md` documents the read-only detection probe
   (`git rev-parse --git-dir` vs `--git-common-dir`, `git branch --show-current`) and the
   "commit + hand off to local" fallback. Reuse it; don't re-derive it.
3. **Context file name.** `CLAUDE.md` vs `AGENTS.md` vs `GEMINI.md`.
4. **Invocation + namespacing.** `/plugin:skill` vs `$skill-name`.
5. **Hooks.** SessionStart hooks and similar are harness-specific; treat as optional
   enhancement, never load-bearing.

#### AGENTS.md is canonical — decide this now, not at publish time

`AGENTS.md` was formalised as an open spec in Aug 2025 (OpenAI with Google, Cursor, Factory,
Sourcegraph) and **donated to the Linux Foundation's Agentic AI Foundation in Dec 2025** —
60,000+ repos and 20+ tools. Claude Code is the notable holdout, still reading `CLAUDE.md`.

**So: author `AGENTS.md` and symlink `CLAUDE.md` → `AGENTS.md`.** This is exactly the policy the
existing `sync-agent-md` user skill implements (though inverted — it makes CLAUDE.md canonical),
and it is what ZCode's own docs recommend. Kerbe should invert `sync-agent-md`'s direction,
because a published multi-harness plugin has the broader standard as its centre of gravity, not
Claude. **Getting this right on day one is free; retrofitting it is a rewrite.**

### The pivot vocabulary: artifact kinds

The seam only works if both stacks map onto one shared noun set. This is the core design
artifact of the whole refactor.

| Artifact kind | Symfony | Flutter |
|---|---|---|
| screen | Twig template + Controller action | Screen widget + route |
| navigation edge | `path()`, `redirectToRoute()` | `go()` / `Navigator.push` / deep link |
| data model | Doctrine Entity + migration | freezed / json_serializable model |
| data access | Repository | Repository / DataSource / API client |
| **app state** | *(none — request-scoped)* | Provider / Bloc / Riverpod notifier |
| form | Symfony FormType | Form widget + validators |
| permission boundary | `#[IsGranted]`, `security.yaml` | route guard + platform permission + secure storage |
| acceptance test | PHPUnit Functional | widget test (`flutter test`) |
| e2e test | Panther | `integration_test` |
| style token | SCSS variable / palette | `ThemeData` / design token |
| **schema migration** | Doctrine migration | *(server-side, or local Drift/Isar)* |
| **platform channel** | *(n/a)* | MethodChannel |

Asymmetries are **declared, never smoothed over** — an adapter states which kinds it supports
and which are `n/a`, reusing `sdlc-scaffold`'s existing `generated`/`exists`/`n/a` disposition
discipline. Kinds Flutter adds (app state, platform channel, platform parity, offline/sync,
store-release gates) get their own doc-set extensions.

### Portability triage

| Skill | Lifecycle % | Verdict |
|---|---|---|
| `flowmap` | ~95% | Free port. Already abstract: "screens as nodes, edges keyed by route name". |
| `help` | ~90% | Free once paths are config-driven. Strip the ECS/cron appendix to integration. |
| `split` | ~90% | Free. Only test command + container name are stack-bound. |
| `coverage` | ~85% | Relay logic is universal; "existence ≠ wired" checks become adapter recipes. |
| `audit` | ~70% | Core fine; the 5 audit targets become artifact-kind lookups. |
| `start` | ~70% | Doc-set becomes adapter-declared; templates move out of the skill body. |
| `plan` | ~60% | Must be made standalone first (Phase 1). |
| `implement` | ~55% | Worktree/Docker/DB standup → adapter `commands.md` + env recipe. |
| `bug` | ~40% | Method is universal; every checklist row is Doctrine-specific. |
| `scaffold` | ~20% | Mostly templates = mostly adapter. Keep the manifest contract in the skill. |
| `review` | ~20% | Tier *concept* invariant; every classification rule stack-specific. |
| `figma` | integration | Whole skill is one integration adapter. |
| `monday` | integration | Whole skill is one integration adapter. **Private.** |

---

## Phase 1 — Hygiene (fixes defects that exist regardless of publishing)

Do these on the `sdlc-*` suite **before** copying, so Kerbe starts from a correct base. These
are the only edits this project makes to the old suite; after Phase 1 it is frozen.

### 1.1 Retire `slice-start`

Confirmed by git history in `~/.claude`: `slice-start` was committed **2026-04-24** in one
commit and never touched again; `sdlc-start` appeared **2026-05-25** and evolved through
**2026-06-30**. `sdlc-start` still carries `slice-start`'s H1 (`# Slice Start Skill`) and
opening line verbatim.

Both are active, both trigger on the phrase `/slice-start`, and both claim authority over
`INDEX.md` with **different** lifecycle rules.

- [ ] Port back the three mechanics `sdlc-start` dropped, if still wanted:
  - [ ] pre-fill from a feature file (`slice-start:35`)
  - [ ] copy from `_templates/` instead of inlining templates *(becomes the adapter mechanism
        anyway — see 3.3, so this one resolves itself)*
  - [ ] the `SCOPE.md` `## Lifecycle` table-append rule + "advancing to `scoped` locks SCOPE.md
        above the Scope Change Log"
- [ ] Delete `~/.claude/skills/slice-start/`
- [ ] Fix `sdlc-start:48` and `:279` — both say *"If the user runs `/slice-start`…"*
- [ ] Replace the inherited H1 and the client-named opening line

**Acceptance:** one skill owns slice creation; nothing in the suite mentions `/slice-start`.

### 1.2 Break the superpowers hard dependency

`sdlc-implementation-plan:16` declares **"REQUIRED SUB-SKILL: `superpowers:writing-plans`"** and
contains **zero** plan-authoring instruction — 63 lines of naming/location override around
someone else's skill. Without superpowers, lifecycle step 5 has no content, and step 6 has
nothing to consume because `PLAN.md` is its declared task source (`sdlc-implement:16`).

Soft: `sdlc-implement:82,89` names `superpowers:subagent-driven-development` and
`superpowers:executing-plans`. The parallel path is self-contained (built-in `Agent` tool,
`isolation: "worktree"`); the sequential path is a dangling reference.

- [ ] Inline a minimal plan-authoring spec: required header, file-structure map, right-sized TDD
      tasks, bite-sized steps with real commands + expected output, self-review pass. (The
      skill's own Overview already *describes* this structure — it just delegates the content.)
- [ ] Gate the delegation: *"if `superpowers:writing-plans` is available use it and apply the two
      overrides; otherwise follow the inline spec."*
- [ ] Same for `sdlc-implement`'s two named execution modes
- [ ] Keep the override paragraphs (`sdlc-implement:188–189`,
      `sdlc-implementation-plan:32–38`) but mark them *"applies only when superpowers is
      installed"*
- [ ] README: document the interaction — superpowers' SessionStart hook injects a skill-priority
      rule (process skills first) that can pull `superpowers:brainstorming` ahead of
      `kerbe:start` on a fresh feature. Usually desirable; must be stated.

**Acceptance:** the full 7-step lifecycle completes with superpowers uninstalled. Test it, don't
read it.

### 1.3 Carry over the `CLAUDE.md` rules that don't survive export

**Must be inlined into skill bodies:**

- [ ] **Pathspec-scoped commits** — `git commit -m "…" -- path/to/file`. The strongest git safety
      rule in the global config and **no skill carries it**. Needed by `coverage` (commits every
      round), `split`, `figma`, `scaffold`. Include the why: the git index is shared per-repo
      across concurrent sessions, so a bare commit sweeps up another session's staged work.
- [ ] **`claude-progress.md` + no-hidden-dotfolder-scratch** — well restated in
      `sdlc-implement:188–189`, but `sdlc-audit:199` and `sdlc-implementation-plan:37` only say
      "project rule" and point nowhere. Make each self-contained.
- [ ] **Context guidance** — compact at ~50%. Matters most for `coverage`'s multi-round loops.

**README-documented, adapter-supplied, or no action:**

- [ ] `<task-complete/>` / `<waiting-for-user/>` sentinels → README
- [ ] Docker port policy (never 8080, 8100+) → adapter env recipe
- [ ] MySQL 8.4 / `serverVersion=8.4` → Symfony adapter
- [ ] `git add` one file at a time → **already correctly restated** in `sdlc-scaffold:379`,
      `sdlc-implement:159`, `sdlc-split:24`. No action.
- [ ] Python venv rule → **no action.** Verified both script sets import stdlib only
      (`json os re subprocess sys argparse urllib.request datetime pathlib`). Note as a
      portability win in the README.

**Acceptance:** a fresh clone with no `~/.claude/CLAUDE.md` runs safely with no dangling refs.

**→ `sdlc-*` is now FROZEN. Everything below happens in `~/projects/kerbe/`.**

---

## Phase 2 — Plugin scaffold, config seam, adapter contract

### 2.1 Repo skeleton

- [ ] `git init`; `.claude-plugin/plugin.json` + `marketplace.json`; `LICENSE`; README stub
- [ ] Verify local dev install works: `/plugin marketplace add ~/projects/kerbe`

**Two harness-neutrality disciplines, adopted now because retrofitting them costs a rewrite
(see §0 "second axis"):**

- [ ] **`AGENTS.md` is canonical; `CLAUDE.md` is a symlink to it.** Not the reverse.
- [ ] **No harness tool names in skill bodies.** Write the *intent* — "dispatch a subagent per
      task, isolated from the main context" — and put the mechanism (`Agent` tool with
      `isolation: "worktree"` / `spawn_agent`+`wait_agent`+`close_agent` / inline fallback) in
      `adapters/harness/<name>/tools.md`. Today's `sdlc-implement:143–152` embeds a literal
      `Agent({...})` call; that is exactly the shape to avoid carrying over.
- [ ] Grep guard to keep it honest:
      `grep -rniE "Agent\(|isolation:|spawn_agent|TaskCreate" skills/` should only ever match
      inside `adapters/harness/`

### 2.2 `kerbe.config.md`

Config, **not** working state — so not a violation of the no-hidden-folder rule, which targets
progress ledgers, task briefs and agent scratch. Repo root, visible.

```markdown
# Kerbe Config
stack: symfony | flutter | <adapter name>
integrations: [figma, monday]         # or []
planning_root: planning/<product>/slices
app_root: symfony                     # or lib
worktree_root: ~/projects
worktree_prefix: <project>-
branch_prefix: slice/
review_prefix: review/
base_branch: origin/review/main
planning_branch: <branch planning docs live on>
timezone: Pacific/Auckland
editor_command: phpstorm --line {line} {file}
```

- [ ] Resolution order: explicit arg → config → adapter default → ask once, offer to write it in
- [ ] Absent config is **not** fatal — degrade to defaults + one clarifying question

### 2.3 Adapter contract — pressure-tested by stubbing BOTH adapters

```
adapters/stack/<name>/
├── ADAPTER.md        # identity, detection heuristic, supported kinds (+ n/a list)
├── layout.md         # source root per artifact kind
├── doc-set.md        # which planning docs apply, names, stack-specific extensions
├── scaffold.md       # generation template per artifact kind
├── risk-tiers.md     # tier 1/2/3 classification rules
├── commands.md       # test / single-test / lint / build / migrate / run
└── verify.md         # "exists AND is wired" recipes per kind
```

- [ ] Author `adapters/ADAPTER_CONTRACT.md`
- [ ] **Stub BOTH adapters against it before filling either in** — write `ADAPTER.md`,
      `layout.md` and `doc-set.md` for `symfony/` *and* `flutter/`, leaving `scaffold.md`,
      `verify.md`, `risk-tiers.md`, `commands.md` empty. This is the cheap, *real* pressure test:
      any field Flutter cannot express means the contract is Symfony-shaped and must widen now.
- [ ] Same contract shape for `adapters/integration/<name>/`: capability, token resolution,
      commands, output format
- [ ] **Freeze the contract**, and adopt the change protocol: a change forced by one stack
      updates the other adapter in the same commit + re-runs the baseline comparison

**Acceptance:** two stubbed adapters both satisfy the contract, and no field exists that only
one stack can express.

---

## Phase 3 — Both adapters, concurrently

Two tracks run in parallel against the frozen contract. **Track A** is extraction — mechanical,
low-risk, grinding. **Track B** is discovery — thinking, done inside the real mobile build.
Interleave them as attention allows; neither blocks the other. The contract-change protocol
(2.3) governs every collision between them.

Running underneath both: the **continuous baseline comparison** (3.C), which is what makes
concurrent work diagnosable rather than confusing.

---

### Track A — Symfony adapter, extracted by copy

Extraction, not rewrite. The value is the ~2 months of hard-won specificity already encoded.
Source files are read-only.

#### A.1 Extract

- [ ] `scaffold.md` ← `sdlc-scaffold` §§1–6 (entity / repository / controller / form / test /
      migration templates, all conventions and rules)
- [ ] `risk-tiers.md` ← `sdlc-code-review` Step 3 table + the four "project-specific rules"
      (generalise the rules, drop the client name)
- [ ] `commands.md` ← the `docker exec <container> …` family from project `CLAUDE.md`
      + `sdlc-split:88` + `sdlc-bug:77,80`, parameterised on container name
- [ ] `layout.md` ← the `symfony/**` path set
- [ ] `verify.md` ← `sdlc-coverage` Step 5 failure modes (stub, unimported stylesheet,
      class-name mismatch, dead link, unwired route, importmap gap, entity/field drift)
- [ ] `doc-set.md` ← `sdlc-start` Phase 1 + Phase 2 doc sets and the tailoring rules
- [ ] Move project-`CLAUDE.md` couplings here rather than dropping them:
      `mhpdigital/cross-tenant-security-bundle` traits (`sdlc-scaffold:165,191`),
      `getBlockPrefix(): ''` as a tier-1 signal (`sdlc-code-review:57`),
      `RequestStack`-not-`Request` + method-level DI (`sdlc-scaffold:258–259`,
      `sdlc-implement:156`), datetime columns without `_at` (`sdlc-scaffold:149–150`),
      `ConfirmActionType` (`sdlc-scaffold:301`), `_test` DB suffix + `symfony/test` kernel env
      + shared `KernelBrowser` (`sdlc-scaffold:319–338`), `.env` not `.env.local`,
      `symfony/migrations/CLAUDE.md` (`sdlc-bug:43`)
- [ ] The cross-tenant bundle is a **third-party dependency** —
      `github.com/mhpdigital/cross-tenant-security-bundle`, public, but not something a stranger
      will already have or necessarily want. The adapter must state the dependency explicitly
      and offer a plain-Doctrine fallback template.

#### A.2 De-hardcode every path

- [ ] **`planning/<product>/slices/…` — 21 occurrences across 9 skills**, the load-bearing
      assumption of the entire suite → `{planning_root}/{slice}/`
- [ ] `symfony/src/{Entity,Repository,Controller,Form}/`, `symfony/templates/`,
      `symfony/tests/Functional/`, `symfony/migrations/` → artifact-kind lookups
- [ ] `~/projects/<prefix>-{slice-id}` + `<db-prefix>_{slice}` DB naming (`sdlc-implement:31,49,60`)
      → `{worktree_root}/{worktree_prefix}{slice}`
- [ ] Branch conventions, `origin/review/main`, planning-branch default `review/<planning-branch>`,
      `sdlc-code-review`'s diffs-vs-`master` → config
- [ ] `docs/flows/` → config key
- [ ] `phpstorm --line N /abs/path` on every review row → `editor_command` template; must work
      for VS Code, Android Studio, Xcode
- [ ] Tooling that exists nowhere else: `bin/check-figma-freshness.py`
      (`sdlc-figma`, `sdlc-coverage`), `scripts/slice-metrics/collect.py` (`sdlc-split`) →
      vendor into the plugin, or degrade gracefully **and say so** (`sdlc-coverage:107` already
      models this: "flag the missing tooling as a vendoring gap")

#### A.3 Thin the skills to lifecycle

- [ ] Each skill: read config → load only the adapter files it needs → apply
- [ ] Move `sdlc-start`'s inlined doc templates out to the adapter's `doc-set.md` — this is
      `slice-start`'s original `_templates/` idea, restored properly
- [ ] Strip `sdlc-help:147–162` (ECS / EventBridge / review-environment) to integration
- [ ] Preserve every lifecycle invariant **verbatim** — the suite's real IP: scaffold's
      non-skippable manifest contract; audit's artifact decomposition + un-pre-fillable
      human-verification questions + 4-digit review codes; coverage's two-triangle relay,
      cumulative-count semantics and two-consecutive-clean-rounds convergence rule; audit's
      scope-conflation guard; split's 10-signal smell score

**Acceptance:** `grep -rn "planning/<product>\|symfony/src\|~/projects/<prefix>" skills/` is
empty; every SKILL.md is stack-neutral and materially shorter; no capability lost.

---

### Track B — Flutter adapter, written during the real mobile build

Discovery work, done inside the actual app build rather than speculatively. Starts as soon as
the contract is frozen — it does **not** wait on Track A finishing.

#### B.1 Cheapest first: flowmap

- [ ] Port `flowmap` (~95% lifecycle already). Node key = GoRouter route name; template-only
      screens = `tpl_<slug>`. Edges: `go()` / `push()` / `pop()`, declarative redirects, deep
      links, and the mobile analog of the skill's own documented blind spot — **navigation
      callbacks passed into widgets**, which no route-table parse will find.
- [ ] Generate and commit a real `.flow` baseline for the app
- [ ] Confirm the regeneration contract still yields byte-stable diffs

#### B.2 The adapter

- [ ] `ADAPTER.md` — detection: `pubspec.yaml`. Declare supported kinds + `n/a`s (server-side
      migration → `n/a`)
- [ ] `layout.md` — `lib/{models,screens,widgets,repositories,providers,services}/`, `test/`,
      `integration_test/` — match the app's actual structure, don't impose one
- [ ] `commands.md` — `flutter test`, `flutter test <file>`, `flutter analyze`,
      `dart format --set-exit-if-changed`, `flutter build {apk,ipa}`, `flutter run -d <device>`
- [ ] `risk-tiers.md`:
  - **tier 1** — auth flows, secure storage, API clients + token refresh, state
    notifiers/reducers, permission requests, platform channels, any crypto or PII handling
  - **tier 2** — screen widgets, routing config, DI/provider wiring, serialization setup
  - **tier 3** — pure presentation widgets, theme/tokens, **generated code** (`*.g.dart`,
    `*.freezed.dart`), asset declarations, l10n ARB files
- [ ] `verify.md` — Flutter's "exists ≠ wired" family: a screen with no route entry; a route no
      edge reaches; a provider never watched/read; an asset in `pubspec.yaml` never referenced
      (and the reverse); a permission used in code but absent from `Info.plist` /
      `AndroidManifest.xml`; generated code stale vs its source annotation; an un-awaited
      `Future`
- [ ] `scaffold.md` — model, repository/data source, screen widget + route registration, form +
      validators, widget test stub, integration test stub
- [ ] `doc-set.md` — reuse SCOPE / UI_ELEMENTS / DONE_CRITERIA / REQUIREMENTS / TIMING; add the
      mobile-only docs the artifact-kind table exposes as gaps:
  - [ ] `NAVIGATION.md` replaces `ROUTES.md` (route table, deep links, guards)
  - [ ] `STATE.md` — new kind, no Symfony analog
  - [ ] `PERMISSIONS.md` replaces `SECURITY.md` (platform permissions, secure storage, API
        auth, certificate handling)
  - [ ] `PLATFORM.md` — iOS/Android parity, min OS versions, store-release gates
  - [ ] `OFFLINE.md` if the app syncs

#### B.3 Run one real slice end to end

- [ ] Drive one genuine Flutter feature slice through all 7 steps
- [ ] Log every friction point and sort it honestly into **adapter gap** vs **bad abstraction**

#### B.4 Honest expectation

Symfony arrives with two months of accumulated specificity. Flutter starts empty and only gets
good through use. Expect the first Flutter slice to be **slower** than doing it unassisted; the
payoff starts at slice two. Budget for it rather than being surprised.

---

### 3.C Continuous baseline comparison (runs throughout Phase 3)

Not a one-time gate — a standing check, available as often as wanted, because the frozen
`sdlc-*` suite is sitting right there.

- [ ] Whenever a Symfony slice runs through Kerbe, also run the frozen `sdlc-*` equivalent and
      diff the outputs artifact by artifact: audit report, scaffold manifest, review tiers,
      coverage matrix
- [ ] Keep a running comparison log in the repo (`BASELINE_LOG.md`) — date, slice, skill,
      match/divergence, cause
- [ ] Re-run after **every** contract change (per the 2.3 protocol)

**This is the diagnostic that makes concurrent tracks safe:**

| Symptom | Diagnosis | Fix in |
|---|---|---|
| Symfony-via-Kerbe ≠ Symfony-via-`sdlc-*` | extraction bug | Track A |
| Symfony matches baseline, Flutter painful | contract gap or Flutter adapter gap | contract, or Track B |
| Both stacks awkward in the same place | the lifecycle skill itself is wrong | `skills/` |

**Phase 3 exit criteria (all three):**

1. Symfony matches the baseline on at least two real slices
2. One real Flutter slice completes all 7 steps
3. Both stacks run from the same skills with only the `stack:` config line differing

---

## Phase 4 — Retire `sdlc-*`

- [ ] Add `kerbe.config.md` to the reference project's repos (`stack: symfony`)
- [ ] Run one further reference-project slice on Kerbe only
- [ ] Delete `~/.claude/skills/sdlc-*` (it's in git in `~/.claude` — recoverable)
- [ ] Freeze rule ends; single suite from here

---

## Phase 5 — Scrub for public release

Nothing found is a leaked credential — all tokens resolve at runtime. But client and
infrastructure identification appears in **12 of 14 files**. Most of it never reaches Kerbe if
Phase 3 is done properly; this phase is the audit that confirms it.

### 5.1 Tier 1 — must not ship

- [ ] **The client's product name (two forms) and `<legacy-app>`** — 12 of 14 files; both
      `-start` skills *open* with "the &lt;product&gt; rebuild slice system"
- [ ] **`<pm-dashboard-host>`** — live client hostname
      (`sdlc-monday-review:83`)
- [ ] **monday.com board IDs `<board-id>` ×2**, group IDs,
      column IDs — live handles into the client's board
      (`monday_sync.py:31–50`)
- [ ] **AWS SSM `/<project>/figma/api-token`**, profile `<aws-profile>`, region `<region>`
      (`sdlc-figma/SKILL.md:12`, `config.py:16–18`)
- [ ] `~/projects/<repo>/symfony/.env`, `~/projects/<planning-repo>/…`
      (`sdlc-monday-review:24,124`, `monday_sync.py:28–29`)
- [ ] **`mhpdigital/…`** vendor namespace → Symfony adapter, explicitly declared
- [ ] **Seven real slice/branch names used as worked examples** (see the local scrub sheet)
      (`sdlc-code-review:190,211`; `sdlc-flowmap:89–92`; `sdlc-implement:57`)
- [ ] Client design internals: `<component-set>` "still uses `Property 1`" (`sdlc-figma:102`),
      the `.card-share`/`.card-email` bug family (`sdlc-coverage:101,161`), `<FEATURE>_PLAN.md`
      (`sdlc-coverage:65`)
- [ ] `app:<scheduled-command>` + ECS review-environment topology (`sdlc-help:147–162`)

Replace each with a neutral invented example that still teaches the lesson. The class-mismatch
anecdote in `sdlc-coverage:101,161` — where the template renders one class and the SCSS defines a
differently-named one — is genuinely instructive and must survive the scrub; carry it over as
`.card-share` vs `.card-email`.

### 5.2 Hold back monday.com

Its value is almost entirely the board IDs, column IDs, `LABEL_TO_SLICE` mapping and the
`PmReader::getSliceFeedback()` output contract. A scrubbed version is an empty shell.

- [ ] Keep monday.com as a **private** adapter (separate repo or unpublished directory)
- [ ] Ship **`github-issues`** as the public reference integration — demonstrates the interface
      with zero client exposure and is immediately useful
- [ ] Document the integration contract so Jira / Linear adapters are writable by others

### 5.3 Requirements + framing

- [ ] `## Requirements` / `## Configuration` block on every skill
- [ ] README lists the `CLAUDE.md` rules the suite expects (1.3)
- [ ] README **names the stack coupling honestly**: a slice-based SDLC toolkit with Symfony and
      Flutter adapters, not a framework-agnostic suite. Only `help`, `split`, `flowmap` and
      largely `coverage` are genuinely stack-neutral.

---

## Phase 6 — Publish

### 6.1 Names are immutable

The marketplace `name` is an immutable slug; renaming after publish breaks every install with
`plugin-not-found`. `displayName` changes the UI label; a top-level `renames` map
(`{"old": "new"}`) auto-migrates on next sync — the official directory uses it for six plugins.
Escape hatches, not a plan.

- [ ] Slug frozen: **`kerbe`**. Skill names frozen (users build muscle memory on them).

### 6.2 Package

- [ ] **Pick the licence** (see 6.2a below) and declare it in *both* `LICENSE` and
      `plugin.json`'s `license` field
- [ ] `plugin.json` — `name`, `description`, `version` (semver), `author`, `homepage`,
      `repository`, `license`, `keywords`
- [ ] `marketplace.json` — `$schema`
      `https://anthropic.com/claude-code/marketplace.schema.json`, `name`, `owner`,
      `plugins: [{ name, source: "./", category: "development", description, tags }]`
- [ ] README — install, config, adapter-authoring guide, superpowers interaction, CLAUDE.md
      expectations, stack-coupling disclosure
- [ ] Verify: `/plugin marketplace add mhpdigital/kerbe` → `/plugin install kerbe@kerbe`

### 6.2a Licence — what the ecosystem actually uses

Surveyed from disk, not guessed:

| Publisher | Licence |
|---|---|
| Anthropic's ~40 internal plugins in the official directory | **Apache-2.0**, near-uniformly |
| superpowers (largest community skill library) | **MIT** |
| claude-hud | **MIT** |

Both are safe, permissive, and OSI-approved. The split:

- **MIT** — community norm for skills, shortest, zero friction, maximum adoption.
- **Apache-2.0** — adds an express patent grant, a trademark clause, and a `NOTICE` file. The
  convention when a company publishes under its own name.

### DECIDED: MIT

`LICENSE` is **MIT** (`Copyright (c) 2026 mhpdigital`), committed as the repo's root commit.
This matches the skills-ecosystem norm — superpowers and claude-hud are both MIT — and
prioritises frictionless adoption over the patent/trademark protection Apache-2.0 adds.

- [x] Licence chosen and committed
- [ ] Declare it in `plugin.json`'s `license` field too: `"license": "MIT"`
- [ ] Add the MIT header expectation to any future contributor guidance
- [ ] **No dual-licensing** (e.g. MIT for code + CC-BY for prose). Skills blur the code/prose
      line constantly, so a split creates a boundary nobody can adjudicate. One licence, whole
      repo.
- [ ] Do not revisit after third parties fork — relicensing then is painful and sometimes
      impossible.

### 6.3 Self-publish first — no approval needed

A public GitHub repo with `marketplace.json` is immediately installable by anyone given the repo
name. **No review, no gatekeeper, no Anthropic involvement.** This is how most plugins,
including superpowers, reach their users.

- [ ] Publish; install on a clean machine as a stranger would
- [ ] Run **both** stacks from the installed copy, not from `~/.claude/skills/`

### 6.4 Optional: official directory

`anthropics/claude-plugins-official` — 276 entries as of this machine's last sync (2026-07-29).

- [ ] Submit via the form **`https://clau.de/plugin-directory-submission`** (**not** a PR)
- [ ] Expect *"External plugins must meet quality and security standards for approval."* No
      published rubric or SLA. Anthropic-internal plugins live in `/plugins`, third-party in
      `/external_plugins`.
- [ ] Understand what a listing is: a **pointer**. The entry references your repo by `url` plus
      a **pinned `sha`** (e.g. Adobe's pins `17ef6fb53d…`). **Pushing to `main` does NOT reach
      directory users until the sha is bumped.** Your own marketplace can track a branch —
      consider self-hosted as the fast channel, the directory as discovery.

### 6.5 Version tracking — three independent layers

1. **You own semver** in `plugin.json` `version` (superpowers is at `6.2.0`). Nothing enforces
   it; it's your declaration.
2. **The marketplace entry pins a commit** — `source: { url, ref, sha }`.
3. **The client records the install** — `~/.claude/plugins/installed_plugins.json` stores
   per-install `version`, `gitCommitSha`, `installedAt`, `lastUpdated`, `scope`; the cache path
   is version-segmented (`…/cache/<marketplace>/<plugin>/<version>/`). This is what makes
   rollback and "which version am I on" answerable.

- [ ] Policy: **minor** for a new adapter, **patch** for adapter content fixes, **major** for a
      lifecycle or config-format break
- [ ] Keep `RELEASE-NOTES.md` (superpowers does; it's the norm for skill plugins)
- [ ] Remember there is **no `dependencies` field** — the superpowers relationship can only be a
      README instruction plus the runtime check from 1.2

---

## Phase 7 — Publish to other harnesses

Deliberately **after** Claude Code ships. One harness proven end-to-end beats four
half-working. The Phase-2 disciplines (`AGENTS.md` canonical, no tool names in skill bodies) are
what make this phase cheap instead of a rewrite — everything here is additive manifests plus one
adapter file per harness.

### 7.1 Harness adapter contract

- [ ] `adapters/harness/ADAPTER_CONTRACT.md` — mirrors the stack contract:

```
adapters/harness/<name>/
├── HARNESS.md     # identity, skill install path, invocation syntax, context filename
├── tools.md       # subagent dispatch, isolation, file ops — mechanism per intent
└── limits.md      # what this harness cannot do + the documented fallback
```

- [ ] **Degradation ladder** for subagent dispatch, declared once and referenced by every skill
      that fans out (`implement`, `coverage`, `review`):
      **parallel isolated** → **sequential subagents, shared tree** → **inline in main context**.
      Each harness adapter states the highest rung it can reach. A harness at the bottom rung
      still runs the whole lifecycle — just slower and with more context pressure. Never let a
      missing primitive block a skill outright.

### 7.2 Codex CLI

Closest to Claude Code; skills landed Dec 2025 and the format is compatible.

- [ ] `.codex-plugin/` manifest; `skills/*/agents/openai.yaml` per skill (`interface.display_name`,
      `short_description`, `default_prompt` — see `~/.claude/skills/sync-agent-md/agents/openai.yaml`
      for the shape)
- [ ] `adapters/harness/codex/tools.md` — `spawn_agent` / `wait_agent` / `close_agent`, and the
      `[features] multi_agent = true` prerequisite in `~/.codex/config.toml`
- [ ] `limits.md` — sandbox detached-HEAD detection and the "commit, then hand off to local"
      fallback. **Copy superpowers' `references/codex-tools.md` probe verbatim**; it is correct
      and hard-won.
- [ ] Packaging: adapt `scripts/package-codex-plugin.sh` (rootless archive: `.codex-plugin/`,
      `skills/`, `README.md`, `LICENSE` at archive root; other harnesses' manifests excluded)
- [ ] Verify: install into `~/.codex/skills/`, run one full lifecycle on the Symfony stack

### 7.3 ZCode (Z.ai / GLM)

- [ ] **No plugin or marketplace mechanism exists** — so there is nothing to publish. Users
      *import*: ZCode natively imports skills from Claude Code, Codex, OpenClaw, Augment and
      Windsurf, either as symlinks (tracking source changes) or independent copies.
- [ ] Deliverable is therefore **documentation, not packaging**: a README section covering
      `~/.zcode/skills/<name>/SKILL.md`, `$kerbe-audit` invocation, and the import path
- [ ] `adapters/harness/zcode/limits.md` — confirm subagent support before promising the top
      rung of the degradation ladder; assume sequential until proven otherwise
- [ ] Because import-as-symlink follows the source, a ZCode user tracking a Claude Code install
      gets updates for free — note that in the README as the recommended route

### 7.4 Gemini CLI, Pi, opencode (opportunistic)

Cheap once the above exists; superpowers has a working manifest for each.

- [ ] Gemini CLI — `gemini-extension.json` (`{name, description, version, contextFileName}`) +
      `GEMINI.md`
- [ ] Pi — `package.json` with `pi.skills` / `pi.extensions` and the `pi-package` keyword
- [ ] opencode — `.opencode/plugins/kerbe.js` referenced from `package.json` `main`
- [ ] Only claim support for a harness after running **one real slice** on it. An untested
      manifest in the repo is a promise you haven't kept.

### 7.5 Keep the harnesses honest

- [ ] One canonical `skills/` tree — **never** fork skill content per harness. Divergence here
      is the same failure mode as the `sdlc-*` freeze rule guards against.
- [ ] CI (or a documented manual check) that every harness manifest still enumerates every skill
- [ ] README support matrix: harness × tested/untested × degradation rung reached
- [ ] Version bump policy extends to harnesses: **minor** for a new harness adapter, same as a
      new stack adapter

---

## Sequencing summary

| Phase | Depends on | Deliverable |
|---|---|---|
| 1 Hygiene | — | one slice-creation skill; superpowers-optional; git/context rules inlined. **Then `sdlc-*` freezes.** |
| 2 Scaffold + contract | 1 | repo, `kerbe.config.md`, contract pressure-tested by stubbing **both** adapters, then frozen |
| **3 Both adapters (concurrent)** | 2 | **A:** Symfony extracted by copy, zero hardcoded paths, skills thinned · **B:** Flutter adapter written during the real build · **C:** continuous baseline comparison + `BASELINE_LOG.md` |
| 4 Retire `sdlc-*` | 3 | single suite; freeze rule ends |
| 5 Scrub | 4 | publishable content; `github-issues` adapter; monday held back |
| 6 Publish (Claude Code) | 5 | licence chosen; self-hosted marketplace, then optional directory submission |
| 7 Other harnesses | 6 | harness adapter contract + degradation ladder; Codex packaged; ZCode documented; Gemini/Pi/opencode opportunistic |

**Two decisions belong in Phase 2 even though they only pay off in Phases 6–7:** `AGENTS.md` as
the canonical context file, and zero harness tool names in skill bodies. Both are free now and a
rewrite later.

Phases 1–3 are worth doing **even if publishing never happens** — they fix a live skill
collision, a hard dependency on a third-party plugin, and a missing git safety rule.

**Phase 3 is the decision point.** Exit criteria met → the plugin is worth publishing.
Persistent divergence between the two adapters, or a contract that keeps needing to widen →
the honest outcome is a well-factored private Symfony suite plus a separate Flutter suite,
which is still better than today. Decide on the evidence in `BASELINE_LOG.md`, not on sunk cost.
