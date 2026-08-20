#!/usr/bin/env python3
"""Deterministic acceptance checks for kerbe:start output.

usage: check_start.py <project_root> <slice-id> <true|false>

Third arg is the design_required answer the run was given. Prints PASS/FAIL per
check; exit 0 = all pass.
"""
import pathlib
import re
import sys

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def main(argv):
    if len(argv) != 4 or argv[3] not in ("true", "false"):
        print("usage: check_start.py <project_root> <slice-id> <true|false>", file=sys.stderr)
        return 1
    root, slice_id, design = pathlib.Path(argv[1]), argv[2], argv[3]
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

    for doc in ("REQUIREMENTS.md", "ENTITIES.md", "ROUTES.md", "SECURITY.md",
                "DONE_CRITERIA.md", "TIMING.md"):
        check(doc + " exists", (slice_dir / doc).exists())

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
