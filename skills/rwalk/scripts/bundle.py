#!/usr/bin/env python3
"""Build the JSON bundle the local rwalk review screen renders.

Reads the current quality review (QR) from REVIEW.md and, per row, the slice of
git diff around the cited lines. Stdlib only; git is always called with an argv
list, never through a shell. When the `pygmentize` command (Pygments) is on PATH,
diff lines also carry syntax-highlighted HTML; without it they stay plain text.

    bundle.py --review REVIEW.md --repo REPO --base REF --slice NAME --out bundle.json
"""
import argparse
import dataclasses
import json
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import qr as qr_mod  # noqa: E402

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
MARGIN = 5
# Pygments' own colour schemes; the page applies one per prefers-color-scheme.
HL_STYLES = {"light": "default", "dark": "github-dark"}
HL_PREFIX = "hl-"
HL_TIMEOUT = 20


class BundleError(Exception):
    pass


def _git(repo, *args):
    try:
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
    except FileNotFoundError as e:
        raise BundleError("git not found: %s" % e)
    return r.returncode, r.stdout, r.stderr


def _check_ref(repo, ref, what):
    if ref.startswith("-"):
        raise BundleError("%s must not start with '-': %r" % (what, ref))
    code, _, err = _git(repo, "rev-parse", "--verify", ref + "^{commit}")
    if code != 0:
        raise BundleError("%s %r is not a commit in %s: %s" % (what, ref, repo, err.strip()))


def _split(text):
    """Split on \\n only (str.splitlines also splits on \\x0c, \\x85, ...)."""
    parts = [p[:-1] if p.endswith("\r") else p for p in text.split("\n")]
    if parts and parts[-1] == "":
        parts.pop()
    return parts


def _hunks(diff_text):
    """[(new_start, new_len, [line dicts])] with the hunk header as the first line."""
    out = []
    for raw in _split(diff_text):
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
    code, diff, err = _git(repo, "diff", "-U3", "%s...%s" % (base, ref), "--", row.file)
    if code != 0:
        raise BundleError("git diff failed for %s: %s" % (row.file, err.strip()))
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
    code, src, err = _git(repo, "show", "%s:%s" % (ref, row.file))
    if code != 0:
        raise BundleError("git show failed for %s: %s" % (row.file, err.strip()))
    src_lines = _split(src)
    if start > len(src_lines):
        return [{"t": "h", "text": "line %d out of range" % start}]
    return [{"t": "c", "old": n, "new": n, "text": src_lines[n - 1], "in": True}
            for n in range(max(start, 1), min(end, len(src_lines)) + 1)]


def _pygmentize(exe, args):
    try:
        r = subprocess.run([exe, *args], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=HL_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return r.stdout if r.returncode == 0 else None


def _highlight_file(exe, repo, rev, path):
    """HTML lines of path at rev, or None. The whole file goes through Pygments in one
    pass so strings and comments that span lines colour correctly."""
    code, src, _ = _git(repo, "show", "%s:%s" % (rev, path))
    if code != 0:
        return None
    with tempfile.TemporaryDirectory() as d:
        # The file's own name picks the lexer (.php, .py, .dart, .html.twig, ...).
        f = Path(d) / Path(path).name
        f.write_text(src, encoding="utf-8", newline="")
        out = _pygmentize(exe, ["-f", "html", "-O", "nowrap=True,stripnl=False,encoding=utf-8,"
                                "classprefix=" + HL_PREFIX, str(f)])
    if out is None:
        return None
    lines = _split(out)
    return lines if len(lines) == len(_split(src)) else None


def _highlight_css(exe):
    """{scheme: CSS} scoped to .diff, keeping only the token-colour rules."""
    css = {}
    for scheme, style in HL_STYLES.items():
        out = _pygmentize(exe, ["-S", style, "-f", "html", "-a", ".diff",
                                "-O", "classprefix=" + HL_PREFIX])
        if out is None:
            return None
        css[scheme] = "\n".join(l for l in _split(out) if l.startswith(".diff ." + HL_PREFIX))
    return css


def _highlight(repo, base, ref, rows):
    """Add "html" to every code line Pygments can colour; return the CSS, or None."""
    exe = shutil.which("pygmentize")
    if not exe:
        return None
    css = _highlight_css(exe)
    if css is None:
        return None
    code, mb, _ = _git(repo, "merge-base", base, ref)
    old_rev = mb.strip() if code == 0 else None
    # Deleted lines are numbered against the merge base (git diff base...ref),
    # context and added lines against ref.
    want = set()
    for r in rows:
        for l in r["diff"]:
            if l["t"] == "d" and old_rev:
                want.add((old_rev, r["file"]))
            elif l["t"] in ("a", "c"):
                want.add((ref, r["file"]))
    with ThreadPoolExecutor(max_workers=8) as pool:
        keys = sorted(want)
        done = dict(zip(keys, pool.map(lambda k: _highlight_file(exe, repo, *k), keys)))
    for r in rows:
        for l in r["diff"]:
            if l["t"] == "h":
                continue
            old = l["t"] == "d"
            src = done.get((old_rev if old else ref, r["file"]))
            n = l["old"] if old else l["new"]
            if src and 1 <= n <= len(src):
                l["html"] = src[n - 1]
    return css


def _repo_path(repo, f):
    """Repo-relative form of a row's file. An Open-column path is absolute, and may sit in
    another checkout of the same repo, so fall back to its own git top level."""
    if not f or not Path(f).is_absolute():
        return f
    p = Path(f)
    try:
        return p.resolve().relative_to(Path(repo).resolve()).as_posix()
    except ValueError:
        pass
    if not p.parent.is_dir():
        return None
    code, top, _ = _git(p.parent, "rev-parse", "--show-toplevel")
    try:
        return p.resolve().relative_to(Path(top.strip()).resolve()).as_posix() if code == 0 else None
    except ValueError:
        return None


def _resolve_file(repo, ref, row):
    """The row's repo-relative file. A concern path is often relative to a code root
    below the repo top (`src/...` under `symfony/`), so when it is not present at ref,
    use the Open cell's absolute path if that one is."""
    f = _repo_path(repo, row.file)
    if f and _git(repo, "cat-file", "-e", "%s:%s" % (ref, f))[0] == 0:
        return f
    alt = _repo_path(repo, row.open_file)
    if alt and alt != f and _git(repo, "cat-file", "-e", "%s:%s" % (ref, alt))[0] == 0:
        return alt
    return f


def build(review_path, repo, base, slice_name):
    with open(review_path, encoding="utf-8", newline="") as f:
        qrs = qr_mod.parse(f.read())
    q = qr_mod.current_qr(qrs)
    if q is None:
        raise BundleError("no open quality review in %s" % review_path)
    ref = q.reviewed_at or "HEAD"
    _check_ref(repo, base, "base")
    _check_ref(repo, ref, "reviewed_at")
    rows = []
    for r in q.rows:
        r = dataclasses.replace(r, file=_resolve_file(repo, ref, r))
        rows.append({"id": r.id, "tier": r.tier, "title": r.title, "file": r.file,
                     "start": r.start, "end": r.end, "why": r.why, "status": r.status,
                     "diff": _row_diff(repo, base, ref, r)})
    return {"slice": slice_name, "qr": q.id, "reviewed_at": q.reviewed_at,
            "tier3": {"status": q.tier3_status, "files": q.tier3_files}, "rows": rows,
            "highlight": _highlight(repo, base, ref, rows)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--review", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--slice", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    try:
        bundle = build(Path(a.review), Path(a.repo), a.base, a.slice)
        Path(a.out).write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    except (BundleError, OSError, UnicodeDecodeError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
