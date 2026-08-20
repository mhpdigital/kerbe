#!/usr/bin/env python3
"""Deterministic structural checks for a kerbe PLAN.md (or FIX_PLAN.md).

usage: check_plan.py <plan-path> [true|false]

The optional second arg is the slice's design_required value: `true` additionally
requires the header to record the design and at least one task to carry a
`node=<id> measured=<date>` origin. Structure only — never judgment. Prints
PASS/FAIL per check; exit 0 = all pass, 2 = usage/unreadable.
"""
import pathlib
import re
import sys

HEADER_FIELDS = ("Goal", "Architecture", "Stack", "Spec", "Design")
PLACEHOLDERS = (
    r"\bTBD\b",
    r"\bTODO\b",
    r"implement later",
    r"fill in details?",
    r"add (?:appropriate )?error handling",
    r"handle edge cases",
    r"similar to task \d",
    r"write tests for the above",
)
BAD_ADD = (r"git add -A\b", r"git add \.(?:\s|$)", r"git add \*")
STATUS_OK = 0


def main(argv):
    if len(argv) not in (2, 3) or (len(argv) == 3 and argv[2] not in ("true", "false")):
        print("usage: check_plan.py <plan-path> [true|false]", file=sys.stderr)
        return 2
    path = pathlib.Path(argv[1])
    if not path.is_file():
        print("FAIL plan file exists — " + str(path))
        return 2
    text = path.read_text()
    design_required = len(argv) == 3 and argv[2] == "true"
    failures = 0

    def check(name, ok, detail=""):
        nonlocal failures
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else " — " + detail))
        failures += 0 if ok else 1

    check("filename is PLAN.md or FIX_PLAN.md", path.name in ("PLAN.md", "FIX_PLAN.md"),
          path.name)
    check("not in a hidden dotfolder",
          not any(p.startswith(".") and p not in (".", "..") for p in path.parts[:-1]),
          str(path))
    check("has an H1 title", bool(re.search(r"^# \S.*$", text, re.M)))

    for field in HEADER_FIELDS:
        check("header records " + field,
              bool(re.search(r"^\*\*" + field + r":\*\*\s*\S", text, re.M)))

    gc = re.search(r"^## Global Constraints\s*$(.*?)(?=^## |\Z)", text, re.M | re.S)
    check("Global Constraints section present", bool(gc))
    check("Global Constraints non-empty", bool(gc and gc.group(1).strip()))
    check("Global Constraints name the base branch",
          bool(gc and re.search(r"branch", gc.group(1), re.I)))
    check("Global Constraints carry the full-suite trigger",
          bool(gc and re.search(r"full suite|full-suite|whole suite", gc.group(1), re.I)))

    check("file-structure map present",
          bool(re.search(r"^#{2,3} .*file[- ]structure|^#{2,3} .*files? map", text,
                         re.M | re.I)))

    tasks = re.split(r"^### Task \d+[:.]", text, flags=re.M)[1:]
    check("has at least one task", len(tasks) >= 1, "no '### Task N:' heading")

    for i, body in enumerate(tasks, start=1):
        tag = "task %d" % i
        check(tag + " lists Files", "**Files:**" in body)
        steps = re.findall(r"^- \[ \] ", body, re.M)
        check(tag + " has checkbox steps", len(steps) >= 3, "%d found" % len(steps))
        check(tag + " starts with a failing test",
              bool(re.search(r"failing test|test to verify it fails|confirm it fails",
                             body, re.I)))
        check(tag + " ends with a commit step", bool(re.search(r"git commit", body)))
        check(tag + " commit is pathspec-scoped",
              all(re.search(r"git commit[^\n]*--\s+\S", line)
                  for line in re.findall(r"^.*git commit.*$", body, re.M)),
              "every git commit must end with -- <paths>")

    for pat in BAD_ADD:
        check("no unscoped staging (%s)" % pat.replace("\\b", "").replace("\\", ""),
              not re.search(pat, text))

    for pat in PLACEHOLDERS:
        hits = re.findall(pat, text, re.I)
        check("no placeholder %r" % pat.replace("\\b", ""), not hits, str(hits[:3]))

    if design_required:
        check("header Design line records the measured design",
              bool(re.search(r"^\*\*Design:\*\*.*(?:measured|\d{4}-\d{2}-\d{2})", text,
                             re.M | re.I)))
        check("a task carries node= and measured=",
              bool(re.search(r"node=\S+", text)) and bool(re.search(r"measured=\d{4}-\d{2}-\d{2}", text)))

    print(("ALL PASS" if failures == 0 else "%d FAILED" % failures))
    return STATUS_OK if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
