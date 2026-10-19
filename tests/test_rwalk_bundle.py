import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

from tests.test_rwalk_qr import TEXT

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "rwalk" / "scripts" / "bundle.py"
_spec = importlib.util.spec_from_file_location("rwalk_bundle", SCRIPT)
bundle = importlib.util.module_from_spec(_spec)
sys.modules["rwalk_bundle"] = bundle
_spec.loader.exec_module(bundle)

CTRL = "src/Controller/CardController.php"


class BundleTest(unittest.TestCase):
    def git(self, *args):
        r = subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t",
                            "-c", "user.email=t@example.com", *args],
                           capture_output=True, text=True, check=True)
        return r.stdout.strip()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = pathlib.Path(self._tmp.name)
        self.git("init", "-q", "-b", "main")
        f = self.repo / CTRL
        f.parent.mkdir(parents=True)
        f.write_text("".join("line %d\n" % n for n in range(1, 41)))
        self.git("add", CTRL)
        self.git("commit", "-q", "-m", "base")
        self.git("checkout", "-q", "-b", "slice/cards")
        f.write_text("".join(("changed %d\n" if 20 <= n <= 24 else "line %d\n") % n
                             for n in range(1, 41)))
        self.git("add", CTRL)
        self.git("commit", "-q", "-m", "change")
        sha = self.git("rev-parse", "--short", "HEAD")
        self.review = self.repo / "REVIEW.md"
        self.review.write_text(TEXT.replace("a41c9e2", sha))
        self.bundle = bundle.build(self.review, self.repo, "main", "cards")

    def row(self, rid):
        return next(r for r in self.bundle["rows"] if r["id"] == rid)

    def test_rows_and_meta(self):
        b = self.bundle
        self.assertEqual(b["qr"], "QR-1")
        self.assertEqual([r["id"] for r in b["rows"]], ["B1", "B2", "G1", "F1"])
        self.assertEqual(b["slice"], "cards")
        self.assertEqual(b["tier3"], {"status": None, "files": 1})

    def test_row_diff_marks_in_range(self):
        d = self.row("B1")["diff"]
        self.assertTrue(any(l["t"] == "a" and l["in"] for l in d))
        self.assertEqual(d[0]["t"], "h")
        for l in d[1:]:
            if l["new"] is not None and not 20 <= l["new"] <= 41:
                self.assertFalse(l["in"], l)

    def test_row_outside_hunks_shows_context(self):
        d = self.row("G1")["diff"]   # G1 cites L5, outside the changed hunk
        self.assertTrue(d and all(l["t"] == "c" for l in d))
        self.assertEqual(d[0]["new"], 5)

    def test_missing_file_header(self):
        # B2's file was never committed
        self.assertIn("not present", self.row("B2")["diff"][0]["text"])

    def test_cli_writes_json(self):
        with tempfile.TemporaryDirectory() as d:
            out = pathlib.Path(d) / "bundle.json"
            r = subprocess.run([sys.executable, str(SCRIPT), "--review", str(self.review),
                                "--repo", str(self.repo), "--base", "main",
                                "--slice", "cards", "--out", str(out)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(out.read_text())["qr"], "QR-1")

    # ---- fix round 1 ----
    def commit_pair(self, name, old, new):
        """Commit old then new content of `name`; return (old_sha, new_sha)."""
        f = self.repo / name
        f.write_bytes(old)
        self.git("add", name)
        self.git("commit", "-q", "-m", "old " + name)
        a = self.git("rev-parse", "HEAD")
        f.write_bytes(new)
        self.git("add", name)
        self.git("commit", "-q", "-m", "new " + name)
        return a, self.git("rev-parse", "HEAD")

    def mkrow(self, file, start, end=None):
        return bundle.qr_mod.Row("QR-1", "B9", "B", "t", file, start, end, "w", None, 1)

    @staticmethod
    def nums(n, repl=None):
        repl = repl or {}
        return "".join(repl.get(i, "line %d" % i) + "\n" for i in range(1, n + 1)).encode()

    def test_hunk_header_without_count(self):
        a, b = self.commit_pair("one.txt", b"a\n", b"b\n")
        d = bundle._row_diff(self.repo, a, b, self.mkrow("one.txt", 1))
        self.assertIn("@@ -1 +1 @@", d[0]["text"])
        self.assertEqual([l["t"] for l in d], ["h", "d", "a"])
        self.assertTrue(d[2]["in"])

    def test_no_newline_marker_skipped(self):
        a, b = self.commit_pair("nn.txt", b"a\nb", b"a\nc")
        d = bundle._row_diff(self.repo, a, b, self.mkrow("nn.txt", 2))
        self.assertEqual([l["text"] for l in d[1:]], ["a", "b", "c"])
        self.assertFalse(any("No newline" in l["text"] for l in d))

    def test_deleted_lines_and_in_marking(self):
        old = self.nums(40)
        new = self.nums(40, {})
        new = b"".join(l for i, l in enumerate(old.splitlines(True), 1) if i not in (20, 21))
        a, b = self.commit_pair("del.txt", old, new)
        d = bundle._row_diff(self.repo, a, b, self.mkrow("del.txt", 20, 20))
        dels = [l for l in d if l["t"] == "d"]
        self.assertEqual([l["old"] for l in dels], [20, 21])
        self.assertTrue(all(l["new"] is None for l in dels))
        self.assertTrue(all(l["in"] for l in dels))  # both sit at new position 20
        far = bundle._row_diff(self.repo, a, b, self.mkrow("del.txt", 25, 26))
        self.assertFalse(any(l["in"] for l in far if l["t"] == "d"))

    def test_end_none_marks_only_start(self):
        d = bundle._row_diff(self.repo, "main", "HEAD", self.mkrow(CTRL, 21))
        self.assertEqual([l["new"] for l in d if l.get("in")], [21])

    def test_out_of_window_hunk_dropped(self):
        old = self.nums(80)
        a, b = self.commit_pair("far.txt", old, self.nums(80, {5: "X5", 60: "X60"}))
        d = bundle._row_diff(self.repo, a, b, self.mkrow("far.txt", 60, 60))
        self.assertEqual(sum(1 for l in d if l["t"] == "h"), 1)
        self.assertTrue(any(l["text"] == "X60" for l in d))
        self.assertFalse(any(l["text"] == "X5" for l in d))

    def test_missing_reviewed_at_uses_head(self):
        text = TEXT.replace("**Reviewed at:** `a41c9e2`\n", "")
        self.review.write_text(text)
        b = bundle.build(self.review, self.repo, "main", "cards")
        self.assertIsNone(b["reviewed_at"])
        self.assertEqual(b["rows"][0]["diff"], self.row("B1")["diff"])

    def test_row_without_file_has_empty_diff(self):
        self.assertEqual(bundle._row_diff(self.repo, "main", "HEAD", self.mkrow(None, 3)), [])

    def test_file_with_no_diff_gives_context(self):
        sha = self.git("rev-parse", "HEAD")
        d = bundle._row_diff(self.repo, sha, sha, self.mkrow(CTRL, 3, 5))
        self.assertEqual([(l["t"], l["new"], l["in"]) for l in d],
                         [("c", 3, True), ("c", 4, True), ("c", 5, True)])
        self.assertEqual(d[0]["text"], "line 3")

    def test_start_past_eof(self):
        sha = self.git("rev-parse", "HEAD")
        d = bundle._row_diff(self.repo, sha, sha, self.mkrow(CTRL, 500))
        self.assertEqual(d, [{"t": "h", "text": "line 500 out of range"}])

    def test_form_feed_stays_one_line(self):
        a, b = self.commit_pair("ff.txt", self.nums(10), self.nums(10, {3: "x\x0cy"}))
        d = bundle._row_diff(self.repo, a, b, self.mkrow("ff.txt", 3, 6))
        added = [l for l in d if l["t"] == "a"]
        self.assertEqual([(l["new"], l["text"]) for l in added], [(3, "x\x0cy")])
        self.assertEqual([l["new"] for l in d if l["t"] == "c" and l["new"] > 3][:2], [4, 5])

    def test_bad_refs_raise(self):
        with self.assertRaises(bundle.BundleError):
            bundle.build(self.review, self.repo, "nope", "cards")
        with self.assertRaisesRegex(bundle.BundleError, "must not start"):
            bundle.build(self.review, self.repo, "--output=x", "cards")
        self.review.write_text(TEXT.replace("a41c9e2", "deadbee"))
        with self.assertRaises(bundle.BundleError):
            bundle.build(self.review, self.repo, "main", "cards")
        with tempfile.TemporaryDirectory() as d:
            self.review.write_text(TEXT.replace("a41c9e2", "HEAD"))
            with self.assertRaises(bundle.BundleError):
                bundle.build(self.review, pathlib.Path(d), "main", "cards")

    def test_cli_missing_review_exits_2(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(SCRIPT), "--review", str(pathlib.Path(d) / "nope.md"),
                                "--repo", str(self.repo), "--base", "main", "--slice", "cards",
                                "--out", str(pathlib.Path(d) / "o.json")],
                               capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertTrue(r.stderr.startswith("error:"), r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_no_current_qr_raises_bundle_error(self):
        self.review.write_text("# Review\n\nNo quality review here.\n")
        with self.assertRaisesRegex(bundle.BundleError, "no open quality review"):
            bundle.build(self.review, self.repo, "main", "cards")


if __name__ == "__main__":
    unittest.main()
