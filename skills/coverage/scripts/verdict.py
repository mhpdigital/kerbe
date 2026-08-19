#!/usr/bin/env python3
"""Compute the kerbe:coverage verdict from a promise ledger.

The verdict is COUNTED from ledger rows, never asserted by an agent.
Spec: docs/specs/2026-08-20-coverage-skill.md. Exit: 0 finished, 1 not, 2 malformed.
"""
import pathlib
import re
import sys

ID_RE = re.compile(r"^P-\d{3,}$")
SPEC_RE = re.compile(r"^(\?|req:\S.*|doc:\S.*|origin|GAP|n/a)$")
PLAN_RE = re.compile(r"^(\?|task:\S.*|origin|GAP|none-yet)$")
CODE_VOCAB = ("present", "partial", "absent", "to-build", "?")
HEADER_FIELDS = ("LEDGER_VERSION", "MODE", "STATUS")
MODES = ("audit", "pre-impl")


class Malformed(Exception):
    pass


def parse(path):
    text = pathlib.Path(path).read_text()
    header = {}
    for field in HEADER_FIELDS:
        m = re.search(r"^" + field + r":\s*(\S+)", text, re.M)
        if not m:
            raise Malformed("missing header field " + field)
        header[field] = m.group(1)
    if header["MODE"] not in MODES:
        raise Malformed("MODE must be one of " + ", ".join(MODES))
    rows, seen = [], set()
    for lineno, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        first = cells[0] if cells else ""
        if first == "id" or not first or set(first) <= set("-: "):
            continue  # column header / separator row
        if not ID_RE.match(first):
            raise Malformed("line %d: row id %r is not P-NNN" % (lineno, first))
        if len(cells) != 7:
            raise Malformed("line %d: %s has %d columns, expected 7 (no | in cells)"
                            % (lineno, first, len(cells)))
        pid, promise, promised_by, spec, plan, code, evidence = cells
        if pid in seen:
            raise Malformed("line %d: duplicate id %s" % (lineno, pid))
        seen.add(pid)
        if not promise or not promised_by:
            raise Malformed(pid + ": promise and promised-by must be non-empty")
        if not SPEC_RE.match(spec):
            raise Malformed(pid + ": bad spec value %r" % spec)
        if not PLAN_RE.match(plan):
            raise Malformed(pid + ": bad plan value %r" % plan)
        if code not in CODE_VOCAB:
            raise Malformed(pid + ": bad code value %r" % code)
        rows.append({"id": pid, "promise": promise, "promised_by": promised_by,
                     "spec": spec, "plan": plan, "code": code, "evidence": evidence})
    if not rows:
        raise Malformed("no promise rows found")
    return header, rows


def _is_open(row, mode):
    if row["spec"] in ("GAP", "?") or row["plan"] in ("GAP", "?"):
        return True
    if mode == "audit":
        return row["code"] in ("absent", "partial", "to-build", "?")
    return False  # pre-impl: code column is the to-build inventory, informational


def verdict(header, rows):
    mode = header["MODE"]
    spec_gaps = sum(1 for r in rows if r["spec"] == "GAP")
    plan_gaps = sum(1 for r in rows if r["plan"] == "GAP")
    code_counts = {v: sum(1 for r in rows if r["code"] == v) for v in CODE_VOCAB}
    open_rows = [r["id"] for r in rows if _is_open(r, mode)]
    lines = [
        "kerbe:coverage verdict (mode: %s)" % mode,
        "promises: %d" % len(rows),
        "hop design->spec : %d GAP" % spec_gaps,
        "hop spec->plan   : %d GAP" % plan_gaps,
        "hop plan->code   : %d present · %d partial · %d absent · %d to-build · %d unverified"
        % (code_counts["present"], code_counts["partial"], code_counts["absent"],
           code_counts["to-build"], code_counts["?"]),
    ]
    if open_rows:
        lines.append("FINISHED: NO — %d open rows: %s" % (len(open_rows), " ".join(open_rows)))
        return "\n".join(lines), 1
    lines.append("FINISHED: YES")
    return "\n".join(lines), 0


def main(argv):
    if len(argv) != 2:
        print("usage: verdict.py PROMISES.md", file=sys.stderr)
        return 2
    try:
        header, rows = parse(argv[1])
    except (Malformed, OSError) as e:
        print("MALFORMED LEDGER: " + str(e), file=sys.stderr)
        return 2
    text, code = verdict(header, rows)
    print(text)
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
