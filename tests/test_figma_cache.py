import importlib.util
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "coverage" / "scripts" / "figma_cache.py"

spec = importlib.util.spec_from_file_location("figma_cache", SCRIPT)
figma_cache = importlib.util.module_from_spec(spec)
spec.loader.exec_module(figma_cache)


def run(args, env_extra=None):
    env = {k: v for k, v in os.environ.items() if k != "FIGMA_API_TOKEN"}
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(SCRIPT)] + args,
                          capture_output=True, text=True, env=env)


class FigmaCacheTest(unittest.TestCase):
    def test_refuses_overwrite_without_refetch(self):
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "file.json").write_text("{}")
        r = run(["--file", "x", "--out", str(d)], {"FIGMA_API_TOKEN": "t"})
        self.assertEqual(r.returncode, 2)
        self.assertIn("REFUSED", r.stderr)

    def test_missing_token_errors_clearly(self):
        d = pathlib.Path(tempfile.mkdtemp())
        r = run(["--file", "x", "--out", str(d)])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("token", r.stderr)

    def test_compact_drops_exactly_the_dropped_keys(self):
        node = {"id": "1", "fillGeometry": [1], "strokeGeometry": [2],
                "absoluteRenderBounds": {}, "exportSettings": [], "effects": [{"type": "SHADOW"}],
                "children": [{"id": "2", "fillGeometry": [3]}]}
        out = figma_cache.compact(node)
        self.assertEqual(set(out), {"id", "effects", "children"})
        self.assertEqual(set(out["children"][0]), {"id"})

    def test_count_nodes(self):
        tree = {"id": "1", "children": [{"id": "2"}, {"id": "3", "children": []}]}
        self.assertEqual(figma_cache.count_nodes(tree), 3)


if __name__ == "__main__":
    unittest.main()
