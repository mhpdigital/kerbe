import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "fixtures" / "check_review.py"

GOOD = """# Cards — Quality Reviews

> Code reviews recorded during development and review of this slice.

---

## QR-1 — Code Review: cards

**Branch:** `slice/cards`
**Date:** 2026-08-25
**Diff:** 3 files changed, 120 insertions, 4 deletions
**Review ID:** QR-1

---

### Summary

Card index + detail pages. Low risk overall; adversarial pass ran. Full suite green.

---

### Business-logic — read every line

| File · concern (lines) | Why | Open |
|------|-----|------|
| `src/Controller/CardController.php` · `detail()` (L20–41) | ownership check decides who sees a card | `phpstorm --line 20 /abs/src/Controller/CardController.php` |

---

### Glue — read the flow, skip the syntax

| File | What to check | Open |
|------|---------------|------|
| `src/Controller/CardController.php` | index route renders the right template | `phpstorm --line 12 /abs/src/Controller/CardController.php` |

---

### Boilerplate — don't read, trust the full suite

| File | What it does |
|------|-------------|
| `templates/card/index.html.twig` | card list markup |

---

### Flags

None.
"""


def run(text, *args):
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "REVIEW.md"
        p.write_text(text)
        r = subprocess.run([sys.executable, str(SCRIPT), str(p), *args],
                           capture_output=True, text=True)
        return r.returncode, r.stdout


class CheckReviewTest(unittest.TestCase):
    def test_good_review_passes(self):
        code, out = run(GOOD)
        self.assertEqual(code, 0, out)
        self.assertIn("ALL PASS", out)

    def test_coverage_arg_catches_dropped_file(self):
        code, out = run(GOOD, "src/Controller/CardController.php,src/Service/Mystery.php")
        self.assertEqual(code, 1)
        self.assertIn("silently dropped", out)

    def test_flags_not_last_fails(self):
        code, out = run(GOOD + "\n### Afterthoughts\n\nmore\n")
        self.assertEqual(code, 1)
        self.assertIn("Flags last", out)

    def test_tier1_row_without_lines_fails(self):
        bad = GOOD.replace("`detail()` (L20–41)", "`detail()`").replace(
            "`phpstorm --line 20 /abs/src/Controller/CardController.php`", "`phpstorm /abs/x.php`")
        code, out = run(bad)
        self.assertEqual(code, 1)
        self.assertIn("line reference", out)

    def test_missing_section_fails(self):
        code, out = run(GOOD.replace("### Glue — read the flow, skip the syntax", "### Wiring"))
        self.assertEqual(code, 1)
        self.assertIn("all five sections", out)

    def test_non_sequential_qr_fails(self):
        code, out = run(GOOD.replace("QR-1", "QR-3"))
        self.assertEqual(code, 1)
        self.assertIn("sequential", out)

    def test_check_prefix_forbidden(self):
        code, out = run(GOOD.replace("None.", "✅ all clear"))
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
