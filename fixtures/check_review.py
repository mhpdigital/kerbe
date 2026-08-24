#!/usr/bin/env python3
"""Deterministic structural checks for a kerbe REVIEW.md quality review.

usage: check_review.py <review-path> [changed-files]

Optional second arg: comma-separated repo-relative paths the diff changed; every
one must appear in some tier table (coverage — nothing silently dropped).
Structure only, never judgment. Prints PASS/FAIL per check; exit 0 = all pass,
2 = usage/unreadable.
"""
import pathlib
import re
import sys

QR_RE = re.compile(r"^## (QR-\d+) — Code Review: \S+", re.M)
SECTION_ORDER = ("### Summary", "### Business-logic", "### Glue",
                 "### Boilerplate", "### Flags")


def main(argv):
    if len(argv) not in (2, 3):
        print("usage: check_review.py <review-path> [changed-files]", file=sys.stderr)
        return 2
    path = pathlib.Path(argv[1])
    if not path.is_file():
        print("FAIL review file exists — " + str(path))
        return 2
    text = path.read_text()
    changed = [f for f in (argv[2].split(",") if len(argv) == 3 else []) if f]
    failures = 0

    def check(name, ok, detail=""):
        nonlocal failures
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else " — " + detail))
        failures += 0 if ok else 1

    qrs = QR_RE.findall(text)
    check("at least one QR recorded", bool(qrs))
    check("QR ids sequential from QR-1",
          qrs == ["QR-%d" % i for i in range(1, len(qrs) + 1)], str(qrs))

    bodies = re.split(QR_RE, text)[1:]  # [id, body, id, body, ...]
    for qid, body in zip(bodies[0::2], bodies[1::2]):
        pos = [body.find(s) for s in SECTION_ORDER]
        check(qid + " has all five sections", all(p >= 0 for p in pos),
              str([s for s, p in zip(SECTION_ORDER, pos) if p < 0]))
        if all(p >= 0 for p in pos):
            check(qid + " sections in order, Flags last",
                  pos == sorted(pos) and
                  not re.search(r"^### ", body[pos[-1] + 1:], re.M),
                  "order broken or a section follows Flags")
        for field in ("Branch", "Date", "Diff"):
            check(qid + " metadata carries " + field,
                  bool(re.search(r"\*\*" + field + r":\*\*\s*\S", body)))
        biz = body[body.find("### Business-logic"):body.find("### Glue")] \
            if "### Business-logic" in body and "### Glue" in body else ""
        rows = [r for r in biz.splitlines()
                if r.strip().startswith("|") and "`" in r and "---" not in r
                and not r.strip().startswith("| File")]
        for r in rows:
            check(qid + " tier-1 row has line reference: " + r.strip()[:44],
                  bool(re.search(r"L\d+|:\d+", r)), "no L<n> or :<line>")
            check(qid + " tier-1 row has an Open cell: " + r.strip()[:44],
                  len([c for c in r.strip().strip("|").split("|") if c.strip()]) >= 3,
                  "row must carry its own Open column (ATOMIC-ITEM)")

    for f in changed:
        check("changed file categorised: " + f, f in text,
              "appears in no tier table — silently dropped")

    check("no ✅ prefix (strikethrough convention)", "✅" not in text)
    check("resolutions keep struck item in place",
          not re.search(r"^#+ .*(resolved|done|fixed) items", text, re.I | re.M),
          "no 'resolved/done' section — strike in place")

    print(("ALL PASS" if failures == 0 else "%d FAILED" % failures))
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
