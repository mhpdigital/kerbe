import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SERVE = REPO / "skills/rwalk/scripts/serve.py"
SCREEN_MD = REPO / "skills/rwalk/references/screen.md"
SCREEN_FILES = ("bundle.py", "serve.py", "discuss.py", "qr.py", "index.html")


class BreakGlassTest(unittest.TestCase):
    def test_terminal_walk_names_no_screen_script(self):
        for rel in ("skills/rwalk/SKILL.md", "skills/rwalk/references/recording.md"):
            text = (REPO / rel).read_text()
            for name in SCREEN_FILES:
                self.assertNotIn(name, text, f"{rel} must not depend on {name}")

    def test_skill_routes_screen_to_reference(self):
        text = (REPO / "skills/rwalk/SKILL.md").read_text()
        self.assertIn("--screen", text)
        self.assertIn("references/screen.md", text)

    def test_screen_reference_has_fallback(self):
        text = (REPO / "skills/rwalk/references/screen.md").read_text()
        self.assertIn("Screen failed: {error}. Continuing in the terminal.", text)

    def test_screen_serve_command_matches_argparse(self):
        """The serve.py command documented in screen.md uses only real flags and
        passes every required one, so the contract cannot drift from the script."""
        cmds = re.findall(r"`(scripts/serve\.py [^`]*)`", SCREEN_MD.read_text())
        self.assertEqual(len(cmds), 1, cmds)
        documented = set(re.findall(r"(?<![\w-])(--[a-z][a-z-]*)", cmds[0]))
        src = SERVE.read_text()
        known = set(re.findall(r'add_argument\("(--[a-z][a-z-]*)"', src))
        required = set(re.findall(r'add_argument\("(--[a-z][a-z-]*)", required=True', src))
        self.assertTrue(required, "no required flags found in serve.py")
        self.assertEqual(documented - known, set(), "screen.md names flags serve.py lacks")
        self.assertEqual(required - documented, set(), "screen.md omits required flags")

    def test_screen_reference_has_no_separate_bundle_step(self):
        self.assertNotIn("bundle.py", SCREEN_MD.read_text())

    def test_bug_pending_raised_before_nothing_to_walk(self):
        text = (REPO / "skills/rwalk/SKILL.md").read_text()
        raise_at = text.index("raise each `BUG PENDING` row")
        self.assertLess(raise_at, text.index("nothing to walk"))
        self.assertLess(raise_at, text.index("start the fix batch instead"))


if __name__ == "__main__":
    unittest.main()
