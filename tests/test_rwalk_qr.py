import importlib.util
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
CHECKER = REPO / "fixtures" / "check_review.py"

_spec = importlib.util.spec_from_file_location("rwalk_qr", REPO / "skills" / "rwalk" / "scripts" / "qr.py")
qr_mod = importlib.util.module_from_spec(_spec)
sys.modules["rwalk_qr"] = qr_mod
_spec.loader.exec_module(qr_mod)
Verdict = qr_mod.Verdict

TEXT = """# Cards — Quality Reviews

> Code reviews recorded during development and review of this slice.

---

## QR-1 — Code Review: cards

**Branch:** `slice/cards`
**Date:** 2026-08-25
**Diff:** 3 files changed, 120 insertions, 4 deletions
**Review ID:** QR-1
**Reviewed at:** `a41c9e2`

---

### Summary

Card index + detail pages. Low risk overall; adversarial pass ran. Full suite green.

---

### Business-logic — read every line

| ID | File · concern (lines) | Why | Open |
|----|------|-----|------|
| B1 | `src/Controller/CardController.php` · `detail()` (L20–41) | ownership check decides who sees a card | `phpstorm --line 20 /abs/src/Controller/CardController.php` |
| B2 | `src/Repository/CardRepository.php` · `findVisibleFor()` (L10–30) | query filter scopes cards to the owner | `phpstorm --line 10 /abs/src/Repository/CardRepository.php` |

---

### Glue — read the flow, skip the syntax

| ID | File | What to check | Open |
|----|------|---------------|------|
| G1 | `src/Controller/CardController.php` (L5) | index route renders the right template | `phpstorm --line 5 /abs/src/Controller/CardController.php` |

---

### Boilerplate — don't read, trust the full suite

| File | What it does |
|------|-------------|
| `templates/card/index.html.twig` | card list markup |

---

### Flags

**F1 — Medium: draft cards readable by id** `src/Controller/CardController.php` L20-41 loads by id before any status check.
"""


def run_checker(text):
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "REVIEW.md"
        p.write_text(text)
        r = subprocess.run([sys.executable, str(CHECKER), str(p)], capture_output=True, text=True)
        return r.returncode, r.stdout


class QrTest(unittest.TestCase):
    def test_fixture_passes_checker(self):
        code, out = run_checker(TEXT)
        self.assertEqual(code, 0, out)

    def test_parse_rows_and_order(self):
        qr = qr_mod.parse(TEXT)[0]
        self.assertEqual([r.id for r in qr.rows], ["B1", "B2", "G1", "F1"])
        b1 = qr.rows[0]
        self.assertEqual((b1.file, b1.start, b1.end), ("src/Controller/CardController.php", 20, 41))
        self.assertEqual(qr.reviewed_at, "a41c9e2")
        g1 = qr.rows[2]
        self.assertEqual((g1.start, g1.end), (5, None))
        self.assertIsNone(qr.tier3_status)

    def test_verified_row_syntax(self):
        out = qr_mod.write_verdict(TEXT, "QR-1", "B1", Verdict("verified", mechanism="findVisibleFor() filters on owner"), "2026-10-20")
        row = next(l for l in out.splitlines() if l.startswith("| B1 "))
        self.assertIn("**RESOLVED (VERIFIED) 2026-10-20**", row)
        self.assertIn("Confirmed: findVisibleFor() filters on owner", row)
        self.assertTrue(row.startswith("| B1 | ~~"))
        self.assertTrue(row.endswith("~~ |"))
        self.assertTrue(qr_mod.is_closed(qr_mod.parse(out)[0].rows[0]))

    def test_fix_with_option_and_detail(self):
        v = Verdict("fix", option="O2: owner gets a restore page", detail="30-day window only\nno change to findVisibleFor()", proves="owner at 10 days gets 200")
        row = next(l for l in qr_mod.write_verdict(TEXT, "QR-1", "B1", v, "2026-10-20").splitlines() if l.startswith("| B1 "))
        self.assertIn("**FIX QUEUED 2026-10-20**", row)
        self.assertIn("~~ownership check decides who sees a card~~ Ruled: ", row)
        self.assertIn("Ruled: O2: owner gets a restore page<br>30-day window only<br>no change to findVisibleFor() · proves it: owner at 10 days gets 200", row)

    def test_fix_detail_is_cell_escaped(self):
        v = Verdict("fix", detail="use a | b\nthen `x`", proves="p")
        out = qr_mod.write_verdict(TEXT, "QR-1", "B1", v, "2026-10-20")
        row = next(l for l in out.splitlines() if l.startswith("| B1 "))
        self.assertIn("use a \\| b<br>then `x`", row)
        self.assertEqual(qr_mod.parse(out)[0].rows[0].status, "FIX QUEUED")

    def test_other_bytes_identical(self):
        out = qr_mod.write_verdict(TEXT, "QR-1", "B2", Verdict("defer", reason="later"), "2026-10-20")
        changed = [i for i, (a, b) in enumerate(zip(TEXT.splitlines(), out.splitlines())) if a != b]
        self.assertEqual(len(changed), 1)
        self.assertEqual(len(TEXT.splitlines()), len(out.splitlines()))
        self.assertIn("Deferred: later", out)
        self.assertIn("**DEFERRED 2026-10-20**", out)

    def test_flag_paragraph_bug_pending(self):
        out = qr_mod.write_verdict(TEXT, "QR-1", "F1", Verdict("bug", detail="drafts leak"), "2026-10-20")
        self.assertIn("**BUG PENDING 2026-10-20**", out)
        self.assertIn("Bug: drafts leak", out)
        self.assertTrue(qr_mod.is_decided(qr_mod.parse(out)[0].rows[3]))
        self.assertIn("**F1 — Medium: draft cards readable by id** ~~", out)

    def test_tier3_accept_line(self):
        out = qr_mod.write_verdict(TEXT, "QR-1", "tier3", Verdict("tier3"), "2026-10-20")
        self.assertRegex(out, r"### Boilerplate[^\n]*\n\n\*\*TIER 3 ACCEPTED 2026-10-20\*\* — 1 files")
        self.assertIn("behind the full suite", out)
        self.assertIsNotNone(qr_mod.parse(out)[0].tier3_status)
        with self.assertRaises(qr_mod.InvalidVerdict):
            qr_mod.write_verdict(out, "QR-1", "tier3", Verdict("tier3"), "2026-10-20")
        code, o = run_checker(out)
        self.assertEqual(code, 0, o)

    def test_tier3_uses_test_evidence(self):
        text = TEXT.replace("**Reviewed at:**", "**Test evidence:** 212 passed\n**Reviewed at:**")
        out = qr_mod.write_verdict(text, "QR-1", "tier3", Verdict("tier3"), "2026-10-20")
        self.assertIn("1 files, behind 212 passed", out)

    def test_unknown_row_and_closed_row_rejected(self):
        with self.assertRaises(qr_mod.UnknownRow):
            qr_mod.write_verdict(TEXT, "QR-1", "B9", Verdict("verified", mechanism="m"), "2026-10-20")
        with self.assertRaises(qr_mod.UnknownRow):
            qr_mod.write_verdict(TEXT, "QR-9", "B1", Verdict("verified", mechanism="m"), "2026-10-20")
        once = qr_mod.write_verdict(TEXT, "QR-1", "B1", Verdict("verified", mechanism="m"), "2026-10-20")
        with self.assertRaises(qr_mod.InvalidVerdict):
            qr_mod.write_verdict(once, "QR-1", "B1", Verdict("verified", mechanism="m"), "2026-10-20")

    def test_fix_needs_ruling_and_proof(self):
        with self.assertRaises(qr_mod.InvalidVerdict):
            qr_mod.write_verdict(TEXT, "QR-1", "B1", Verdict("fix", proves="p"), "2026-10-20")
        with self.assertRaises(qr_mod.InvalidVerdict):
            qr_mod.write_verdict(TEXT, "QR-1", "B1", Verdict("fix", detail="d"), "2026-10-20")

    def test_verified_needs_mechanism(self):
        with self.assertRaises(qr_mod.InvalidVerdict):
            qr_mod.write_verdict(TEXT, "QR-1", "B1", Verdict("verified"), "2026-10-20")

    def test_write_uses_current_text(self):
        edited = TEXT.replace("ownership check", "ownership check (edited in terminal)")
        out = qr_mod.write_verdict(edited, "QR-1", "B2", Verdict("verified", mechanism="m"), "2026-10-20")
        self.assertIn("(edited in terminal)", out)

    def test_current_qr(self):
        qrs = qr_mod.parse(TEXT)
        self.assertEqual(qr_mod.current_qr(qrs).id, "QR-1")
        text = TEXT
        for rid in ("B1", "B2", "G1"):
            text = qr_mod.write_verdict(text, "QR-1", rid, Verdict("defer", reason="r"), "2026-10-20")
        text = qr_mod.write_verdict(text, "QR-1", "F1", Verdict("bug", detail="d"), "2026-10-20")
        self.assertIsNone(qr_mod.current_qr(qr_mod.parse(text)))

    def test_written_review_still_passes_checker(self):
        out = qr_mod.write_verdict(TEXT, "QR-1", "B1", Verdict("verified", mechanism="m"), "2026-10-20")
        for rid, v in (("B2", Verdict("fix", option="o", proves="p")), ("G1", Verdict("defer", reason="r")),
                       ("F1", Verdict("verified", mechanism="m"))):
            out = qr_mod.write_verdict(out, "QR-1", rid, v, "2026-10-20")
        code, o = run_checker(out)
        self.assertEqual(code, 0, o)

    def test_escape_cell(self):
        self.assertEqual(qr_mod.escape_cell("a | b\nc"), "a \\| b<br>c")


if __name__ == "__main__":
    unittest.main()
