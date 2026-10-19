import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "rwalk" / "scripts"))
import discuss  # noqa: E402

ROW = {
    "id": "B1", "tier": "B", "title": "Card expiry check",
    "file": "src/cards/expiry.py", "start": 10, "end": 14,
    "why": "Expired cards must be rejected",
    "status": None,
    "diff": [
        {"t": "c", "old": 9, "new": 9, "text": "def check(card):", "in": False},
        {"t": "a", "old": None, "new": 10, "text": "    return card.expiry > today", "in": True},
    ],
}
ROW10 = dict(ROW, id="B10", title="Other row")
ROW2 = dict(ROW, id="B2", title="Second row")


def script(tmp, name, body):
    p = Path(tmp) / name
    p.write_text(textwrap.dedent(body), encoding="utf-8")
    return p


class DiscussTest(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.addCleanup(self._td.cleanup)
        self.tmp = Path(self._td.name)
        self.echo = script(self.tmp, "echo.py", "import sys\nsys.stdout.write(sys.stdin.read())\n")
        self.sleeper = script(self.tmp, "sleeper.py", "import time\ntime.sleep(30)\n")
        self.failer = script(self.tmp, "failer.py", "import sys\nsys.stderr.write('boom\\n')\nsys.exit(3)\n")
        self.silent_fail = script(self.tmp, "silent.py", "import sys\nsys.exit(4)\n")

    def test_parse_options(self):
        body, opts = discuss.parse_options("It returns 404.\nOptions:\nO0: keep it\nO1: 410 Gone\nO2: restore page")
        self.assertEqual(opts, [("O0", "keep it"), ("O1", "410 Gone"), ("O2", "restore page")])
        self.assertEqual(body.strip(), "It returns 404.\nOptions:")

    def test_no_options(self):
        self.assertEqual(discuss.parse_options("plain")[1], [])

    def test_mid_text_option_mention_not_parsed(self):
        text = "Earlier I said\nO1: not an option\nbut the answer is plain."
        body, opts = discuss.parse_options(text)
        self.assertEqual(opts, [])
        self.assertEqual(body, text)

    def test_prompt_replays_history(self):
        p = discuss.build_prompt(ROW, [("q1", "a1")], "q2", "ask")
        self.assertLess(p.index("q1"), p.index("a1"))
        self.assertLess(p.index("a1"), p.index("q2"))
        self.assertIn("O0:", p)

    def test_prompt_describes_row(self):
        p = discuss.build_prompt(ROW, [], "why?", "ask")
        for s in ("B1", "Card expiry check", "src/cards/expiry.py", "Expired cards must be rejected",
                  "return card.expiry > today"):
            self.assertIn(s, p)
        self.assertIn("+    return card.expiry > today", p)
        self.assertNotIn("def check(card):", p)

    def test_prompt_without_in_lines_shows_all_but_headers(self):
        row = dict(ROW, diff=[
            {"t": "h", "old": None, "new": None, "text": "@@ -9 +9 @@", "in": False},
            {"t": "c", "old": 9, "new": 9, "text": "keep", "in": False},
            {"t": "d", "old": 10, "new": None, "text": "gone", "in": False},
            {"t": "a", "old": None, "new": 10, "text": "fresh", "in": False}])
        p = discuss.build_prompt(row, [], "q", "ask")
        self.assertIn(" keep\n-gone\n+fresh", p)
        self.assertNotIn("@@", p)

    def test_missing_cwd(self):
        ok, out = discuss.run(f"{sys.executable} {self.echo}", "x", self.tmp / "nope")
        self.assertFalse(ok)
        self.assertIn("working directory not found", out)

    def test_answer_heading_on_first_and_indented_lines(self):
        path = self.tmp / "d.md"
        discuss.append_discussion(path, "QR-1", ROW, "q", "## first\n   ### deep\n    ## code", "t")
        text = path.read_text(encoding="utf-8")
        self.assertIn("**Agent:** \\## first", text)
        self.assertIn("   \\### deep", text)
        self.assertIn("    ## code", text)
        self.assertEqual([l for l in text.splitlines() if l.startswith("#")],
                         ["## QR-1/B1 — Card expiry check"])

    def test_preread_has_no_option_instruction(self):
        p = discuss.build_prompt(ROW, [], "", "preread")
        self.assertNotIn("O0:", p)
        self.assertIn("two sentences", p)

    def test_run_passes_stdin(self):
        ok, out = discuss.run(f"{sys.executable} {self.echo}", "hello", self.tmp)
        self.assertTrue(ok)
        self.assertIn("hello", out)

    def test_timeout_returns_error(self):
        ok, out = discuss.run(f"{sys.executable} {self.sleeper}", "x", self.tmp, timeout=1)
        self.assertFalse(ok)
        self.assertIn("timed out", out)

    def test_missing_command_returns_error(self):
        ok, out = discuss.run("no-such-binary-kerbe", "x", self.tmp)
        self.assertFalse(ok)
        self.assertIn("not found", out)

    def test_nonzero_exit_returns_stderr(self):
        ok, out = discuss.run(f"{sys.executable} {self.failer}", "x", self.tmp)
        self.assertFalse(ok)
        self.assertIn("boom", out)

    def test_nonzero_exit_without_stderr(self):
        ok, out = discuss.run(f"{sys.executable} {self.silent_fail}", "x", self.tmp)
        self.assertFalse(ok)
        self.assertEqual(out, "exit 4")

    def test_empty_and_malformed_cmd(self):
        for cmd in ("", "   ", "'unterminated"):
            ok, out = discuss.run(cmd, "x", self.tmp)
            self.assertFalse(ok, cmd)
            self.assertTrue(out)

    def test_append_discussion_groups_by_row(self):
        path = self.tmp / "REVIEW-discussion.md"
        discuss.append_discussion(path, "QR-1", ROW, "q1", "a1", "10:00")
        discuss.append_discussion(path, "QR-1", ROW2, "q2", "a2", "10:01")
        discuss.append_discussion(path, "QR-1", ROW, "q3", "a3", "10:02")
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count("## QR-1/B1 — "), 1)
        self.assertEqual(text.count("## QR-1/B2 — "), 1)
        self.assertIn("**You (10:00):** q1", text)
        self.assertIn("**Agent:** a1", text)
        b1, b2 = text.index("## QR-1/B1 — "), text.index("## QR-1/B2 — ")
        self.assertTrue(b1 < text.index("q1") < text.index("q3") < b2 < text.index("q2"))

    def test_b1_does_not_match_b10(self):
        path = self.tmp / "d.md"
        discuss.append_discussion(path, "QR-1", ROW10, "qten", "aten", "t")
        discuss.append_discussion(path, "QR-1", ROW, "qone", "aone", "t")
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count("## QR-1/B1 — "), 1)
        self.assertEqual(text.count("## QR-1/B10 — "), 1)
        self.assertTrue(text.index("qten") < text.index("## QR-1/B1 — ") < text.index("qone"))

    def test_crlf_preserved(self):
        path = self.tmp / "d.md"
        path.write_bytes(b"## QR-1/B1 \xe2\x80\x94 Card\r\n\r\n**You (t):** old\r\n\r\n**Agent:** older\r\n")
        discuss.append_discussion(path, "QR-1", ROW, "new q", "line1\nline2", "t2")
        raw = path.read_bytes()
        self.assertNotIn(b"\r\r", raw)
        self.assertEqual(raw.replace(b"\r\n", b"").count(b"\n"), 0)
        self.assertIn(b"new q", raw)

    def test_lf_stays_lf(self):
        path = self.tmp / "d.md"
        discuss.append_discussion(path, "QR-1", ROW, "q", "a", "t")
        self.assertNotIn(b"\r", path.read_bytes())

    def test_answer_heading_line_escaped(self):
        path = self.tmp / "d.md"
        discuss.append_discussion(path, "QR-1", ROW, "q", "intro\n## QR-1/B2 — fake\ntail", "t")
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("\n## QR-1/B2", text)
        self.assertIn("\\## QR-1/B2 — fake", text)
        self.assertEqual([l for l in text.splitlines() if l.startswith("## ")],
                         ["## QR-1/B1 — Card expiry check"])

    def test_question_newlines_collapsed(self):
        path = self.tmp / "d.md"
        discuss.append_discussion(path, "QR-1", ROW, "a\n## injected\nb", "ans", "t")
        text = path.read_text(encoding="utf-8")
        self.assertEqual([l for l in text.splitlines() if l.startswith("## ")],
                         ["## QR-1/B1 — Card expiry check"])
        self.assertIn("**You (t):** a ## injected b", text)

    def test_inserts_before_next_heading(self):
        path = self.tmp / "d.md"
        path.write_text("## QR-1/B1 — Card\n\n**You (t):** old\n\n**Agent:** older\n\n## QR-1/B2 — Next\n\nkeep\n",
                        encoding="utf-8")
        discuss.append_discussion(path, "QR-1", ROW, "newq", "newa", "t2")
        text = path.read_text(encoding="utf-8")
        self.assertTrue(text.index("older") < text.index("newq") < text.index("## QR-1/B2"))
        self.assertTrue(text.endswith("keep\n"))
        self.assertIn("newa\n\n## QR-1/B2", text)


if __name__ == "__main__":
    unittest.main()
