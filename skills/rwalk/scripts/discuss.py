#!/usr/bin/env python3
"""Discussion bridge for the rwalk review screen. Stdlib only.

Builds a prompt about one review row, runs the configured agent command with the
prompt on stdin, parses trailing `O<n>:` options out of the answer, and logs each
exchange to REVIEW-discussion.md, one `## QR-n/ROW — title` section per row.
"""
import re
import shlex
import subprocess
from pathlib import Path

OPTION_RE = re.compile(r"^(O\d+):[ \t]*(.*?)[ \t]*$")

RULES = ("You may read files in the working directory to answer, but never edit, "
         "create, or delete any file.")
PREREAD_RULE = ("Explain the mechanism of the code under review in at most two sentences, "
                "and state any uncertainty plainly.")
ASK_RULE = ("Answer the reviewer's question. When there is more than one reasonable choice, "
            "end your answer with one line per choice, formatted `O0: ...`, `O1: ...`, "
            "each on its own line with nothing after the last one.")


def _loc(row):
    f = row.get("file")
    if not f:
        return "(no file reference)"
    s, e = row.get("start"), row.get("end")
    if s is None:
        return f
    return "%s:%s–%s" % (f, s, e) if e not in (None, s) else "%s:%s" % (f, s)


def build_prompt(row, history, question, kind):
    parts = [RULES, ""]
    parts.append("Review row %s: %s" % (row.get("id", ""), row.get("title", "")))
    parts.append("Location: " + _loc(row))
    if row.get("why"):
        parts.append("Why it matters: " + row["why"])
    changed = [d.get("text", "") for d in row.get("diff", []) if d.get("in")]
    if changed:
        parts += ["", "Code under review:"] + changed
    parts.append("")
    parts.append(PREREAD_RULE if kind == "preread" else ASK_RULE)
    if history:
        parts += ["", "Conversation so far:"]
        for q, a in history:
            parts += ["You: " + q, "Agent: " + a]
    if kind != "preread":
        parts += ["", "You: " + question]
    return "\n".join(parts) + "\n"


def run(cmd, prompt, cwd, timeout=300):
    try:
        argv = shlex.split(cmd)
    except ValueError as e:
        return False, "invalid command: %s" % e
    if not argv:
        return False, "empty command"
    try:
        p = subprocess.run(argv, input=prompt.encode("utf-8"), capture_output=True,
                           cwd=str(cwd), timeout=timeout, shell=False)
    except subprocess.TimeoutExpired:
        return False, "timed out after %ss" % timeout
    except FileNotFoundError:
        return False, "command not found: %s" % argv[0]
    except OSError as e:
        return False, "cannot run %s: %s" % (argv[0], e)
    out = p.stdout.decode("utf-8", errors="replace")
    err = p.stderr.decode("utf-8", errors="replace")
    if p.returncode != 0:
        return False, err.strip() or "exit %d" % p.returncode
    return True, out


def parse_options(text):
    lines = text.splitlines()
    end = len(lines)
    while end and not lines[end - 1].strip():
        end -= 1
    start = end
    while start and OPTION_RE.match(lines[start - 1]):
        start -= 1
    if start == end:
        return text, []
    opts = [OPTION_RE.match(l).groups() for l in lines[start:end]]
    return "\n".join(lines[:start]), [(k, v) for k, v in opts]


def _one_line(s):
    return re.sub(r"\s*[\r\n]+\s*", " ", s).strip()


def append_discussion(path, qr_id, row, question, answer, when):
    path = Path(path)
    text = path.read_text(encoding="utf-8", newline="") if path.exists() else ""
    lines = text.splitlines(keepends=True)
    first = next((l for l in lines if l.endswith("\n")), "")
    eol = "\r\n" if first.endswith("\r\n") else "\n"
    prefix = "## %s/%s — " % (qr_id, row["id"])
    ans = []
    for l in answer.splitlines() or [""]:
        ans.append("\\" + l if l.startswith("## ") else l)
    block = ["**You (%s):** %s" % (when, _one_line(question)), ""]
    block += ["**Agent:** " + ans[0]] + ans[1:]
    block = [l + eol for l in block]
    head = next((i for i, l in enumerate(lines) if l.startswith(prefix)), None)
    if head is None:
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += eol
        if lines and lines[-1].strip():
            lines.append(eol)
        lines += [prefix + _one_line(row.get("title", "")) + eol, eol] + block
    else:
        nxt = next((i for i in range(head + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
        k = nxt
        while k > head + 1 and not lines[k - 1].strip():
            k -= 1
        if k > 0 and not lines[k - 1].endswith("\n"):
            lines[k - 1] += eol
        new = [eol] + block
        if k == nxt and nxt < len(lines):
            new.append(eol)
        lines[k:k] = new
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("".join(lines))
