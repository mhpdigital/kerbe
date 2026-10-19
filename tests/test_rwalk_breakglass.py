import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
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
        self.assertIn("Continuing in the terminal", text)


if __name__ == "__main__":
    unittest.main()
