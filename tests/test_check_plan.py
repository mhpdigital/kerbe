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

**Files:**
- Create: `src/Controller/CardController.php`
- Test: `tests/Controller/CardControllerTest.php`

**Design:** node=213:2224 measured=2026-08-20

- [ ] **Step 1: Write the failing test**
- [ ] **Step 2: Run it, confirm it fails** — `php vendor/bin/phpunit tests/Controller/CardControllerTest.php`
- [ ] **Step 3: Minimal implementation**
- [ ] **Step 4: Run it, confirm it passes**
- [ ] **Step 5: Commit**

```bash
git add src/Controller/CardController.php tests/Controller/CardControllerTest.php
git commit -m "feat: card index" -- src/Controller/CardController.php tests/Controller/CardControllerTest.php
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


if __name__ == "__main__":
    unittest.main()
