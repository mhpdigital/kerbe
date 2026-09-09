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
    r"open questions?:",
    r"to be decided",
    r"decide (?:this )?later",
)
BAD_ADD = (r"git add -A\b", r"git add \.(?:\s|$)", r"git add \*")
# Expected output is a shape, not a count: an assertion tally is wrong the moment a
# worker adds an assertion the plan welcomed.
ASSERTION_COUNT = r"\(\s*\d+\s+tests?\s*,\s*\d+\s+assertions?\s*\)"
EFFORT = r"^\*\*Effort:\*\*\s*(low|standard|deep)\s*$"
# Concurrency is read off a per-task dependency graph, not a per-plan chain/group label.
DEPENDS = r"^\*\*Depends:\*\*\s*(none|\d+(?:\s*,\s*\d+)*)\s*$"
# A case's level decides what infrastructure proves it, so it is a planning decision.
LEVELS = ("unit", "kernel", "http", "browser")
STATUS_OK = 0


def case_levels(body):
    """Levels declared in the task's case tables, as (found_a_table, bad_values)."""
    found, bad, in_table = False, [], False
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            in_table = False
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if not cells:
            continue
        if cells[0].lower() == "level":
            found, in_table = True, True
            continue
        if in_table and set(cells[0]) <= set("-: "):
            continue
        if in_table and cells[0].lower() not in LEVELS:
            bad.append(cells[0])
    return found, bad


def find_cycle(deps):
    """A task number on a dependency cycle, or None. Unknown targets are ignored."""
    state = {}

    def visit(node):
        if state.get(node) == "done":
            return None
        if state.get(node) == "open":
            return node
        state[node] = "open"
        for target in deps.get(node, ()):
            if target in deps and visit(target) is not None:
                return node
        state[node] = "done"
        return None

    for node in deps:
        if visit(node) is not None:
            return node
    return None


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

    found = list(re.finditer(r"^### Task (\d+)[:.](.*?)(?=^### Task \d+[:.]|\Z)",
                             text, re.M | re.S))
    tasks = [m.group(2) for m in found]
    numbers = [int(m.group(1)) for m in found]
    check("has at least one task", len(tasks) >= 1, "no '### Task N:' heading")

    deps = {}
    for i, body in enumerate(tasks, start=1):
        tag = "task %d" % i
        check(tag + " lists Files", "**Files:**" in body)
        check(tag + " declares an Effort level",
              bool(re.search(EFFORT, body, re.M)),
              "**Effort:** low | standard | deep — it sets the code boundary")
        check(tag + " has an Interfaces block", "**Interfaces:**" in body,
              "seams only; say none rather than omitting it")
        declared = re.search(DEPENDS, body, re.M)
        check(tag + " declares Depends", bool(declared),
              "**Depends:** none | 2, 3 — the scheduler reads the graph, not a label")
        if declared:
            raw = declared.group(1).strip()
            deps[numbers[i - 1]] = ([] if raw == "none"
                                    else [int(n) for n in raw.split(",")])
        has_table, bad = case_levels(body)
        check(tag + " case table carries a Level column", has_table,
              "| Level | Precondition | Expectation | @req |")
        check(tag + " case levels are unit/kernel/http/browser", not bad,
              str(bad[:3]))
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

    unknown = sorted({t for targets in deps.values() for t in targets
                      if t not in numbers})
    check("every Depends names a task that exists", not unknown,
          "no such task: " + str(unknown))
    cycle = find_cycle(deps)
    check("dependency graph is acyclic", cycle is None,
          "task %s is on a cycle — the tasks are not independently deliverable" % cycle)

    for pat in BAD_ADD:
        check("no unscoped staging (%s)" % pat.replace("\\b", "").replace("\\", ""),
              not re.search(pat, text))

    for pat in PLACEHOLDERS:
        hits = re.findall(pat, text, re.I)
        check("no placeholder %r" % pat.replace("\\b", ""), not hits, str(hits[:3]))

    counts = re.findall(ASSERTION_COUNT, text)
    check("expected output is a shape, not an assertion count", not counts,
          "%s — state what must be observable (zero failures, the class in the run)"
          % str(counts[:3]))

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
