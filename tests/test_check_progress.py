import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "fixtures" / "check_progress.py"

GOOD = """# Cards — Implementation Progress

**Slice:** cards
**Workspace:** ~/projects/demo-cards  ·  **Branch:** slice/cards
**Plan:** planning/slices/cards/PLAN.md  ·  **Started:** 2026-08-20
**Executor:** claude  ·  **Shape:** group
**Tests:** 12 passing, 0 failing (`php vendor/bin/phpunit`, 2026-08-20)

## Position
| Plan task | Status | Worker | Evidence |
|---|---|---|---|
| Task 1: index route | done | W-A | a1b2c3d · full suite 12/0 pasted |
| Task 2: detail template | in progress | W-B | — |

## Worker A: routing
- [ ] Task 1
**Owns:** `src/Controller/CardController.php`, `tests/Controller/CardControllerTest.php`

## Worker B: templates
- [ ] Task 2
**Owns:** `templates/card/index.html.twig`

## Blockers

## Files touched this session
- src/Controller/CardController.php
"""

PLAN = """# Cards — Implementation Plan

### Task 1: index route
### Task 2: detail template
"""


def run(text, plan=None):
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "claude-progress.md"
        p.write_text(text)
        args = [sys.executable, str(SCRIPT), str(p)]
        if plan is not None:
            pl = pathlib.Path(d) / "PLAN.md"
            pl.write_text(plan)
            args.append(str(pl))
        r = subprocess.run(args, capture_output=True, text=True)
        return r.returncode, r.stdout


class CheckProgressTest(unittest.TestCase):
    def test_good_tracker_passes(self):
        code, out = run(GOOD)
        self.assertEqual(code, 0, out)

    def test_done_without_evidence_fails(self):
        code, out = run(GOOD.replace("| done | W-A | a1b2c3d · full suite 12/0 pasted |",
                                     "| done | W-A | — |"))
        self.assertEqual(code, 1)
        self.assertIn("done row carries evidence", out)

    def test_overlapping_ownership_fails(self):
        code, out = run(GOOD.replace("**Owns:** `templates/card/index.html.twig`",
                                     "**Owns:** `src/Controller/CardController.php`"))
        self.assertEqual(code, 1)
        self.assertIn("ownership is disjoint", out)

    def test_missing_header_fails(self):
        code, out = run(GOOD.replace("**Plan:**", "**Planfile:**"))
        self.assertEqual(code, 1)
        self.assertIn("header records Plan", out)

    def test_task_coverage_against_plan(self):
        code, out = run(GOOD, plan=PLAN + "\n### Task 3: styles\n")
        self.assertEqual(code, 1)
        self.assertIn("a position row per plan task", out)

    def test_task_coverage_matching_plan_passes(self):
        code, out = run(GOOD, plan=PLAN)
        self.assertEqual(code, 0, out)

    def test_hidden_dotfolder_fails(self):
        with tempfile.TemporaryDirectory() as d:
            hidden = pathlib.Path(d) / ".superpowers"
            hidden.mkdir()
            p = hidden / "claude-progress.md"
            p.write_text(GOOD)
            r = subprocess.run([sys.executable, str(SCRIPT), str(p)],
                               capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("not in a hidden dotfolder", r.stdout)


if __name__ == "__main__":
    unittest.main()
