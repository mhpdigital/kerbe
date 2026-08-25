import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "coverage" / "scripts" / "dc_extract.py"

spec = importlib.util.spec_from_file_location("dc_extract", SCRIPT)
dc_extract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc_extract)

ARTBOARD = """<!doctype html>
<html><head><meta charset="utf-8"><script src="./support.js"></script></head>
<body>
<x-dc>
<helmet><style>body { margin: 0 } a { color: #b45309 }</style></helmet>
<div style="padding: 32px">
  <h1>aus4 / php8.1 — 47 sites down</h1>
  <pre id="command-preview">systemctl reload php8.1-fpm</pre>
  <form id="ack-form" method="post">
    <input type="hidden" name="intent" value="ack">
    <button id="ack-button" type="submit" style="height: 44px">Acknowledge</button>
  </form>
  <form id="act-form" method="post">
    <button type="submit">Reload PHP-FPM now</button>
  </form>
  <sc-if value="{{used}}" hint-placeholder-val="{{ true }}">
    <div id="used-notice" data-leaf="state">This link has already been used.</div>
  </sc-if>
  <a href="#" id="help-link">What does this do?</a>
</div>
</x-dc>
<script data-dc-script data-props='{"used":{"editor":"boolean","default":false}}'>
class Component extends DCLogic { renderVals() { return { used: this.props.used }; } }
</script>
</body></html>
"""


def run(args):
    return subprocess.run([sys.executable, str(SCRIPT)] + args, capture_output=True, text=True)


def design_dir(commit=True):
    root = pathlib.Path(tempfile.mkdtemp())
    d = root / "design"
    d.mkdir()
    (d / "Main.dc.html").write_text(ARTBOARD)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "."], cwd=root, check=True)
    if commit:
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "seed"],
                       cwd=root, check=True)
    return d


class DcExtractTest(unittest.TestCase):
    def test_every_interactive_leaf_is_a_row_with_the_id_as_node_id(self):
        rows = dc_extract.extract(design_dir())
        by_id = {r["id"]: r for r in rows if r["id"]}
        self.assertEqual(by_id["ack-button"]["text"], "Acknowledge")
        self.assertEqual(by_id["ack-button"]["tag"], "button")
        self.assertTrue(by_id["ack-button"]["interactive"])
        self.assertEqual(by_id["help-link"]["tag"], "a")

    def test_a_branch_is_recorded_on_leaves_inside_sc_if(self):
        rows = dc_extract.extract(design_dir())
        used = next(r for r in rows if r["id"] == "used-notice")
        self.assertIn("sc-if", used["branch"])
        self.assertTrue(used["interactive"], "data-leaf marks a non-control as a leaf")
        self.assertEqual(used["type"], "state", "the data-leaf kind is the row's type")

    def test_a_hidden_input_is_plumbing_not_a_leaf(self):
        rows = dc_extract.extract(design_dir())
        hidden = [r for r in rows if r["tag"] == "input" and r["type"] == "hidden"]
        self.assertEqual(hidden, [], "hidden inputs must not be enumerated or linted")

    def test_helmet_and_script_content_is_not_a_leaf(self):
        rows = dc_extract.extract(design_dir())
        self.assertFalse(any(r["tag"] in ("style", "script") for r in rows))
        self.assertFalse(any("DCLogic" in r["text"] for r in rows))

    def test_lint_names_the_interactive_leaf_with_no_id(self):
        r = run(["--dir", str(design_dir()), "--lint"])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("<button>", r.stdout)
        self.assertIn("Reload PHP-FPM now", r.stdout)
        # The act-form itself has an id; only its button is flagged.
        self.assertEqual(r.stdout.count("LINT "), 1)

    def test_duplicate_ids_across_artboards_are_a_lint_problem(self):
        d = design_dir()
        (d / "Email.dc.html").write_text('<x-dc><a id="help-link" href="#">x</a></x-dc>')
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "."], cwd=d.parent, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "two"],
                       cwd=d.parent, check=True)
        r = run(["--dir", str(d), "--lint"])
        self.assertIn("duplicate id 'help-link'", r.stdout)

    def test_refuses_a_dirty_design_dir_without_allow_dirty(self):
        d = design_dir()
        (d / "Main.dc.html").write_text(ARTBOARD + "\n")
        r = run(["--dir", str(d), "--json"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("REFUSED", r.stderr)
        r = run(["--dir", str(d), "--json", "--allow-dirty"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(json.loads(r.stdout)["manifest"]["sha"].endswith("-dirty"))

    def test_manifest_pins_the_commit_and_per_file_dates(self):
        d = design_dir()
        out = d / "EXTRACT.json"
        r = run(["--dir", str(d), "--out", str(out)])
        self.assertEqual(r.returncode, 0, r.stderr)
        doc = json.loads(out.read_text())
        self.assertEqual(doc["manifest"]["files"], ["Main.dc.html"])
        self.assertRegex(doc["manifest"]["sha"], r"^[0-9a-f]{7,}$")
        self.assertRegex(doc["manifest"]["file_committed"]["Main.dc.html"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(len(doc["lint"]), 1)


if __name__ == "__main__":
    unittest.main()
