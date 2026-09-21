#!/usr/bin/env python3
"""Render a narrowly safe editor-open command without executing it.

The caller executes the returned ``shell_command`` as a separate tool call. Keeping
classification and launch separate means a permission layer sees a literal editor argv,
not a shell substitution or a generic launcher.
"""

import argparse
import json
import pathlib
import shlex
import string
import sys


JETBRAINS = {
    "clion", "datagrip", "goland", "idea", "phpstorm", "pycharm", "rider",
    "rubymine", "webstorm",
}
VSCODE = {"code", "codium", "cursor"}
SUBLIME = {"subl"}
SHELL_META = set("|&;<>()$`\n\r")


class UnsafeEditorCommand(ValueError):
    pass


def _fields(template: str) -> set[str]:
    fields = set()
    for _, field, _, _ in string.Formatter().parse(template):
        if field is not None:
            fields.add(field)
    return fields


def classify(template: str, file_name: str, line: int) -> dict:
    path = pathlib.Path(file_name)
    if not path.is_absolute():
        raise UnsafeEditorCommand("target file must be absolute")
    if line < 1:
        raise UnsafeEditorCommand("line must be a positive integer")
    if any(char in SHELL_META for char in template):
        raise UnsafeEditorCommand("shell operators and substitutions are not allowed")
    if _fields(template) != {"file", "line"}:
        raise UnsafeEditorCommand("template must use exactly {file} and {line}")

    try:
        template_argv = shlex.split(template)
    except ValueError as exc:
        raise UnsafeEditorCommand("template is not valid shell-style argv") from exc
    argv = [
        token.replace("{file}", str(path)).replace("{line}", str(line))
        for token in template_argv
    ]
    if not argv:
        raise UnsafeEditorCommand("template has no executable")

    executable = pathlib.Path(argv[0]).name.lower()
    if executable in JETBRAINS:
        expected = [template_argv[0], "--line", "{line}", "{file}"]
    elif executable in VSCODE:
        expected = [template_argv[0], template_argv[1] if len(template_argv) > 1 else "", "{file}:{line}"]
        if len(template_argv) != 3 or template_argv[1] not in ("-g", "--goto"):
            raise UnsafeEditorCommand("VS Code-family template must be: editor -g {file}:{line}")
    elif executable in SUBLIME:
        expected = [template_argv[0], "{file}:{line}"]
    else:
        raise UnsafeEditorCommand("executable is not an allowlisted editor")

    if template_argv != expected:
        raise UnsafeEditorCommand("editor template has unsupported arguments or ordering")
    if argv.count(str(path)) + sum(token.startswith(str(path) + ":") for token in argv) != 1:
        raise UnsafeEditorCommand("rendered command must contain the target exactly once")

    return {
        "classification": "direct_editor_open",
        "argv": argv,
        "shell_command": shlex.join(argv),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True)
    parser.add_argument("--file", required=True)
    parser.add_argument("--line", required=True, type=int)
    args = parser.parse_args(argv)
    try:
        result = classify(args.template, args.file, args.line)
    except UnsafeEditorCommand as exc:
        print(json.dumps({"classification": "refused", "reason": str(exc)}))
        return 2
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
