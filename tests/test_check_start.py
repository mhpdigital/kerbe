import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "fixtures" / "check_start.py"

SETTINGS = """# Demo — Slice Settings

```settings
design_required: true
```

## Notes

| Key | Set on | Reason / context |
|-----|--------|------------------|
| `design_required` | 2026-08-20 | design-driven, frame exists |
"""

UI = """# Demo — UI Element Catalogue

## Design sources

| Screen / frame | Node id | Measured (YYYY-MM-DD) |
|----------------|---------|-----------------------|
"""

TIMING = """# Demo — Timing

| Step | Skill | Run at (local) | Notes |
|------|-------|----------------|-------|
| 1. Start | `/kerbe:start` | 2026-08-20 14:05 | |
| 2. Design | `/kerbe:figma` | — | |
"""


def build(design="true", omit=()):
    root = pathlib.Path(tempfile.mkdtemp())
    sd = root / "planning" / "slices" / "demo"
    sd.mkdir(parents=True)
    files = {
        "SETTINGS.md": SETTINGS.replace(": true", ": " + design),
        "REQUIREMENTS.md": "# Demo — Requirements\n",
        "ENTITIES.md": "#\n", "ROUTES.md": "#\n", "SECURITY.md": "#\n",
        "DONE_CRITERIA.md": "#\n",
        "TIMING.md": TIMING if design == "true"
        else TIMING.replace("| — |", "| n/a (design_required: false) |", 1),
    }
    if design == "true":
        files["UI_ELEMENTS.md"] = UI
    for name, content in files.items():
        if name not in omit:
            (sd / name).write_text(content)
    (root / "planning" / "slices" / "INDEX.md").write_text(
        "| demo | planning | 2026-08-20 | |\n")
    return root


def run(root, design="true"):
    return subprocess.run([sys.executable, str(SCRIPT), str(root), "demo", design],
                          capture_output=True, text=True)


class CheckStartTest(unittest.TestCase):
    def test_complete_true_slice_passes(self):
        r = run(build("true"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_complete_false_slice_passes(self):
        r = run(build("false"), "false")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_missing_settings_fails(self):
        r = run(build("true", omit=("SETTINGS.md",)))
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL SETTINGS.md exists", r.stdout)

    def test_ui_elements_present_on_false_fails(self):
        root = build("false")
        (root / "planning" / "slices" / "demo" / "UI_ELEMENTS.md").write_text(UI)
        r = run(root, "false")
        self.assertEqual(r.returncode, 1)
        self.assertIn("UI_ELEMENTS.md omitted", r.stdout)

    def test_unstamped_timing_fails(self):
        root = build("true")
        p = root / "planning" / "slices" / "demo" / "TIMING.md"
        p.write_text(p.read_text().replace("2026-08-20 14:05", "—"))
        r = run(root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL TIMING row '1. Start' stamped", r.stdout)


if __name__ == "__main__":
    unittest.main()
