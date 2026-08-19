import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "coverage" / "scripts" / "verdict.py"

HEADER = """# Promise ledger — cards
LEDGER_VERSION: 1
MODE: {mode}
STATUS: FROZEN
SOURCES: docs@abc1234 · design@v42
EXTRACTION: converged (passes=3)

| id | promise | promised-by | spec | plan | code | evidence |
|----|---------|-------------|------|------|------|----------|
"""

FINISHED_AUDIT = HEADER.format(mode="audit") + """\
| P-001 | Card grid on index | figma:1:3 | doc:UI_ELEMENTS.md#grid | task:T1 index page | present | templates/card/index.html.twig:4 route card_index defined |
| P-002 | Detail description | req:REQ-CARD-002 | origin | task:T2 detail page | present | templates/card/detail.html.twig:7 |
"""

OPEN_AUDIT = HEADER.format(mode="audit") + """\
| P-001 | Card grid on index | figma:1:3 | doc:UI_ELEMENTS.md#grid | task:T1 index page | present | templates/card/index.html.twig:4 |
| P-002 | Download row | figma:2:2 | req:REQ-CARD-002 | task:T3 download row | absent | no template renders a download row |
| P-003 | Filter chips row | figma:1:4 | GAP | ? | ? | no spec doc mentions filter chips |
"""

FINISHED_PREIMPL = HEADER.format(mode="pre-impl") + """\
| P-001 | Card grid on index | figma:1:3 | doc:UI_ELEMENTS.md#grid | task:T1 index page | to-build | expected absent pre-impl |
"""

DUP_ID = HEADER.format(mode="audit") + """\
| P-001 | A | figma:1:3 | origin | task:T1 | present | a:1 |
| P-001 | B | figma:1:4 | origin | task:T1 | present | a:2 |
"""

BAD_VOCAB = HEADER.format(mode="audit") + """\
| P-001 | A | figma:1:3 | origin | task:T1 | missing | a:1 |
"""

NO_MODE = FINISHED_AUDIT.replace("MODE: audit\n", "")


def run(text):
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write(text)
    return subprocess.run([sys.executable, str(SCRIPT), f.name],
                          capture_output=True, text=True)


class VerdictTest(unittest.TestCase):
    def test_finished_audit_exits_0(self):
        r = run(FINISHED_AUDIT)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("FINISHED: YES", r.stdout)
        self.assertIn("promises: 2", r.stdout)

    def test_open_audit_exits_1_and_lists_open_rows(self):
        r = run(OPEN_AUDIT)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FINISHED: NO", r.stdout)
        self.assertIn("P-002", r.stdout)
        self.assertIn("P-003", r.stdout)
        self.assertNotIn("P-001", r.stdout.split("FINISHED")[1])

    def test_hop_counts(self):
        r = run(OPEN_AUDIT)
        self.assertIn("design->spec : 1 GAP", r.stdout)
        self.assertIn("1 present", r.stdout)
        self.assertIn("1 absent", r.stdout)

    def test_preimpl_tobuild_is_finished(self):
        r = run(FINISHED_PREIMPL)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("FINISHED: YES", r.stdout)

    def test_duplicate_id_is_malformed(self):
        r = run(DUP_ID)
        self.assertEqual(r.returncode, 2)
        self.assertIn("P-001", r.stderr)

    def test_bad_code_vocab_is_malformed(self):
        r = run(BAD_VOCAB)
        self.assertEqual(r.returncode, 2)
        self.assertIn("missing", r.stderr)

    def test_missing_mode_is_malformed(self):
        r = run(NO_MODE)
        self.assertEqual(r.returncode, 2)
        self.assertIn("MODE", r.stderr)


if __name__ == "__main__":
    unittest.main()
