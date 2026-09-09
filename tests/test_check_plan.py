import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "fixtures" / "check_plan.py"

GOOD = """# Cards — Implementation Plan

**Goal:** Ship the card index and detail pages.
**Architecture:** One controller, two templates, one stylesheet partial.
**Stack:** symfony — Twig, Doctrine.
**Spec:** planning/slices/cards/
**Design:** design_required: true — figma 05eb, page Cards, measured 2026-08-20

## Global Constraints

- Branch off `origin/review/main`.
- A task touching `src/Entity/` or `migrations/` runs the full suite and pastes it.
- Tests: `php vendor/bin/phpunit`

## File structure

- `src/Controller/CardController.php` — routing and lookups.

### Task 1: Card index route

**Effort:** standard
**Depends:** none
**Files:**
- Create: `src/Controller/CardController.php`
- Test: `tests/Controller/CardControllerTest.php`

**Interfaces:**
- Consumes: none
- Produces: route `card_index` at `/cards`, rendering `card/index.html.twig`

**Design:** node=213:2224 measured=2026-08-20

- [ ] **Step 1: Write the failing test** — cases:

      | Level | Precondition | Expectation | @req |
      |---|---|---|---|
      | http | GET `/cards` as a member | 200, the grid container is present | REQ-CARD-001 |

- [ ] **Step 2: Run it, confirm it fails** — `php vendor/bin/phpunit tests/Controller/CardControllerTest.php`
- [ ] **Step 3: Minimal implementation**
- [ ] **Step 4: Run it, confirm it passes** — zero failures, the class appears in the run
- [ ] **Step 5: Commit**

```bash
git add src/Controller/CardController.php tests/Controller/CardControllerTest.php
git commit -m "feat: card index" -- src/Controller/CardController.php tests/Controller/CardControllerTest.php
```

### Task 2: Card slug normaliser

**Effort:** low
**Depends:** 1
**Files:**
- Create: `src/Card/SlugNormaliser.php`
- Test: `tests/Unit/Card/SlugNormaliserTest.php`

**Interfaces:**
- Consumes: route `card_index` from Task 1
- Produces: `SlugNormaliser::normalise(string): string`

- [ ] **Step 1: Write the failing test** — cases:

      | Level | Precondition | Expectation | @req |
      |---|---|---|---|
      | unit | `"Rosacea  Mild"` | `"rosacea-mild"` | REQ-CARD-002 |

- [ ] **Step 2: Run it, confirm it fails** — `php vendor/bin/phpunit tests/Unit/Card/SlugNormaliserTest.php`
- [ ] **Step 3: Minimal implementation**
- [ ] **Step 4: Run it, confirm it passes** — zero failures, the class appears in the run
- [ ] **Step 5: Commit**

```bash
git add src/Card/SlugNormaliser.php tests/Unit/Card/SlugNormaliserTest.php
git commit -m "feat: slug normaliser" -- src/Card/SlugNormaliser.php tests/Unit/Card/SlugNormaliserTest.php
```
"""


def run(text, *args, name="PLAN.md"):
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / name
        p.write_text(text)
        r = subprocess.run([sys.executable, str(SCRIPT), str(p), *args],
                           capture_output=True, text=True)
        return r.returncode, r.stdout


class CheckPlanTest(unittest.TestCase):
    def test_good_plan_passes(self):
        code, out = run(GOOD, "true")
        self.assertEqual(code, 0, out)
        self.assertIn("ALL PASS", out)

    def test_missing_global_constraints_fails(self):
        code, out = run(GOOD.replace("## Global Constraints", "## Notes"), "true")
        self.assertEqual(code, 1)
        self.assertIn("FAIL Global Constraints section present", out)

    def test_unscoped_commit_fails(self):
        bad = GOOD.replace(
            'git commit -m "feat: card index" -- src/Controller/CardController.php tests/Controller/CardControllerTest.php',
            'git commit -m "feat: card index"')
        code, out = run(bad, "true")
        self.assertEqual(code, 1)
        self.assertIn("commit is pathspec-scoped", out)

    def test_git_add_all_fails(self):
        code, out = run(GOOD.replace("git add src/Controller/CardController.php tests/Controller/CardControllerTest.php",
                                     "git add -A"), "true")
        self.assertEqual(code, 1)
        self.assertIn("no unscoped staging", out)

    def test_placeholder_fails(self):
        code, out = run(GOOD.replace("**Step 3: Minimal implementation**",
                                     "**Step 3: TBD**"), "true")
        self.assertEqual(code, 1)
        self.assertIn("no placeholder", out)

    def test_design_required_needs_node_id(self):
        code, out = run(GOOD.replace("**Design:** node=213:2224 measured=2026-08-20", ""),
                        "true")
        self.assertEqual(code, 1)
        self.assertIn("node= and measured=", out)

    def test_design_not_required_skips_node_check(self):
        code, out = run(GOOD.replace("**Design:** node=213:2224 measured=2026-08-20", ""),
                        "false")
        self.assertEqual(code, 0, out)

    def test_missing_effort_fails(self):
        code, out = run(GOOD.replace("**Effort:** standard\n", ""), "true")
        self.assertEqual(code, 1)
        self.assertIn("declares an Effort level", out)

    def test_invalid_effort_value_fails(self):
        code, out = run(GOOD.replace("**Effort:** standard", "**Effort:** medium"), "true")
        self.assertEqual(code, 1)
        self.assertIn("declares an Effort level", out)

    def test_every_effort_level_accepted(self):
        for level in ("low", "standard", "deep"):
            code, out = run(GOOD.replace("**Effort:** standard",
                                         "**Effort:** " + level), "true")
            self.assertEqual(code, 0, level + ": " + out)

    def test_missing_interfaces_block_fails(self):
        code, out = run(GOOD.replace("**Interfaces:**", "**Notes:**"), "true")
        self.assertEqual(code, 1)
        self.assertIn("has an Interfaces block", out)

    def test_assertion_count_as_expected_output_fails(self):
        code, out = run(GOOD.replace("zero failures, the class appears in the run",
                                     "OK (4 tests, 7 assertions)"), "true")
        self.assertEqual(code, 1)
        self.assertIn("expected output is a shape", out)

    def test_unresolved_decision_fails(self):
        code, out = run(GOOD.replace("- Consumes: none",
                                     "- Consumes: none (open question: which repository?)"),
                        "true")
        self.assertEqual(code, 1)
        self.assertIn("no placeholder", out)

    def test_no_task_fails(self):
        code, out = run(GOOD.split("### Task 1")[0], "false")
        self.assertEqual(code, 1)
        self.assertIn("has at least one task", out)

    def test_fix_plan_name_accepted(self):
        code, out = run(GOOD, "false", name="FIX_PLAN.md")
        self.assertEqual(code, 0, out)

    def test_other_name_rejected(self):
        code, out = run(GOOD, "false", name="NOTES.md")
        self.assertEqual(code, 1)
        self.assertIn("filename is PLAN.md", out)


class DependsTest(unittest.TestCase):
    def test_missing_depends_fails(self):
        code, out = run(GOOD.replace("**Depends:** none\n", ""), "true")
        self.assertEqual(code, 1)
        self.assertIn("declares Depends", out)

    def test_depends_garbage_value_fails(self):
        code, out = run(GOOD.replace("**Depends:** none", "**Depends:** the importer"),
                        "true")
        self.assertEqual(code, 1)
        self.assertIn("declares Depends", out)

    def test_depends_list_of_several_accepted(self):
        code, out = run(GOOD.replace("**Depends:** 1", "**Depends:** 1, 1"), "true")
        self.assertEqual(code, 0, out)

    def test_depends_on_unknown_task_fails(self):
        code, out = run(GOOD.replace("**Depends:** 1", "**Depends:** 7"), "true")
        self.assertEqual(code, 1)
        self.assertIn("Depends names a task that exists", out)

    def test_depends_on_self_fails(self):
        code, out = run(GOOD.replace("**Depends:** none", "**Depends:** 1"), "true")
        self.assertEqual(code, 1)
        self.assertIn("dependency graph is acyclic", out)

    def test_dependency_cycle_fails(self):
        code, out = run(GOOD.replace("**Depends:** none", "**Depends:** 2"), "true")
        self.assertEqual(code, 1)
        self.assertIn("dependency graph is acyclic", out)


class LevelTest(unittest.TestCase):
    def test_missing_level_column_fails(self):
        code, out = run(GOOD.replace("| Level | Precondition | Expectation | @req |",
                                     "| Precondition | Expectation | @req |"), "true")
        self.assertEqual(code, 1)
        self.assertIn("case table carries a Level column", out)

    def test_invalid_level_value_fails(self):
        code, out = run(GOOD.replace("| unit |", "| integration |"), "true")
        self.assertEqual(code, 1)
        self.assertIn("case levels are unit/kernel/http/browser", out)

    def test_every_level_accepted(self):
        for level in ("unit", "kernel", "http", "browser"):
            code, out = run(GOOD.replace("| unit |", "| " + level + " |"), "true")
            self.assertEqual(code, 0, level + ": " + out)


if __name__ == "__main__":
    unittest.main()
