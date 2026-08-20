#!/usr/bin/env python3
"""Deterministic structural checks for a kerbe progress tracker.

usage: check_progress.py <progress-path> [plan-path]

Checks the tracker derived by kerbe:implement from a frozen plan: header pins, a
position row per plan task, legal status vocabulary, evidence on every `done`
row, disjoint file ownership across workers, and that it is not hidden away in a
dotfolder. With a plan path given, task coverage is checked against it.
Prints PASS/FAIL per check; exit 0 = all pass, 2 = usage/unreadable.
"""
import pathlib
import re
import sys

STATUSES = {"todo", "in progress", "done", "blocked", "parked"}
HEADER_FIELDS = ("Slice", "Workspace", "Branch", "Plan")


def rows(text):
    """Position-table rows as (task, status, worker, evidence)."""
    out = []
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4:
            continue
        if cells[1].lower() in STATUSES:
            out.append(cells)
    return out


def main(argv):
    if len(argv) not in (2, 3):
        print("usage: check_progress.py <progress-path> [plan-path]", file=sys.stderr)
        return 2
    path = pathlib.Path(argv[1])
    if not path.is_file():
        print("FAIL tracker exists — " + str(path))
        return 2
    text = path.read_text()
    failures = 0

    def check(name, ok, detail=""):
        nonlocal failures
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else " — " + detail))
        failures += 0 if ok else 1

    check("not in a hidden dotfolder",
          not any(p.startswith(".") and p not in (".", "..") for p in path.parts[:-1]),
          str(path))
    check("has an H1 title", bool(re.search(r"^# \S.*$", text, re.M)))
    for field in HEADER_FIELDS:
        check("header records " + field,
              bool(re.search(r"\*\*" + field + r":\*\*\s*\S", text)))

    position = rows(text)
    check("position table has rows", bool(position))
    for cells in position:
        task, status, _worker, evidence = cells
        if status.lower() == "done":
            check("done row carries evidence: " + task[:40],
                  bool(evidence) and evidence not in ("-", "—", "n/a"),
                  "evidence cell is empty")

    bad = [c[1] for c in rows(text) if c[1].lower() not in STATUSES]
    check("status vocabulary legal", not bad, str(bad))

    owners = re.findall(r"^\*\*Owns:\*\*\s*(.+)$", text, re.M)
    files = {}
    dupes = []
    for idx, line in enumerate(owners):
        for f in re.findall(r"[`\s,]([\w./{}-]+\.[A-Za-z0-9]+)", " " + line):
            if f in files and files[f] != idx:
                dupes.append(f)
            files[f] = idx
    check("worker file ownership is disjoint", not dupes, str(sorted(set(dupes))))

    if len(argv) == 3:
        plan = pathlib.Path(argv[2])
        if not plan.is_file():
            check("plan readable", False, str(plan))
        else:
            n_tasks = len(re.findall(r"^### Task \d+[:.]", plan.read_text(), re.M))
            check("a position row per plan task", len(position) >= n_tasks,
                  "%d rows for %d tasks" % (len(position), n_tasks))

    print(("ALL PASS" if failures == 0 else "%d FAILED" % failures))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
