# kerbe:coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `kerbe:coverage` plugin skill — inventory-first, pairwise-hop missing-functionality review — with its verdict script, design/stack adapters, and a planted-gap fixture harness that becomes the skill's permanent acceptance test.

**Architecture:** Two-phase skill: EXTRACT builds a frozen promise ledger (`PROMISES.md`, one leaf-level promise per row) from config-declared sources; VERIFY fills the pairwise hop columns (design→spec→plan→code) per row with evidence; `verdict.py` computes the verdict from the ledger — no agent ever asserts completeness. Project specifics live in `kerbe.yml` + design/stack adapters, never in the skill body.

**Tech Stack:** Claude Code plugin (`.claude-plugin/plugin.json`, `skills/coverage/SKILL.md`), Python 3 stdlib only (`verdict.py`, `figma_cache.py`, `fixtures/score.py`), `unittest` for tests.

**Spec:** `docs/specs/2026-08-20-coverage-skill.md` — the plan argues from it; read it first.

## Global Constraints

- **This repo is PUBLIC.** No client-identifying strings (a pre-commit guard enforces a denylist). Fixture content uses invented domain words ("cards", "gallery"). Real values map via the gitignored `SCRUB_TARGETS.local.md`.
- **Python:** stdlib only, `python3`, no pip installs. Scripts are executable (`chmod +x`) with `#!/usr/bin/env python3`.
- **Never use these exact strings in any new file or subagent prompt** (a legacy PreToolUse hook on this machine pattern-matches them): the legacy skill's hyphenated name, `COVERAGE_REVIEW.md`, `REVIEW_STATUS`, "coverage convergence loop". The new artifacts are named `PROMISES.md`, `OUT_OF_SCOPE.md`, and the phrase is "extraction passes".
- **Git:** stage files one by one; every commit scoped with `-- <paths>`; commit messages end with the Claude Code co-author line.
- The frozen legacy suite in `~/.claude/skills/` is **never edited or invoked**.
- Ledger cells must not contain `|` characters (the parser is a pipe-table split).

---

### Task 1: Plugin scaffold

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`
- Create: `README.md`

**Interfaces:**
- Produces: plugin name `kerbe` (skills invoke as `/kerbe:<skill>`); repo layout `skills/`, `adapters/`, `fixtures/`, `docs/`.

- [ ] **Step 1: Write `.claude-plugin/plugin.json`**

```json
{
  "name": "kerbe",
  "displayName": "Kerbe",
  "description": "Portable slice-based SDLC skills with stack and design adapters. First skill: coverage — inventory-first missing-functionality review.",
  "version": "0.1.0",
  "author": { "name": "MHP Digital" },
  "license": "MIT",
  "homepage": "https://github.com/jochendaum/kerbe"
}
```

- [ ] **Step 2: Write `.claude-plugin/marketplace.json`**

```json
{
  "name": "kerbe-marketplace",
  "owner": { "name": "MHP Digital" },
  "plugins": [
    { "name": "kerbe", "source": "./", "description": "Portable slice-based SDLC skills with stack and design adapters." }
  ]
}
```

- [ ] **Step 3: Write `README.md`**

Content: one-paragraph description (from plugin.json description), install hint (`claude plugin` local install pointing at the repo), a section "Skills" listing `kerbe:coverage` with a two-line summary and a pointer to `docs/specs/2026-08-20-coverage-skill.md`, and a section "Repository layout" listing `skills/`, `adapters/`, `fixtures/`, `docs/`.

- [ ] **Step 4: Validate the JSON parses**

Run: `python3 -c "import json;[json.load(open(f)) for f in ['.claude-plugin/plugin.json','.claude-plugin/marketplace.json']];print('ok')"`
Expected: `ok`

- [ ] **Step 5: Commit scaffold + spec + this plan**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json README.md docs/specs/2026-08-20-coverage-skill.md docs/superpowers/plans/2026-08-20-kerbe-coverage.md
git commit -m "feat: plugin scaffold + kerbe:coverage spec and implementation plan" -- .claude-plugin README.md docs
```

---

### Task 2: `verdict.py` — the computed verdict (TDD)

**Files:**
- Create: `skills/coverage/scripts/verdict.py`
- Test: `tests/test_verdict.py`

**Interfaces:**
- Produces: `python3 skills/coverage/scripts/verdict.py <PROMISES.md>` → verdict block on stdout; exit 0 finished, 1 not finished, 2 malformed. Importable: `parse(path) -> (header: dict, rows: list[dict])`, `verdict(header, rows) -> (text: str, exit_code: int)`, `class Malformed(Exception)`. Row dict keys: `id, promise, promised_by, spec, plan, code, evidence`.

- [ ] **Step 1: Write the failing tests**

`tests/test_verdict.py` — full content:

```python
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "coverage" / "scripts" / "verdict.py"

HEADER = """# Promise ledger — cards
LEDGER_VERSION: 1
MODE: {mode}
STATUS: FROZEN
SOURCES: docs@abc1234 · design@v42
EXTRACTION: converged (passes=3)

| id | promise | promised-by | spec | plan | code | evidence |
|----|---------|-------------|------|------|------|----------|
"""

FINISHED_AUDIT = HEADER.format(mode="audit") + """\
| P-001 | Card grid on index | figma:1:3 | doc:UI_ELEMENTS.md#grid | task:T1 index page | present | templates/card/index.html.twig:4 route card_index defined |
| P-002 | Detail description | req:REQ-CARD-002 | origin | task:T2 detail page | present | templates/card/detail.html.twig:7 |
"""

OPEN_AUDIT = HEADER.format(mode="audit") + """\
| P-001 | Card grid on index | figma:1:3 | doc:UI_ELEMENTS.md#grid | task:T1 index page | present | templates/card/index.html.twig:4 |
| P-002 | Download row | figma:2:2 | req:REQ-CARD-002 | task:T3 download row | absent | no template renders a download row |
| P-003 | Filter chips row | figma:1:4 | GAP | ? | ? | no spec doc mentions filter chips |
"""

FINISHED_PREIMPL = HEADER.format(mode="pre-impl") + """\
| P-001 | Card grid on index | figma:1:3 | doc:UI_ELEMENTS.md#grid | task:T1 index page | to-build | expected absent pre-impl |
"""

DUP_ID = HEADER.format(mode="audit") + """\
| P-001 | A | figma:1:3 | origin | task:T1 | present | a:1 |
| P-001 | B | figma:1:4 | origin | task:T1 | present | a:2 |
"""

BAD_VOCAB = HEADER.format(mode="audit") + """\
| P-001 | A | figma:1:3 | origin | task:T1 | missing | a:1 |
"""

NO_MODE = FINISHED_AUDIT.replace("MODE: audit\n", "")


def run(text):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(text)
    return subprocess.run([sys.executable, str(SCRIPT), f.name],
                          capture_output=True, text=True)


class VerdictTest(unittest.TestCase):
    def test_finished_audit_exits_0(self):
        r = run(FINISHED_AUDIT)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("FINISHED: YES", r.stdout)
        self.assertIn("promises: 2", r.stdout)

    def test_open_audit_exits_1_and_lists_open_rows(self):
        r = run(OPEN_AUDIT)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FINISHED: NO", r.stdout)
        self.assertIn("P-002", r.stdout)
        self.assertIn("P-003", r.stdout)
        self.assertNotIn("P-001", r.stdout.split("FINISHED")[1])

    def test_hop_counts(self):
        r = run(OPEN_AUDIT)
        self.assertIn("design->spec : 1 GAP", r.stdout)
        self.assertIn("1 present", r.stdout)
        self.assertIn("1 absent", r.stdout)

    def test_preimpl_tobuild_is_finished(self):
        r = run(FINISHED_PREIMPL)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("FINISHED: YES", r.stdout)

    def test_duplicate_id_is_malformed(self):
        r = run(DUP_ID)
        self.assertEqual(r.returncode, 2)
        self.assertIn("P-001", r.stderr)

    def test_bad_code_vocab_is_malformed(self):
        r = run(BAD_VOCAB)
        self.assertEqual(r.returncode, 2)
        self.assertIn("missing", r.stderr)

    def test_missing_mode_is_malformed(self):
        r = run(NO_MODE)
        self.assertEqual(r.returncode, 2)
        self.assertIn("MODE", r.stderr)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests, verify they fail**

Run: `python3 -m unittest tests.test_verdict -v`
Expected: errors (script does not exist yet).

- [ ] **Step 3: Implement `skills/coverage/scripts/verdict.py`**

```python
#!/usr/bin/env python3
"""Compute the kerbe:coverage verdict from a promise ledger.

The verdict is COUNTED from ledger rows, never asserted by an agent.
Spec: docs/specs/2026-08-20-coverage-skill.md. Exit: 0 finished, 1 not, 2 malformed.
"""
import pathlib
import re
import sys

ID_RE = re.compile(r"^P-\d{3,}$")
SPEC_RE = re.compile(r"^(\?|req:\S.*|doc:\S.*|origin|GAP|n/a)$")
PLAN_RE = re.compile(r"^(\?|task:\S.*|origin|GAP|none-yet)$")
CODE_VOCAB = ("present", "partial", "absent", "to-build", "?")
HEADER_FIELDS = ("LEDGER_VERSION", "MODE", "STATUS")
MODES = ("audit", "pre-impl")


class Malformed(Exception):
    pass


def parse(path):
    text = pathlib.Path(path).read_text()
    header = {}
    for field in HEADER_FIELDS:
        m = re.search(r"^" + field + r":\s*(\S+)", text, re.M)
        if not m:
            raise Malformed("missing header field " + field)
        header[field] = m.group(1)
    if header["MODE"] not in MODES:
        raise Malformed("MODE must be one of " + ", ".join(MODES))
    rows, seen = [], set()
    for lineno, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        first = cells[0] if cells else ""
        if first == "id" or not first or set(first) <= set("-: "):
            continue  # column header / separator row
        if not ID_RE.match(first):
            raise Malformed("line %d: row id %r is not P-NNN" % (lineno, first))
        if len(cells) != 7:
            raise Malformed("line %d: %s has %d columns, expected 7 (no | in cells)"
                            % (lineno, first, len(cells)))
        pid, promise, promised_by, spec, plan, code, evidence = cells
        if pid in seen:
            raise Malformed("line %d: duplicate id %s" % (lineno, pid))
        seen.add(pid)
        if not promise or not promised_by:
            raise Malformed(pid + ": promise and promised-by must be non-empty")
        if not SPEC_RE.match(spec):
            raise Malformed(pid + ": bad spec value %r" % spec)
        if not PLAN_RE.match(plan):
            raise Malformed(pid + ": bad plan value %r" % plan)
        if code not in CODE_VOCAB:
            raise Malformed(pid + ": bad code value %r" % code)
        rows.append({"id": pid, "promise": promise, "promised_by": promised_by,
                     "spec": spec, "plan": plan, "code": code, "evidence": evidence})
    if not rows:
        raise Malformed("no promise rows found")
    return header, rows


def _is_open(row, mode):
    if row["spec"] in ("GAP", "?") or row["plan"] in ("GAP", "?"):
        return True
    if mode == "audit":
        return row["code"] in ("absent", "partial", "to-build", "?")
    return False  # pre-impl: code column is the to-build inventory, informational


def verdict(header, rows):
    mode = header["MODE"]
    slice_name = "?"
    spec_gaps = sum(1 for r in rows if r["spec"] == "GAP")
    plan_gaps = sum(1 for r in rows if r["plan"] == "GAP")
    code_counts = {v: sum(1 for r in rows if r["code"] == v) for v in CODE_VOCAB}
    open_rows = [r["id"] for r in rows if _is_open(r, mode)]
    lines = [
        "kerbe:coverage verdict (mode: %s)" % mode,
        "promises: %d" % len(rows),
        "hop design->spec : %d GAP" % spec_gaps,
        "hop spec->plan   : %d GAP" % plan_gaps,
        "hop plan->code   : %d present · %d partial · %d absent · %d to-build · %d unverified"
        % (code_counts["present"], code_counts["partial"], code_counts["absent"],
           code_counts["to-build"], code_counts["?"]),
    ]
    if open_rows:
        lines.append("FINISHED: NO — %d open rows: %s" % (len(open_rows), " ".join(open_rows)))
        return "\n".join(lines), 1
    lines.append("FINISHED: YES")
    return "\n".join(lines), 0


def main(argv):
    if len(argv) != 2:
        print("usage: verdict.py PROMISES.md", file=sys.stderr)
        return 2
    try:
        header, rows = parse(argv[1])
    except (Malformed, OSError) as e:
        print("MALFORMED LEDGER: " + str(e), file=sys.stderr)
        return 2
    text, code = verdict(header, rows)
    print(text)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Run tests, verify they pass**

Run: `python3 -m unittest tests.test_verdict -v` — Expected: all PASS. Then `chmod +x skills/coverage/scripts/verdict.py`.

- [ ] **Step 5: Commit**

```bash
git add skills/coverage/scripts/verdict.py tests/test_verdict.py
git commit -m "feat(coverage): verdict.py — computed, never asserted" -- skills/coverage/scripts/verdict.py tests/test_verdict.py
```

---

### Task 3: `fixtures/score.py` — deterministic fixture scoring (TDD)

**Files:**
- Create: `fixtures/score.py`
- Test: `tests/test_score.py`

**Interfaces:**
- Consumes: `verdict.parse` from Task 2.
- Produces: `python3 fixtures/score.py <EXPECTED.json> <PROMISES.md> [OUT_OF_SCOPE.md]` → per-check PASS/FAIL lines; exit 0 all pass, 1 otherwise. `EXPECTED.json` schema: `{"require": [{"desc": str, "column": "spec"|"plan"|"code", "value": str, "match_re": str}], "forbid": [{"desc": str, "any_re": str}]}`. A `require` passes when some ledger row has `row[column] == value` AND `match_re` (case-sensitive) matches the row's `promise` or `evidence`. A `forbid` fails when any ledger row's promise or evidence matches `any_re` (the drop-file is exempt — that is where decoys belong).

- [ ] **Step 1: Write the failing tests**

`tests/test_score.py` — full content:

```python
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "fixtures" / "score.py"

LEDGER = """# Promise ledger — cards
LEDGER_VERSION: 1
MODE: audit
STATUS: FROZEN

| id | promise | promised-by | spec | plan | code | evidence |
|----|---------|-------------|------|------|------|----------|
| P-001 | Download row on detail | figma:2:2 | req:REQ-CARD-002 | task:T3 | absent | no template renders it |
| P-002 | Filter chips row | figma:1:4 | GAP | ? | ? | unspec'd |
"""

EXPECTED = {
    "require": [
        {"desc": "unbuilt download row", "column": "code", "value": "absent", "match_re": "[Dd]ownload"},
        {"desc": "unspec'd filter chips", "column": "spec", "value": "GAP", "match_re": "[Ff]ilter chips"},
    ],
    "forbid": [
        {"desc": "dead-code decoy not counted", "any_re": "unusedExportHelper"},
    ],
}


def run(expected, ledger):
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "EXPECTED.json").write_text(json.dumps(expected))
    (d / "PROMISES.md").write_text(ledger)
    return subprocess.run([sys.executable, str(SCRIPT), str(d / "EXPECTED.json"),
                           str(d / "PROMISES.md")], capture_output=True, text=True)


class ScoreTest(unittest.TestCase):
    def test_all_pass(self):
        r = run(EXPECTED, LEDGER)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.count("PASS"), 3)

    def test_missing_require_fails(self):
        bad = LEDGER.replace("absent", "present")
        r = run(EXPECTED, bad)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL", r.stdout)
        self.assertIn("unbuilt download row", r.stdout)

    def test_counted_decoy_fails(self):
        bad = LEDGER + "| P-003 | unusedExportHelper has no caller | plan:T1 | origin | task:T1 | present | src/x.php:9 |\n"
        r = run(EXPECTED, bad)
        self.assertEqual(r.returncode, 1)
        self.assertIn("dead-code decoy", r.stdout)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests, verify they fail** — `python3 -m unittest tests.test_score -v`

- [ ] **Step 3: Implement `fixtures/score.py`**

```python
#!/usr/bin/env python3
"""Score a produced promise ledger against a fixture's EXPECTED.json.

Acceptance harness for kerbe:coverage: every skill change must keep all
require checks passing and all forbid checks clean on every fixture.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "skills" / "coverage" / "scripts"))
from verdict import Malformed, parse  # noqa: E402


def main(argv):
    if len(argv) < 3:
        print("usage: score.py EXPECTED.json PROMISES.md [OUT_OF_SCOPE.md]", file=sys.stderr)
        return 1
    expected = json.loads(pathlib.Path(argv[1]).read_text())
    try:
        _, rows = parse(argv[2])
    except Malformed as e:
        print("FAIL ledger is malformed: " + str(e))
        return 1
    failures = 0
    for req in expected.get("require", []):
        rx = re.compile(req["match_re"])
        hit = any(r[req["column"]] == req["value"]
                  and (rx.search(r["promise"]) or rx.search(r["evidence"]))
                  for r in rows)
        print(("PASS " if hit else "FAIL ") + "require: " + req["desc"])
        failures += 0 if hit else 1
    for forb in expected.get("forbid", []):
        rx = re.compile(forb["any_re"])
        hit = [r["id"] for r in rows if rx.search(r["promise"]) or rx.search(r["evidence"])]
        ok = not hit
        print(("PASS " if ok else "FAIL ") + "forbid: " + forb["desc"]
              + ("" if ok else " (counted in " + " ".join(hit) + ")"))
        failures += 0 if ok else 1
    print("score: %d checks, %d failed" % (
        len(expected.get("require", [])) + len(expected.get("forbid", [])), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Run tests, verify they pass** — `python3 -m unittest tests.test_score -v`, then `chmod +x fixtures/score.py`

- [ ] **Step 5: Commit**

```bash
git add fixtures/score.py tests/test_score.py
git commit -m "feat(coverage): fixture scoring harness" -- fixtures/score.py tests/test_score.py
```

---

### Task 4: Ledger + config references

**Files:**
- Create: `skills/coverage/references/ledger.md`
- Create: `skills/coverage/references/config.md`
- Create: `kerbe.yml.example`

**Interfaces:**
- Produces: the ledger format and `kerbe.yml` fields the SKILL.md (Task 7) points at.

- [ ] **Step 1: Write `skills/coverage/references/ledger.md`** — copy the "The promise ledger" and "The computed verdict" sections of the spec verbatim (they are the normative text), plus: the no-pipes-in-cells rule; a complete worked example ledger of 4 rows (one per hop-break: `spec: GAP`, `plan: GAP`, `code: absent`, `code: partial` with an unimported-stylesheet evidence line); the rule that ids are never reused and demoted rows are deleted (their id retires); `OUT_OF_SCOPE.md` line format: `- [route:/kerbe:audit] <one line>`.

- [ ] **Step 2: Write `kerbe.yml.example`** — exactly the YAML block from the spec's "Project independence" section, with one inline comment per key.

- [ ] **Step 3: Write `skills/coverage/references/config.md`** — for each `kerbe.yml` key: type, required/optional, default, and how the skill uses it. Include the resolution rules: config is read from the target project root; a missing `kerbe.yml` is a hard stop ("run kerbe:init or create it from kerbe.yml.example" — no guessed defaults); `design.adapter: none` ⇒ no design-sourced rows and `spec: n/a` is legal; `token_env` beats `token_cmd` when both set.

- [ ] **Step 4: Verify the worked example in ledger.md parses** — extract it to a temp file and run `verdict.py` on it; expected exit 1 (it has open rows) and `promises: 4`.

- [ ] **Step 5: Commit**

```bash
git add skills/coverage/references/ledger.md skills/coverage/references/config.md kerbe.yml.example
git commit -m "docs(coverage): ledger format, config seam" -- skills/coverage/references kerbe.yml.example
```

---

### Task 5: Stack adapter recipes

**Files:**
- Create: `adapters/stack/symfony/verify.md`
- Create: `adapters/stack/flutter/verify.md`

**Interfaces:**
- Produces: recipe files SKILL.md points verifiers at; each defines what `present` (wired), `partial`, `absent` mean on that stack, with grep-level procedures.

- [ ] **Step 1: Write `adapters/stack/symfony/verify.md`** with these recipes (each: what to check, the exact grep/read procedure, what verdict each outcome yields):
  1. **Route wired** — the route name/path a template links (`path('x')`, `href`) has a matching `#[Route]` attribute (or YAML route) in a controller; controller method non-empty. Linked-but-undefined ⇒ `partial` (dead link). Defined-but-linked-from-nowhere is NOT a coverage break (drop-file).
  2. **Template served** — some controller `render()`s it.
  3. **Stylesheet wired** — the class the template actually renders has a rule in authored CSS AND that file is reachable from the manifest (`@use`/`@import` chain from the entry stylesheet). Exists-but-unimported ⇒ `partial`. Class-name mismatch (template `.card-share`, CSS only `.card-email`) ⇒ `partial`.
  4. **JS wired** — behaviour depends on an entry present in `importmap` and imported by the app entrypoint.
  5. **Stub** — empty/TODO method body behind a real route ⇒ `partial`.
  6. **Entity/field** — a spec'd field exists on the entity and in a migration.
- [ ] **Step 2: Write `adapters/stack/flutter/verify.md`** with the equivalents, marked at the top as **drafted, pending validation on a real Flutter app**: widget class exists AND is reachable from the widget tree (imported + constructed somewhere on a route); route registered in the router table (GoRouter/Navigator map) — planned-but-unregistered ⇒ `partial`; asset spec'd ⇒ declared under `flutter.assets` in `pubspec.yaml` AND the file exists; callback/handler stub (`onPressed: null`, empty body, `// TODO`) ⇒ `partial`; state wiring — a provider/bloc the screen depends on is registered above it in the tree.
- [ ] **Step 3: Both files end with the shared rule:** every `present` cites `file:line` for BOTH existence and wiring; when a recipe cannot run (tool missing, dir absent), the row stays `?` with the reason in evidence — never silently `present`.
- [ ] **Step 4: Commit**

```bash
git add adapters/stack/symfony/verify.md adapters/stack/flutter/verify.md
git commit -m "feat(coverage): stack adapter wiring recipes (symfony battle-tested, flutter drafted)" -- adapters/stack
```

---

### Task 6: Design adapters + portable snapshot script

**Files:**
- Create: `adapters/design/figma.md`
- Create: `adapters/design/none.md`
- Create: `skills/coverage/scripts/figma_cache.py`
- Test: `tests/test_figma_cache.py`

**Interfaces:**
- Consumes: `kerbe.yml` `design.*` keys (Task 4).
- Produces: `figma_cache.py --file <key> --out <dir> [--page <name>] [--refetch] [--token-cmd <cmd>]`; token from `$FIGMA_API_TOKEN` else `--token-cmd` output; writes `file.json`, `manifest.json`, `MANIFEST.md`; refuses to overwrite without `--refetch` (exit 2).

- [ ] **Step 1: Port the snapshot script.** Copy the frozen suite's cache script into `skills/coverage/scripts/figma_cache.py` with these changes and NO others: delete the `sys.path.insert`/`config` import; add `--token-cmd`; add a `resolve_token(args)` that reads `os.environ.get("FIGMA_API_TOKEN")` else runs `subprocess.run(args.token_cmd, shell=True, capture_output=True, text=True)` and errors clearly when neither yields a token; module docstring reworded to "fetched once per extraction; every verification pass reads this snapshot; re-fetching starts a new extraction (new ledger)". Keep `DROPPED_KEYS`, `compact`, `count_nodes`, manifest/MANIFEST output byte-compatible.
- [ ] **Step 2: Write `tests/test_figma_cache.py`** (no network): (a) refusal — create tmp dir with an existing `file.json`, run script with `--file x --out <dir>` and env `FIGMA_API_TOKEN=t`; expect exit 2 and "REFUSED" in stderr; (b) missing token — run with empty env override and no `--token-cmd` against an empty out dir; expect nonzero exit and "token" in stderr; (c) unit-test `compact()` drops exactly `DROPPED_KEYS` and `count_nodes()` counts a 3-node tree as 3 (import the module directly).
- [ ] **Step 3: Run tests** — fail first (script absent), then pass; `chmod +x`.
- [ ] **Step 4: Write `adapters/design/figma.md`**: snapshot once per extraction into `{slice}/​{design.cache_dir}` via the script (exact command line with config substitutions); enumerate promises from `file.json` **leaf-to-leaf** — recurse every frame's subtree; every interactive leaf (button, link, toggle, tab, picker, action row, input, card) is its own promise row `figma:<node-id>`; a page-level frame is never a row by itself; commit the snapshot with the ledger.
- [ ] **Step 5: Write `adapters/design/none.md`**: no design leg by configuration; promises originate in spec docs and plan; `spec: n/a` is legal only in this mode; the ledger header records `design@n/a`.
- [ ] **Step 6: Commit**

```bash
git add skills/coverage/scripts/figma_cache.py tests/test_figma_cache.py adapters/design/figma.md adapters/design/none.md
git commit -m "feat(coverage): design adapters + portable snapshot script" -- skills/coverage/scripts/figma_cache.py tests/test_figma_cache.py adapters/design
```

---

### Task 7: SKILL.md

**Files:**
- Create: `skills/coverage/SKILL.md`

**Interfaces:**
- Consumes: everything above by reference (`references/ledger.md`, `references/config.md`, `adapters/`, `scripts/verdict.py`).
- Produces: the invocable `/kerbe:coverage` skill.

**Process:** invoke `superpowers:writing-skills` before authoring; target ≤ 220 lines; the skill body contains **zero** project paths, doc filenames, stack probes, or design-tool calls — those live behind the config/adapters.

- [ ] **Step 1: Write frontmatter** — `name: coverage`; description as a block scalar: answers exactly one question — is anything the approach documentation promises missing from the build; two phases (extract a frozen promise ledger, verify each row with evidence); verdict computed by script; pre-impl and audit modes; use before implementing (is the spec+plan complete) or before sign-off (is everything built and wired).
- [ ] **Step 2: Write the body** with exactly these sections:
  1. **The one question** — missing functionality only; the admission rule is structural: a finding either is a ledger row with a real `promised-by`, or it goes to `OUT_OF_SCOPE.md` uncounted (format per `references/ledger.md`). Include the worked do/don't table from the spec's predecessor (genericized): designed link in no template ⇒ row; button rendered but route unwired ⇒ row (`partial`); two API calls inside an open transaction ⇒ drop-file; stale doc about an existing thing ⇒ drop-file.
  2. **Setup** — read `kerbe.yml` (hard stop if missing, point at `kerbe.yml.example`); resolve slice folder, mode (user-stated, else probe `stack.code_roots` for the slice's artifacts), design + stack adapter files; state mode and adapters at the top of the run.
  3. **Phase A — EXTRACT** — the procedure from the spec: snapshot design once (design adapter); dispatch extractors per source class (`model: sonnet`, one per source, prompts state leaf-level rule and the row schema, return rows only); merge + dedupe (same promised-by + same leaf = one row); safety passes until two consecutive passes add zero rows, cap 5; write header (`MODE`, `STATUS: FROZEN`, `SOURCES` pin, `EXTRACTION:` outcome), commit ledger + snapshot. Include the extractor prompt template verbatim in a fenced block.
  4. **Phase B — VERIFY** — batch rows (≤ 20/agent, `model: haiku`); each verifier fills `spec`/`plan`/`code`/`evidence` per the stack adapter recipes, reading plan task **bodies** not titles; then the quality pass (one fresh agent: re-verify every `GAP`/`absent`/`partial` INCLUDING that the `promised-by` citation really promises it; spot-audit 10% ≥ 5 of `present`); demoted rows are deleted and their finding moved to the drop-file. Include the verifier prompt template verbatim.
  5. **Verdict** — run `scripts/verdict.py PROMISES.md`; paste its output verbatim into the run summary; never restate or adjust its numbers; exit 2 means fix the ledger format, not the script.
  6. **Rules** — short list: never edit application code or docs (report only, both modes); one slice per run, cross-slice observations to the drop-file; sibling slices' features are never this slice's gaps; re-verification after fixes reuses the frozen ledger (the denominator moves only on a deliberate new extraction); every `present` cites existence AND wiring; no `|` in cells; the fixtures are the regression gate for any change to this skill (`fixtures/ACCEPTANCE.md`).
- [ ] **Step 3: Self-check** — grep the file for forbidden legacy strings (Global Constraints) and for any project-specific path; count lines (≤ 220).
- [ ] **Step 4: Commit**

```bash
git add skills/coverage/SKILL.md
git commit -m "feat(coverage): the kerbe:coverage skill" -- skills/coverage/SKILL.md
```

---

### Task 8: `fixtures/symfony-mini` — planted gaps + golden ledger

**Files:**
- Create: `fixtures/symfony-mini/kerbe.yml`
- Create: `fixtures/symfony-mini/planning/slices/cards/{REQUIREMENTS.md,UI_ELEMENTS.md,PLAN.md,DONE_CRITERIA.md}`
- Create: `fixtures/symfony-mini/planning/slices/cards/design-cache/{file.json,manifest.json,MANIFEST.md}`
- Create: `fixtures/symfony-mini/src/Controller/CardController.php`
- Create: `fixtures/symfony-mini/templates/card/{index.html.twig,detail.html.twig}`
- Create: `fixtures/symfony-mini/assets/styles/{app.scss,_card.scss,_hover.scss}`
- Create: `fixtures/symfony-mini/tests/Controller/CardControllerTest.php`
- Create: `fixtures/symfony-mini/EXPECTED.json`
- Create: `fixtures/symfony-mini/GOLDEN.md`

**Planted gaps (audit mode):** P1 Download row — designed (`figma:2:2`), spec'd (REQ-CARD-002), planned (task T3), no code ⇒ `code: absent`. P2 Filter chips row — designed (`figma:1:4`), in no spec doc ⇒ `spec: GAP`. P3 Share-by-email popup — spec'd (REQ-CARD-004), no plan task ⇒ `plan: GAP`. P4 Export-as-PDF — planned (T4), template links `/cards/export`, no route defines it ⇒ `code: partial` (dead link). P5 Card hover style — planned (T5), template renders `.card-hover`, `_hover.scss` defines it but `app.scss` imports only `_card.scss` ⇒ `code: partial` (unimported stylesheet). P6 Email receipt on download — planned (T6), `emailReceipt()` body is a TODO comment ⇒ `code: partial` (stub).
**Decoys (must never be counted):** D1 `unusedExportHelper()` public method, no caller. D2 `CardControllerTest::testDetailPage()` makes no assertion. D3 `DONE_CRITERIA.md` checkboxes unticked for features that exist.

- [ ] **Step 1: Write the planning docs.** REQUIREMENTS.md: REQ-CARD-001 index grid with title+cover; REQ-CARD-002 detail page with description and a Download action row; REQ-CARD-003 Export-as-PDF from the detail toolbar; REQ-CARD-004 Share-by-email popup from the detail page; REQ-CARD-005 card hover style per design; REQ-CARD-006 email receipt after download. UI_ELEMENTS.md: measurements-style entries citing `figma:1:3` (grid), `figma:2:2` (download row), `figma:2:3` (export button), `figma:2:4` (share button) — **no entry for `figma:1:4`**. PLAN.md tasks: T1 index page ✔-shaped body, T2 detail page, T3 Download row, T4 Export toolbar link, T5 hover style, T6 email receipt — **no task for share popup**. DONE_CRITERIA.md: 4 unticked boxes for T1/T2 features (decoy D3).
- [ ] **Step 2: Write `design-cache/file.json`** (hand-authored, same shape the snapshot script emits):

```json
{"name":"cards-design","document":{"id":"0:0","type":"DOCUMENT","children":[{"id":"0:1","type":"CANVAS","name":"Cards","children":[{"id":"1:2","type":"FRAME","name":"Cards page","children":[{"id":"1:3","type":"FRAME","name":"Card grid"},{"id":"1:4","type":"FRAME","name":"Filter chips row","children":[{"id":"1:5","type":"TEXT","name":"All"},{"id":"1:6","type":"TEXT","name":"Recent"}]}]},{"id":"2:1","type":"FRAME","name":"Card detail","children":[{"id":"2:2","type":"FRAME","name":"Download row"},{"id":"2:3","type":"INSTANCE","name":"Export as PDF button"},{"id":"2:4","type":"INSTANCE","name":"Share by email button"}]}]}]}}
```

plus a minimal matching `manifest.json` (`file_key: "FIXTURE"`, `figma_version: "fixture-1"`, sha over the payload) and two-line `MANIFEST.md`.
- [ ] **Step 3: Write the code.** `CardController.php`: `#[Route('/cards', name: 'card_index')] index()` rendering `card/index.html.twig`; `#[Route('/cards/{id}', name: 'card_detail')] detail()` rendering `card/detail.html.twig`; `emailReceipt()` with body `// TODO send receipt` and no route; `public function unusedExportHelper(): string` returning a constant (D1). `index.html.twig`: grid markup with `class="card-grid card-hover"`. `detail.html.twig`: description block, export link `<a href="/cards/export">Export as PDF</a>` — and **no** download-row markup, **no** share markup. `app.scss`: `@use './card';` only. `_card.scss`: `.card-grid { display: grid; }`. `_hover.scss`: `.card-hover:hover { box-shadow: 0 1px 4px; }`. `CardControllerTest.php`: one test method calling `$this->assertTrue(true)`? — no: D2 must assert nothing, so the method body just instantiates the controller and adds a comment (decoy).
- [ ] **Step 4: Write `fixtures/symfony-mini/kerbe.yml`** — planning_root `planning/slices`, spec_globs `["*.md"]`, plan_glob `"*PLAN*.md"`, design adapter `figma` with `cache_dir: design-cache` (snapshot pre-supplied; extraction must NOT refetch — `file_key: FIXTURE` and no token makes a live call fail loudly, which is correct), stack adapter `symfony`, code_roots `["src/", "templates/", "assets/", "tests/"]`.
- [ ] **Step 5: Write `EXPECTED.json`:**

```json
{
  "require": [
    {"desc": "P1 unbuilt download row", "column": "code", "value": "absent", "match_re": "[Dd]ownload"},
    {"desc": "P2 unspec'd filter chips", "column": "spec", "value": "GAP", "match_re": "[Ff]ilter chips"},
    {"desc": "P3 unplanned share popup", "column": "plan", "value": "GAP", "match_re": "[Ss]hare"},
    {"desc": "P4 dead export link", "column": "code", "value": "partial", "match_re": "[Ee]xport"},
    {"desc": "P5 unimported hover stylesheet", "column": "code", "value": "partial", "match_re": "hover"},
    {"desc": "P6 stub email receipt", "column": "code", "value": "partial", "match_re": "[Rr]eceipt"}
  ],
  "forbid": [
    {"desc": "D1 dead code must not be counted", "any_re": "unusedExportHelper"},
    {"desc": "D2 assertion-less test must not be counted", "any_re": "assert|testDetailPage"},
    {"desc": "D3 unticked checkboxes must not be counted", "any_re": "checkbox|unticked|DONE_CRITERIA"}
  ]
}
```

- [ ] **Step 6: Write `GOLDEN.md`** — the hand-authored correct ledger: header (`MODE: audit`, `STATUS: FROZEN`, `SOURCES: docs@fixture · design@fixture-1`) and 9 rows: the six planted rows above with correct columns/evidence plus three `present` rows (card grid, detail description, index route). Run both checks:

Run: `python3 skills/coverage/scripts/verdict.py fixtures/symfony-mini/GOLDEN.md` — Expected: exit 1, `promises: 9`, `FINISHED: NO — 6 open rows`.
Run: `python3 fixtures/score.py fixtures/symfony-mini/EXPECTED.json fixtures/symfony-mini/GOLDEN.md` — Expected: exit 0, 9 × PASS.

- [ ] **Step 7: Commit**

```bash
git add fixtures/symfony-mini
git commit -m "feat(coverage): symfony-mini fixture — six planted gaps, three decoys, golden ledger" -- fixtures/symfony-mini
```

---

### Task 9: `fixtures/flutter-mini`

**Files:**
- Create: `fixtures/flutter-mini/kerbe.yml`
- Create: `fixtures/flutter-mini/planning/slices/gallery/{REQUIREMENTS.md,PLAN.md}`
- Create: `fixtures/flutter-mini/lib/{main.dart,router.dart,util.dart}`
- Create: `fixtures/flutter-mini/lib/screens/{gallery_screen.dart}`
- Create: `fixtures/flutter-mini/pubspec.yaml`
- Create: `fixtures/flutter-mini/EXPECTED.json`
- Create: `fixtures/flutter-mini/GOLDEN.md`

**Planted gaps:** P1 Favorite button on gallery items — spec'd (REQ-GAL-002), planned (T2), no widget anywhere ⇒ `code: absent`. P2 Gallery detail route — planned (T3 names route `/gallery/detail`), not in `router.dart`'s route table ⇒ `code: partial`. P3 Logo asset — spec'd (REQ-GAL-003 "logo in the app bar", `images/logo.png`), not declared under `flutter.assets` in `pubspec.yaml` ⇒ `code: partial`. **Decoy:** D1 `formatBytes()` in `util.dart`, no caller. Design adapter: `none` (exercises that path — promises originate in spec docs).

- [ ] **Step 1: Write the planning docs.** REQUIREMENTS.md: REQ-GAL-001 gallery grid screen; REQ-GAL-002 favorite button on each item; REQ-GAL-003 logo in the app bar from `images/logo.png`. PLAN.md: T1 gallery screen + `/gallery` route; T2 favorite button; T3 detail screen at `/gallery/detail`.
- [ ] **Step 2: Write the code.** `main.dart`: `runApp` with `MaterialApp.router(routerConfig: router)`. `router.dart`: `GoRouter(routes: [GoRoute(path: '/'), GoRoute(path: '/gallery', builder: ... GalleryScreen())])` — no detail route. `gallery_screen.dart`: grid of items, `AppBar(title: Text('Gallery'))` — no favorite button, no logo Image. `util.dart`: `String formatBytes(int b)` unused (D1). `pubspec.yaml`: name, sdk, `flutter:` section with `uses-material-design: true` and **no** `assets:` list; `images/logo.png` not created.
- [ ] **Step 3: `kerbe.yml`** — design adapter `none`, stack `flutter`, code_roots `["lib/", "pubspec.yaml"]`.
- [ ] **Step 4: `EXPECTED.json`** — require: (`code`,`absent`,`[Ff]avorite`), (`code`,`partial`,`detail`), (`code`,`partial`,`logo`); forbid: (`formatBytes`).
- [ ] **Step 5: `GOLDEN.md`** — 5 rows: the three planted plus two `present` (gallery screen route, grid). All spec cells `origin`/`req:...`, no `n/a`-abuse (design none ⇒ promises originate in spec). Run verdict (exit 1, `promises: 5`) and score (exit 0, 4 × PASS).
- [ ] **Step 6: Commit**

```bash
git add fixtures/flutter-mini
git commit -m "feat(coverage): flutter-mini fixture — three planted gaps, one decoy" -- fixtures/flutter-mini
```

---

### Task 10: Live acceptance runs + `fixtures/ACCEPTANCE.md`

**Files:**
- Create: `fixtures/ACCEPTANCE.md`
- Possibly modify: `skills/coverage/SKILL.md`, adapter files (only if a run exposes a defect)

- [ ] **Step 1: Write `fixtures/ACCEPTANCE.md`** — the standing gate: for each fixture, dispatch a fresh subagent whose prompt is: read `<repo>/skills/coverage/SKILL.md` and run it end-to-end in audit mode on slice `<cards|gallery>` inside the fixture dir, writing `PROMISES.md` + `OUT_OF_SCOPE.md` into the slice folder of a scratch copy; then the operator runs `score.py` and `verdict.py` on the output. **Pass = all require PASS, all forbid PASS, and a second identical run yields an identical verdict block.** Any change to SKILL.md, adapters, or scripts reruns this gate before merging. Record each run's date/model/result in a table at the bottom.
- [ ] **Step 2: Run the gate on symfony-mini** (subagent, `model: sonnet` for the whole run in v1 — extraction quality dominates). Copy the fixture to a scratch dir first so produced files never dirty the repo fixture.
- [ ] **Step 3: Score it.** If a require check fails or a decoy is counted: fix the skill/adapter wording (that is the harness working), re-run, and record the iteration in ACCEPTANCE.md.
- [ ] **Step 4: Repeat Steps 2–3 for flutter-mini.**
- [ ] **Step 5: Determinism check** — rerun symfony-mini once more; diff the two verdict blocks; must be identical.
- [ ] **Step 6: Commit**

```bash
git add fixtures/ACCEPTANCE.md
git commit -m "feat(coverage): acceptance gate + first recorded runs" -- fixtures/ACCEPTANCE.md skills/coverage adapters
```

(Include `skills/coverage`/`adapters` in the pathspec only if Step 3/4 edited them; list exactly what changed.)

---

### Task 11: README + ROADMAP closure

**Files:**
- Modify: `README.md` (Skills section: usage of `/kerbe:coverage`, the two modes, the fixture gate)
- Modify: `ROADMAP.md` (add a short section after §1.5: the inventory-first supersession — the frozen-invocation machinery of §1.5 is superseded for `coverage` by the ledger design; link the spec; note the fixture harness as the standing acceptance)

- [ ] **Step 1: Update README.md** — add invocation example (`/kerbe:coverage cards` from a project with `kerbe.yml`), the one-question scope statement, and the fixture-gate rule for contributors.
- [ ] **Step 2: Update ROADMAP.md** — new subsection "§1.6 Inventory-first supersession (2026-08-20)" with: root cause (no frozen denominator), the ledger design in three sentences, pointer to the spec, and the rule that skill edits are gated by `fixtures/ACCEPTANCE.md`.
- [ ] **Step 3: Run the full test suite** — `python3 -m unittest discover -s tests -v` — all pass.
- [ ] **Step 4: Commit**

```bash
git add README.md ROADMAP.md
git commit -m "docs: kerbe:coverage usage + roadmap §1.6 inventory-first supersession" -- README.md ROADMAP.md
```

---

## Self-Review

- **Spec coverage:** one question + drop-file → Task 7 §1 + ledger.md; pairwise hops/ledger → Tasks 2, 4, 7; extraction loop + freeze → Task 7 §3; verify + quality pass → Task 7 §4; computed verdict → Task 2; config seam → Task 4; design adapters + snapshot → Task 6; stack recipes → Task 5; fixtures + score + acceptance → Tasks 3, 8, 9, 10; modes → Tasks 2 (verdict rules) and 7 §2; "deliberately not ported" → absent from every task by construction. No gaps found.
- **Placeholder scan:** doc-writing steps specify content by enumerated bullets (deliberate: the executor writes prose from the spec, which travels with this plan); code steps carry full code. No TBDs.
- **Type consistency:** `verdict.parse`/`Malformed` consumed by `score.py` (Tasks 2→3) match; `EXPECTED.json` schema (Task 3) matches Tasks 8/9; script paths consistent (`skills/coverage/scripts/`, `fixtures/score.py`).
