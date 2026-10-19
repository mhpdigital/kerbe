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
        self.assertEqual(qr.tier3_files, 1)

    def test_tier3_files_empty_and_absent(self):
        head, rest = TEXT.split("| `templates/card/index.html.twig` | card list markup |\n")
        self.assertEqual(qr_mod.parse(head + rest)[0].tier3_files, 0)
        no_sec = TEXT.split("### Boilerplate")[0] + "### Flags" + TEXT.split("### Flags")[1]
        self.assertEqual(qr_mod.parse(no_sec)[0].tier3_files, 0)
        two = TEXT.replace("| card list markup |\n", "| card list markup |\n| `a---b.twig` | dashes |\n")
        self.assertEqual(qr_mod.parse(two)[0].tier3_files, 2)

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

    # ---- fix round 1 ----
    def _flags_text(self, flags):
        return TEXT.split("### Flags\n")[0] + "### Flags\n\n" + flags

    def test_wrapped_flag_head_and_inner_bold(self):
        text = self._flags_text(
            "**F1 — Medium: draft cards are readable by id when the\nowner has not published them yet** `src/Controller/CardController.php:20-41` loads first.\n\n"
            "**F2 — Low: what a deck with **no cards** shows.** `templates/card/index.html.twig` L3 renders empty.\n")
        rows = qr_mod.parse(text)[0].rows
        self.assertEqual([r.id for r in rows], ["B1", "B2", "G1", "F1", "F2"])
        self.assertEqual((rows[3].file, rows[3].start, rows[3].end), ("src/Controller/CardController.php", 20, 41))
        out = qr_mod.write_verdict(text, "QR-1", "F2", Verdict("verified", mechanism="m"), "2026-10-20")
        self.assertIn("**F2 — Low: what a deck with **no cards** shows.** ~~`templates/card/index.html.twig` L3 renders empty.~~ **RESOLVED (VERIFIED) 2026-10-20** Confirmed: m", out)
        out = qr_mod.write_verdict(text, "QR-1", "F1", Verdict("verified", mechanism="m"), "2026-10-20")
        self.assertEqual(qr_mod.parse(out)[0].rows[3].status, "RESOLVED (VERIFIED)")
        self.assertIsNone(qr_mod.parse(out)[0].rows[4].status)

    def test_adjacent_flags_do_not_absorb(self):
        tail = ("**F2 — Low: empty deck page** `templates/card/index.html.twig` L3 renders empty.\n"
                "Verified safe: the index route is read-only.\n")
        text = self._flags_text("**F1 — Medium: draft cards readable by id** `src/Controller/CardController.php` L20 loads first.\n" + tail)
        self.assertEqual([r.id for r in qr_mod.parse(text)[0].rows][-2:], ["F1", "F2"])
        out = qr_mod.write_verdict(text, "QR-1", "F1", Verdict("bug", detail="d"), "2026-10-20")
        self.assertTrue(out.endswith(tail))
        self.assertIsNone(qr_mod.parse(out)[0].rows[4].status)

    def test_crlf_file(self):
        text = TEXT.replace("\n", "\r\n")
        for rid, v in (("B1", Verdict("verified", mechanism="m")), ("F1", Verdict("bug", detail="d")),
                       ("tier3", Verdict("tier3"))):
            out = qr_mod.write_verdict(text, "QR-1", rid, v, "2026-10-20")
            self.assertNotRegex(out, r"(?<!\r)\n", rid)
            self.assertTrue(out.startswith(text.split("### Business")[0]))
        out = qr_mod.write_verdict(text, "QR-1", "B2", Verdict("defer", reason="r"), "2026-10-20")
        a, b = text.splitlines(keepends=True), out.splitlines(keepends=True)
        self.assertEqual([i for i, (x, y) in enumerate(zip(a, b)) if x != y].__len__(), 1)
        self.assertEqual(len(a), len(b))

    def test_status_only_from_concern_cell(self):
        text = TEXT.replace("query filter scopes cards", "**EXPECTED** query filter scopes cards")
        row = qr_mod.parse(text)[0].rows[1]
        self.assertIsNone(row.status)
        out = qr_mod.write_verdict(text, "QR-1", "B2", Verdict("verified", mechanism="m"), "2026-10-20")
        self.assertEqual(qr_mod.parse(out)[0].rows[1].status, "RESOLVED (VERIFIED)")

    def test_file_and_line_extraction(self):
        text = TEXT.replace(
            "`src/Repository/CardRepository.php` · `findVisibleFor()` (L10–30)",
            "`try`/`catch (Throwable)` in `src/Repository/CardRepository.php:267` and `.cards__actions` (L10–30)")
        r = qr_mod.parse(text)[0].rows[1]
        self.assertEqual((r.file, r.start, r.end), ("src/Repository/CardRepository.php", 267, None))
        text = TEXT.replace("`src/Repository/CardRepository.php`", "`slice/cards` `.cards__actions` `src/Repository/CardRepository.php`")
        r = qr_mod.parse(text)[0].rows[1]
        self.assertEqual((r.file, r.start, r.end), ("src/Repository/CardRepository.php", 10, 30))

    def test_flag_line_ref_tied_to_file_span(self):
        text = self._flags_text("**F1 — Medium: weak test** `tests/Controller/CardControllerTest.php:120-135` only checks 200, see also L300.\n")
        r = qr_mod.parse(text)[0].rows[3]
        self.assertEqual((r.file, r.start, r.end), ("tests/Controller/CardControllerTest.php", 120, 135))

    def test_escape_neutralises_markup(self):
        out = qr_mod.write_verdict(TEXT, "QR-1", "B1", Verdict("verified", mechanism="was **FIXED x** and ~~y"), "2026-10-20")
        self.assertEqual(qr_mod.parse(out)[0].rows[0].status, "RESOLVED (VERIFIED)")
        row = next(l for l in out.splitlines() if l.startswith("| B1 "))
        self.assertIn("\\*\\*FIXED x\\*\\*", row)
        self.assertIn("\\~\\~y", row)
        self.assertEqual(row.count("~~") % 2, 0)

    def test_pre_escaped_pipe_row(self):
        text = TEXT.replace("query filter scopes cards to the owner", "query filter a \\| b scopes cards")
        self.assertEqual(len(qr_mod.parse(text)[0].rows), 4)
        out = qr_mod.write_verdict(text, "QR-1", "B2", Verdict("verified", mechanism="m"), "2026-10-20")
        self.assertIn("a \\| b scopes cards~~ Confirmed: m", out)
        self.assertEqual(len(qr_mod.parse(out)[0].rows), 4)

    def _two_qrs(self):
        head, body = TEXT.split("## QR-1", 1)
        return head + "## QR-1" + body + "\n---\n\n## QR-2" + body.replace("QR-1", "QR-2", 1).replace("**Review ID:** QR-1", "**Review ID:** QR-2")

    def test_same_row_id_in_two_qrs(self):
        text = self._two_qrs()
        self.assertEqual([q.id for q in qr_mod.parse(text)], ["QR-1", "QR-2"])
        out = qr_mod.write_verdict(text, "QR-2", "B1", Verdict("verified", mechanism="m"), "2026-10-20")
        qrs = qr_mod.parse(out)
        self.assertIsNone(qrs[0].rows[0].status)
        self.assertEqual(qrs[1].rows[0].status, "RESOLVED (VERIFIED)")
        out2 = qr_mod.write_verdict(text, "QR-1", "tier3", Verdict("tier3"), "2026-10-20")
        qrs = qr_mod.parse(out2)
        self.assertIsNotNone(qrs[0].tier3_status)
        self.assertIsNone(qrs[1].tier3_status)

    def test_current_qr_is_newest_with_open_row(self):
        text = self._two_qrs()
        self.assertEqual(qr_mod.current_qr(qr_mod.parse(text)).id, "QR-2")
        for rid in ("B1", "B2", "G1"):
            text = qr_mod.write_verdict(text, "QR-2", rid, Verdict("defer", reason="r"), "2026-10-20")
        text = qr_mod.write_verdict(text, "QR-2", "F1", Verdict("bug", detail="d"), "2026-10-20")
        self.assertEqual(qr_mod.current_qr(qr_mod.parse(text)).id, "QR-1")

    def test_flag_head_ending_in_quote(self):
        text = self._flags_text('**F1 — Low: the "draft"** `src/Controller/CardController.php` L20 loads first.\n')
        self.assertEqual(qr_mod.parse(text)[0].rows[3].file, "src/Controller/CardController.php")
        out = qr_mod.write_verdict(text, "QR-1", "F1", Verdict("verified", mechanism="m"), "2026-10-20")
        self.assertIn('**F1 — Low: the "draft"** ~~', out)
        self.assertEqual(qr_mod.parse(out)[0].rows[3].status, "RESOLVED (VERIFIED)")
        with self.assertRaisesRegex(qr_mod.InvalidVerdict, "already"):
            qr_mod.write_verdict(out, "QR-1", "F1", Verdict("verified", mechanism="m"), "2026-10-20")

    def test_flag_without_closing_bold_refuses(self):
        text = self._flags_text("**F1 — Low: head never closes `src/Controller/CardController.php` L20 loads first.\n")
        self.assertEqual(qr_mod.parse(text)[0].rows[3].id, "F1")
        with self.assertRaises(qr_mod.InvalidVerdict):
            qr_mod.write_verdict(text, "QR-1", "F1", Verdict("verified", mechanism="m"), "2026-10-20")


if __name__ == "__main__":
    unittest.main()
