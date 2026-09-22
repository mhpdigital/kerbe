import importlib.util
import pathlib
import unittest


REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "rwalk" / "scripts" / "classify_editor_open.py"
SPEC = importlib.util.spec_from_file_location("classify_editor_open", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EditorOpenClassifierTest(unittest.TestCase):
    def test_accepts_jetbrains_literal_argv(self):
        result = MODULE.classify("phpstorm --line {line} {file}", "/tmp/My File.php", 17)
        self.assertEqual(result["argv"], ["phpstorm", "--line", "17", "/tmp/My File.php"])
        self.assertEqual(result["approval_prefix"], ["phpstorm", "--line"])
        self.assertEqual(result["shell_command"], "phpstorm --line 17 '/tmp/My File.php'")

    def test_accepts_vscode_and_sublime_shapes(self):
        self.assertEqual(
            MODULE.classify("code -g {file}:{line}", "/tmp/a.py", 8)["argv"],
            ["code", "-g", "/tmp/a.py:8"],
        )
        self.assertEqual(
            MODULE.classify("subl {file}:{line}", "/tmp/a.py", 8)["argv"],
            ["subl", "/tmp/a.py:8"],
        )

    def test_refuses_shell_substitution_and_pipes(self):
        with self.assertRaisesRegex(MODULE.UnsafeEditorCommand, "shell operators"):
            MODULE.classify(
                "phpstorm --line $(grep -n x {file} | cut -d: -f1) {file}",
                "/tmp/a.php",
                4,
            )

    def test_refuses_unknown_executable_and_extra_flags(self):
        with self.assertRaisesRegex(MODULE.UnsafeEditorCommand, "allowlisted"):
            MODULE.classify("rm {file} --line {line}", "/tmp/a.php", 4)
        with self.assertRaisesRegex(MODULE.UnsafeEditorCommand, "unsupported arguments"):
            MODULE.classify("phpstorm --wait --line {line} {file}", "/tmp/a.php", 4)
        with self.assertRaisesRegex(MODULE.UnsafeEditorCommand, "not a path"):
            MODULE.classify("/tmp/phpstorm --line {line} {file}", "/tmp/a.php", 4)

    def test_refuses_relative_target_and_unknown_placeholders(self):
        with self.assertRaisesRegex(MODULE.UnsafeEditorCommand, "absolute"):
            MODULE.classify("phpstorm --line {line} {file}", "src/a.php", 4)
        with self.assertRaisesRegex(MODULE.UnsafeEditorCommand, "exactly"):
            MODULE.classify("phpstorm --line {line} {file} {other}", "/tmp/a.php", 4)


if __name__ == "__main__":
    unittest.main()
