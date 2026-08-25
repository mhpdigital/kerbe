#!/usr/bin/env python3
"""Extract leaves from a directory of Claude Design artboards (*.dc.html).

The claude-design adapter's snapshot step. Reads committed artboards, never a live
Artifact, and writes EXTRACT.json: every leaf with its node id (the element's `id`
attribute), plus a manifest pinning the git commit the files were read at.

Usage:
  dc_extract.py --dir <design dir> [--out <path>] [--lint] [--allow-dirty] [--json]

  --lint          exit 1 listing interactive leaves with no id, and duplicate ids
  --allow-dirty   extract even when the design dir has uncommitted changes (pin = sha-dirty)
  --json          print the extraction to stdout instead of writing --out
"""
import argparse
import datetime
import json
import pathlib
import subprocess
import sys
from html.parser import HTMLParser

INTERACTIVE_TAGS = {"button", "a", "input", "select", "textarea", "form", "label",
                    "details", "summary"}
# Elements the extractor never descends into for leaves.
SKIP_TAGS = {"helmet", "script", "style", "head"}
VOID_TAGS = {"input", "img", "br", "hr", "meta", "link"}
BRANCH_TAGS = {"sc-if", "sc-for"}


class _Leaf:
    __slots__ = ("file", "tag", "attrs", "text", "branch", "line")

    def __init__(self, file, tag, attrs, branch, line):
        self.file, self.tag, self.attrs, self.branch, self.line = file, tag, attrs, branch, line
        self.text = []

    def as_row(self):
        text = " ".join(" ".join(self.text).split())
        return {
            "file": self.file,
            "id": self.attrs.get("id"),
            "tag": self.tag,
            "type": self.attrs.get("type") or self.attrs.get("role") or self.tag,
            "text": text[:120],
            "branch": self.branch,
            "style": self.attrs.get("style", ""),
            "line": self.line,
            "interactive": is_interactive(self.tag, self.attrs),
        }


def is_interactive(tag, attrs):
    if tag in INTERACTIVE_TAGS:
        return True
    if "role" in attrs or "data-leaf" in attrs:
        return True
    return any(k.lower().startswith("on") for k in attrs)


class _Parser(HTMLParser):
    def __init__(self, file):
        super().__init__(convert_charrefs=True)
        self.file = file
        self.leaves = []
        self.stack = []          # (tag, leaf-or-None)
        self.branch = []         # open sc-if / sc-for descriptions
        # Open tags inside a skipped subtree. A stack, not a counter: void tags
        # (<meta>, <link>) never close, so a counter would never return to zero
        # and the whole body after <head> would be swallowed.
        self.skip_stack = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.skip_stack or tag in SKIP_TAGS:
            if tag not in VOID_TAGS:
                self.skip_stack.append(tag)
            return
        if tag in BRANCH_TAGS:
            self.branch.append("%s(%s)" % (tag, attrs.get("value") or attrs.get("list") or ""))
        leaf = None
        if is_interactive(tag, attrs) or "id" in attrs:
            leaf = _Leaf(self.file, tag, attrs, " > ".join(self.branch), self.getpos()[0])
            self.leaves.append(leaf)
        if tag not in VOID_TAGS:
            self.stack.append((tag, leaf))

    def handle_endtag(self, tag):
        if self.skip_stack:
            for i in range(len(self.skip_stack) - 1, -1, -1):
                if self.skip_stack[i] == tag:
                    del self.skip_stack[i:]
                    break
            return
        if tag in BRANCH_TAGS and self.branch:
            self.branch.pop()
        # Pop to the matching open tag; tolerate stray closers.
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.skip_stack or not data.strip():
            return
        # Text belongs to the innermost open LEAF, so a button's label lands on the button.
        for tag, leaf in reversed(self.stack):
            if leaf is not None:
                leaf.text.append(data.strip())
                break


def git(args, cwd):
    r = subprocess.run(["git"] + args, cwd=str(cwd), capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def manifest(design_dir, allow_dirty):
    sha = git(["log", "-1", "--format=%h", "--", "."], design_dir)
    committed = git(["log", "-1", "--format=%cs", "--", "."], design_dir)
    dirty = bool(git(["status", "--porcelain", "--", "."], design_dir))
    if dirty and not allow_dirty:
        raise SystemExit("REFUSED: %s has uncommitted changes — commit or discard them, "
                         "or pass --allow-dirty (the pin becomes <sha>-dirty)" % design_dir)
    files = sorted(p.name for p in design_dir.glob("*.dc.html"))
    per_file = {f: git(["log", "-1", "--format=%cs", "--", f], design_dir) for f in files}
    return {
        "design_dir": str(design_dir),
        "sha": (sha or "uncommitted") + ("-dirty" if dirty else ""),
        "committed": committed or None,
        "files": files,
        "file_committed": per_file,
        "extracted_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def extract(design_dir):
    rows = []
    for path in sorted(design_dir.glob("*.dc.html")):
        p = _Parser(path.name)
        p.feed(path.read_text(encoding="utf-8"))
        rows.extend(leaf.as_row() for leaf in p.leaves)
    return rows


def lint(rows):
    problems = []
    seen = {}
    for r in rows:
        if r["interactive"] and not r["id"]:
            problems.append("%s:%d <%s> %r has no id" % (r["file"], r["line"], r["tag"], r["text"][:40]))
        if r["id"]:
            if r["id"] in seen:
                problems.append("duplicate id %r in %s:%d and %s" % (r["id"], r["file"], r["line"], seen[r["id"]]))
            else:
                seen[r["id"]] = "%s:%d" % (r["file"], r["line"])
    return problems


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--lint", action="store_true")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    design_dir = pathlib.Path(args.dir)
    if not design_dir.is_dir():
        raise SystemExit("no such design dir: %s" % design_dir)
    if not list(design_dir.glob("*.dc.html")):
        raise SystemExit("no *.dc.html in %s" % design_dir)

    rows = extract(design_dir)
    problems = lint(rows)

    if args.lint:
        for p in problems:
            print("LINT " + p)
        print("%d leaves, %d interactive, %d problems"
              % (len(rows), sum(r["interactive"] for r in rows), len(problems)))
        return 1 if problems else 0

    doc = {"manifest": manifest(design_dir, args.allow_dirty), "leaves": rows,
           "lint": problems}
    text = json.dumps(doc, indent=2) + "\n"
    if args.json or not args.out:
        sys.stdout.write(text)
    else:
        pathlib.Path(args.out).write_text(text)
        print("wrote %s: %d leaves from %d files, pin design@%s%s"
              % (args.out, len(rows), len(doc["manifest"]["files"]), doc["manifest"]["sha"],
                 ", %d lint problems" % len(problems) if problems else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
