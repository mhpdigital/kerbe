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
