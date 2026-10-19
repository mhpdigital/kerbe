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


if __name__ == "__main__":
    unittest.main()
