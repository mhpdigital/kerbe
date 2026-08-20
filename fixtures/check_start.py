#!/usr/bin/env python3
"""Deterministic acceptance checks for kerbe:start output.

usage: check_start.py <project_root> <slice-id> <true|false> [stack-docs]

Third arg is the design_required answer the run was given. Optional fourth arg
is the comma-separated stack-doc set the slice's tailoring should have produced
(default: ENTITIES.md,ROUTES.md,SECURITY.md,DONE_CRITERIA.md) — an infra slice
legitimately omits ENTITIES/ROUTES, so the gate names what it expects per run.
Docs outside the expected set must NOT exist. Prints PASS/FAIL per check;
exit 0 = all pass.
"""
import pathlib
import re
import sys

ALL_STACK_DOCS = ("ENTITIES.md", "ROUTES.md", "SECURITY.md", "DONE_CRITERIA.md")


def main(argv):
    if len(argv) not in (4, 5) or argv[3] not in ("true", "false"):
        print("usage: check_start.py <project_root> <slice-id> <true|false> [stack-docs]",
              file=sys.stderr)
        return 1
    root, slice_id, design = pathlib.Path(argv[1]), argv[2], argv[3]
    stack_docs = tuple(argv[4].split(",")) if len(argv) == 5 else ALL_STACK_DOCS
    slice_dir = root / "planning" / "slices" / slice_id
    checks, failures = [], 0

    def check(name, ok, detail=""):
        nonlocal failures
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else " — " + detail))
        failures += 0 if ok else 1

    check("slice folder exists", slice_dir.is_dir(), str(slice_dir))

    settings = slice_dir / "SETTINGS.md"
    st = settings.read_text() if settings.exists() else ""
    check("SETTINGS.md exists", settings.exists())
    check("design_required explicit and matches",
          bool(re.search(r"^design_required:\s*" + design + r"\s*$", st, re.M)),
          "settings block must carry design_required: " + design)
    notes_row = re.search(r"\|\s*`design_required`\s*\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(\S[^|]*)\|", st)
    check("SETTINGS Notes row dated with a reason", bool(notes_row))

    ui = slice_dir / "UI_ELEMENTS.md"
    if design == "true":
        check("UI_ELEMENTS.md present (design_required true)", ui.exists())
        if ui.exists():
            u = ui.read_text()
            check("UI_ELEMENTS has Design sources block", "Design sources" in u)
            check("UI_ELEMENTS is leaf-level (node id column)", "Node id" in u)
    else:
        check("UI_ELEMENTS.md omitted (design_required false)", not ui.exists())

    for doc in ("REQUIREMENTS.md", "TIMING.md") + stack_docs:
        check(doc + " exists", (slice_dir / doc).exists())
    for doc in ALL_STACK_DOCS:
        if doc not in stack_docs:
            check(doc + " omitted (tailoring)", not (slice_dir / doc).exists())

    timing = slice_dir / "TIMING.md"
    t = timing.read_text() if timing.exists() else ""
    start_row = re.search(r"1\. Start\s*\|[^|]*\|\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})", t)
    check("TIMING row '1. Start' stamped", bool(start_row))
    if design == "false":
        check("TIMING Design row says n/a", "n/a (design_required: false)" in t)

    index = root / "planning" / "slices" / "INDEX.md"
    ix = index.read_text() if index.exists() else ""
    check("INDEX.md registers the slice as planning",
          bool(re.search(re.escape(slice_id) + r".*planning", ix)))

    print("check_start: %d failed" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
