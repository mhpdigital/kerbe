#!/usr/bin/env python3
"""Build the JSON bundle the local rwalk review screen renders.

Reads the current quality review (QR) from REVIEW.md and, per row, the slice of
git diff around the cited lines. Stdlib only; git is always called with an argv
list, never through a shell.

    bundle.py --review REVIEW.md --repo REPO --base REF --slice NAME --out bundle.json
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qr as qr_mod  # noqa: E402

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
MARGIN = 5


def _git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.returncode, r.stdout


def _hunks(diff_text):
    """[(new_start, new_len, [line dicts])] with the hunk header as the first line."""
    out = []
    for raw in diff_text.splitlines():
        m = HUNK_RE.match(raw)
        if m:
            old = int(m.group(1))
            new = int(m.group(3))
            out.append([new, int(m.group(4)) if m.group(4) is not None else 1,
                        [{"t": "h", "text": raw}], old, new])
            continue
        if not out or raw.startswith("\\"):
            continue
        h = out[-1]
        body, tag = raw[1:], raw[:1]
        if tag == "+":
            h[2].append({"t": "a", "old": None, "new": h[4], "text": body})
            h[4] += 1
        elif tag == "-":
            h[2].append({"t": "d", "old": h[3], "new": None, "text": body, "_pos": h[4]})
            h[3] += 1
        else:
            h[2].append({"t": "c", "old": h[3], "new": h[4], "text": raw[1:]})
            h[3] += 1
            h[4] += 1
    return [(h[0], h[1], h[2]) for h in out]


def _row_diff(repo, base, ref, row):
    if not row.file:
        return []
    if _git(repo, "cat-file", "-e", "%s:%s" % (ref, row.file))[0] != 0:
        return [{"t": "h", "text": "file not present at %s" % ref}]
    start = row.start
    end = row.end if row.end is not None else start
    if start is None:
        lo, hi = -10 ** 9, 10 ** 9
    else:
        lo, hi = start - MARGIN, end + MARGIN
    _, diff = _git(repo, "diff", "-U3", "%s...%s" % (base, ref), "--", row.file)
    lines = []
    for ns, nl, body in _hunks(diff):
        if ns <= hi and ns + max(nl, 1) - 1 >= lo:
            lines.extend(body)
    if lines:
        for l in lines:
            if l["t"] == "h":
                continue
            pos = l["new"] if l["new"] is not None else l.pop("_pos")
            l["in"] = start is not None and start <= pos <= end
        return lines
    if start is None:
        return []
    code, src = _git(repo, "show", "%s:%s" % (ref, row.file))
    if code != 0:
        return [{"t": "h", "text": "file not present at %s" % ref}]
    src_lines = src.splitlines()
    return [{"t": "c", "old": n, "new": n, "text": src_lines[n - 1], "in": True}
            for n in range(max(start, 1), min(end, len(src_lines)) + 1)]


def build(review_path, repo, base, slice_name):
    qrs = qr_mod.parse(Path(review_path).read_text(encoding="utf-8"))
    q = qr_mod.current_qr(qrs)
    if q is None:
        raise SystemExit("no open quality review in %s" % review_path)
    ref = q.reviewed_at or "HEAD"
    rows = []
    for r in q.rows:
        rows.append({"id": r.id, "tier": r.tier, "title": r.title, "file": r.file,
                     "start": r.start, "end": r.end, "why": r.why, "status": r.status,
                     "diff": _row_diff(repo, base, ref, r)})
    return {"slice": slice_name, "qr": q.id, "reviewed_at": q.reviewed_at,
            "tier3": {"status": q.tier3_status, "files": q.tier3_files}, "rows": rows}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--review", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--slice", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    bundle = build(Path(a.review), Path(a.repo), a.base, a.slice)
    Path(a.out).write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
