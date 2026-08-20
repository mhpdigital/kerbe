import importlib.util
import os
import pathlib
import subprocess
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "skills" / "figma" / "scripts"
SNAPSHOT = REPO / "fixtures" / "symfony-mini" / "planning" / "slices" / "cards" / "design-cache" / "file.json"

spec = importlib.util.spec_from_file_location("figma_token", SCRIPTS / "figma_token.py")
figma_token = importlib.util.module_from_spec(spec)
spec.loader.exec_module(figma_token)


class TokenTest(unittest.TestCase):
    def test_env_token_wins(self):
        os.environ["FIGMA_API_TOKEN"] = "tok-env"
        try:
            self.assertEqual(figma_token.get_api_token(), "tok-env")
        finally:
            del os.environ["FIGMA_API_TOKEN"]

    def test_token_cmd_fallback(self):
        os.environ.pop("FIGMA_API_TOKEN", None)
        os.environ["KERBE_FIGMA_TOKEN_CMD"] = "echo tok-cmd"
        try:
            self.assertEqual(figma_token.get_api_token(), "tok-cmd")
        finally:
            del os.environ["KERBE_FIGMA_TOKEN_CMD"]

    def test_parse_url_forms(self):
        for url in ("https://www.figma.com/design/ABC123/My-File?node-id=1-2",
                    "https://www.figma.com/file/ABC123/My-File",
                    "ABC123"):
            key, rest = figma_token.parse_file_key(["--file", url, "--page", "P"])
            self.assertEqual(key, "ABC123")
            self.assertEqual(rest, ["--page", "P"])


class ExtractOfflineTest(unittest.TestCase):
    def run_extract(self, *extra):
        env = {k: v for k, v in os.environ.items()
               if k not in ("FIGMA_API_TOKEN", "KERBE_FIGMA_TOKEN_CMD")}
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "extract_elements.py"),
             "--from-json", str(SNAPSHOT), *extra],
            capture_output=True, text=True, env=env)

    def test_snapshot_extraction_lists_every_leaf(self):
        r = self.run_extract()
        self.assertEqual(r.returncode, 0, r.stderr)
        for leaf in ("Filter chips row", "Download row", "Export as PDF button",
                     "Share by email button", "Card grid"):
            self.assertIn(leaf, r.stdout)
        self.assertIn("1:4", r.stdout)  # node ids are printed
        self.assertIn("=== COLOUR PALETTE ===", r.stdout)

    def test_unknown_page_errors_with_page_list(self):
        r = self.run_extract("--page", "Nope")
        self.assertEqual(r.returncode, 1)
        self.assertIn("Cards", r.stderr)


if __name__ == "__main__":
    unittest.main()
