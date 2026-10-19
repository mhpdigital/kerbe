#!/usr/bin/env python3
"""Parse a REVIEW.md quality review and write rwalk verdicts back into it.

Shared row writer: the review screen and any other front end record every verdict
through write_verdict(), so row syntax lives in exactly one place
(see skills/rwalk/references/recording.md). Stdlib only.

write_verdict() is pure: it takes the CURRENT file text and returns the new text,
changing only the one row (or paragraph, or the tier-3 status line) it was asked to.
"""
import re
import sys
from dataclasses import dataclass, field

QR_HEAD = re.compile(r"^## (QR-\d+) — Code Review:", re.M)
CLOSED = ("RESOLVED (VERIFIED)", "RESOLVED", "VERIFIED", "FIXED", "DEFERRED",
          "FALSE POSITIVE", "EXPECTED", "IMPROVED", "REMOVED")
DECIDED = ("FIX QUEUED", "BUG PENDING")
STATUS_RE = re.compile(
    r"\*\*(" + "|".join(re.escape(s) for s in CLOSED + DECIDED) + r"|BUG-[^\s*]+ RAISED)"
    r"(?=[\s*])[^*]*\*\*")
TIER3_RE = re.compile(r"\*\*(TIER 3 ACCEPTED[^*]*)\*\*")
ROW_ID_RE = re.compile(r"^[BG]\d+$")
FLAG_START = re.compile(r"^\*\*(F\d+) — ([^:*\n]+):")
LINES_RE = re.compile(r"\bL(\d+)(?:[–-](\d+))?")
SPAN_RE = re.compile(r"`([^`\n]+)`")
SUFFIX_RE = re.compile(r"^(.*?):(\d+)(?:[–-](\d+))?$")
EXT_RE = re.compile(r"\.[A-Za-z][A-Za-z0-9]{0,7}$")
RULE_RE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$")
VERIFIED_RE = re.compile(r"^\s*(\*\*)?Verified safe", re.I)
CELL_SPLIT = re.compile(r"(?<!\\)\|")
STRUCK_RE = re.compile(r"~~.*?~~", re.S)


class UnknownRow(KeyError):
    pass


class InvalidVerdict(ValueError):
    pass


@dataclass
class Row:
    qr: str
    id: str
    tier: str
    title: str
    file: "str | None"
    start: "int | None"
    end: "int | None"
    why: str
    status: "str | None"
    line_no: int


@dataclass
class QR:
    id: str
    rows: list = field(default_factory=list)
    tier3_status: "str | None" = None
    reviewed_at: "str | None" = None


@dataclass
class Verdict:
    kind: str
    mechanism: str = ""
    option: str = ""
    detail: str = ""
    proves: str = ""
    reason: str = ""


def escape_cell(s):
    """Make free text safe inside one table cell: escape pipes, newlines become <br>."""
    s = re.sub(r"(?<!\\)\|", r"\\|", s.strip())
    s = re.sub(r"[*~]{2,}", lambda m: "".join("\\" + ch for ch in m.group()), s)
    return "<br>".join(p.strip() for p in s.splitlines() if p.strip())


def is_closed(row):
    return row.status is not None and row.status not in DECIDED


def is_decided(row):
    return row.status in DECIDED


def current_qr(qrs):
    for q in reversed(qrs):
        if any(not is_closed(r) and not is_decided(r) for r in q.rows):
            return q
    return None


def _status_of(text):
    m = STATUS_RE.search(STRUCK_RE.sub("", text))
    return m.group(1) if m else None


def _unstrike(s):
    return re.sub(r"~~(.*?)~~", r"\1", s, flags=re.S).strip()


def _eol(line):
    return line[len(line.rstrip("\r\n")):]


def _ref(text):
    """(file, start, end) from the first path-like code span and its line reference."""
    for m in SPAN_RE.finditer(text):
        span = m.group(1).strip()
        sm = SUFFIX_RE.match(span)
        path = sm.group(1) if sm else span
        if (not path or re.search(r"[\s()]", path) or path.startswith(".")
                or path.startswith("slice/") or not ("/" in path or EXT_RE.search(path))):
            continue
        if sm:
            return path, int(sm.group(2)), int(sm.group(3)) if sm.group(3) else None
        lm = LINES_RE.search(text[m.end():])
        if lm:
            return path, int(lm.group(1)), int(lm.group(2)) if lm.group(2) else None
        return path, None, None
    lm = LINES_RE.search(text)
    if lm:
        return None, int(lm.group(1)), int(lm.group(2)) if lm.group(2) else None
    return None, None, None


def _split_flag(para):
    """(head, rest) of a flag paragraph; the head is the bold run opening at 0, nested bold allowed."""
    depth = 0
    for t in re.finditer(r"\*\*", para):
        sp = t.start()
        depth += 1 if (sp == 0 or para[sp - 1] in " \t([\"'") else -1
        if depth <= 0:
            return para[:t.end()], para[t.end():].strip()
    return para, ""


def _para_continues(line):
    return bool(line.strip()) and not FLAG_START.match(line) and not line.startswith("#") \
        and not RULE_RE.match(line) and not VERIFIED_RE.match(line)


def _qr_spans(lines):
    """[(qr_id, first_line_idx, end_idx_exclusive)] over the line list."""
    heads = [(i, QR_HEAD.match(l).group(1)) for i, l in enumerate(lines) if QR_HEAD.match(l)]
    spans = []
    for n, (i, qid) in enumerate(heads):
        end = len(lines)
        for j in range(i + 1, len(lines)):
            if lines[j].startswith("## "):
                end = j
                break
        spans.append((qid, i, end))
    return spans


def _sections(lines, a, b):
    """{'Business-logic': (start, end), ...} keyed by the word after '### '."""
    marks = [(i, re.match(r"### ([A-Za-z-]+)", lines[i]).group(1))
             for i in range(a, b) if re.match(r"### [A-Za-z-]+", lines[i])]
    out = {}
    for n, (i, name) in enumerate(marks):
        out[name] = (i, marks[n + 1][0] if n + 1 < len(marks) else b)
    return out


def _flag_paragraphs(lines, a, b):
    """[(first_idx, last_idx_inclusive)] of paragraphs opening with a flag id."""
    out, i = [], a
    while i < b:
        if FLAG_START.match(lines[i]):
            j = i
            while j + 1 < b and _para_continues(lines[j + 1]):
                j += 1
            out.append((i, j))
            i = j + 1
        else:
            i += 1
    return out


def _row_cells(line):
    return CELL_SPLIT.split(line.rstrip("\r\n").strip())[1:-1]


def _scan(text):
    """Yield (qr_id, kind, idx, last_idx, id, tier) for every addressable row."""
    lines = text.splitlines(keepends=True)
    res = []
    for qid, a, b in _qr_spans(lines):
        secs = _sections(lines, a, b)
        for name, tier in (("Business-logic", "B"), ("Glue", "G")):
            if name in secs:
                s, e = secs[name]
                for i in range(s, e):
                    if lines[i].lstrip().startswith("|"):
                        c = _row_cells(lines[i])
                        if c and ROW_ID_RE.match(c[0].strip().strip("~* ")) and \
                                c[0].strip().strip("~* ")[0] == tier:
                            res.append((qid, "row", i, i, c[0].strip().strip("~* "), tier))
        if "Flags" in secs:
            s, e = secs["Flags"]
            for i, j in _flag_paragraphs(lines, s, e):
                res.append((qid, "flag", i, j, FLAG_START.match(lines[i]).group(1), "F"))
    return lines, res


def parse(text):
    lines, found = _scan(text)
    qrs = []
    for qid, a, b in _qr_spans(lines):
        body = "".join(lines[a:b])
        q = QR(id=qid)
        m = re.search(r"\*\*Reviewed at:\*\*\s*`?([^`\s]+)`?", body)
        q.reviewed_at = m.group(1) if m else None
        secs = _sections(lines, a, b)
        if "Boilerplate" in secs:
            m = TIER3_RE.search("".join(lines[secs["Boilerplate"][0]:secs["Boilerplate"][1]]))
            q.tier3_status = m.group(1) if m else None
        qrs.append(q)
    by_id = {q.id: q for q in qrs}
    for qid, kind, i, j, rid, tier in found:
        if kind == "row":
            c = _row_cells(lines[i])
            concern = c[1] if len(c) > 1 else ""
            why = c[2] if len(c) > 2 else ""
            file_, start, end = _ref(concern)
            row = Row(qid, rid, tier, _unstrike(STATUS_RE.sub("", concern)),
                      file_, start, end, _unstrike(why),
                      _status_of(concern), i + 1)
        else:
            para = " ".join(l.strip() for l in lines[i:j + 1])
            head, rest = _split_flag(para)
            file_, start, end = _ref(rest)
            row = Row(qid, rid, "F", head.strip("*").strip(), file_,
                      start, end, _unstrike(rest), _status_of(rest), i + 1)
        by_id[qid].rows.append(row)
    return qrs


def _verdict_parts(v, today):
    """(status string, why-cell text) for a verdict, validated."""
    k = v.kind
    if k == "verified":
        if not v.mechanism.strip():
            raise InvalidVerdict("verified needs a mechanism")
        return "RESOLVED (VERIFIED) " + today, "Confirmed: " + escape_cell(v.mechanism)
    if k == "fix":
        ruling = "<br>".join(escape_cell(p) for p in (v.option, v.detail) if p.strip())
        if not ruling or not v.proves.strip():
            raise InvalidVerdict("fix needs a ruling (option or detail) and what proves it")
        return "FIX QUEUED " + today, "Ruled: %s · proves it: %s" % (ruling, escape_cell(v.proves))
    if k == "bug":
        t = v.detail.strip() or v.reason.strip()
        if not t:
            raise InvalidVerdict("bug needs a description")
        return "BUG PENDING " + today, "Bug: " + escape_cell(t)
    if k == "defer":
        t = v.reason.strip() or v.detail.strip()
        if not t:
            raise InvalidVerdict("defer needs a reason")
        return "DEFERRED " + today, "Deferred: " + escape_cell(t)
    raise InvalidVerdict("unknown verdict kind: %r" % k)


def _write_tier3(lines, qid, today):
    for q in _qr_spans(lines):
        if q[0] != qid:
            continue
        a, b = q[1], q[2]
        secs = _sections(lines, a, b)
        if "Boilerplate" not in secs:
            raise UnknownRow("tier3")
        s, e = secs["Boilerplate"]
        if TIER3_RE.search("".join(lines[s:e])):
            raise InvalidVerdict("tier 3 already has a status")
        n = 0
        for l in lines[s + 1:e]:
            if l.lstrip().startswith("|") and "---" not in l:
                if _row_cells(l)[0].strip() != "File":
                    n += 1
        m = re.search(r"\*\*Test evidence:\*\*[ \t]*(\S[^\n]*)", "".join(lines[a:b]))
        ev = m.group(1).strip() if m else ""
        if not ev or ev.lower().startswith("none"):
            ev = "the full suite"
        crlf = sum(1 for l in lines if l.endswith("\r\n"))
        eol = "\r\n" if crlf * 2 > sum(1 for l in lines if l.endswith("\n")) else "\n"
        para = "**TIER 3 ACCEPTED %s** — %d files, behind %s%s" % (today, n, ev, eol)
        new = [eol, para]
        if s + 1 >= len(lines) or lines[s + 1].strip():
            new.append(eol)
        lines[s + 1:s + 1] = new
        if not lines[s].endswith("\n"):
            lines[s] += eol
        return
    raise UnknownRow(qid)


def write_verdict(text, qr_id, row_id, v, today):
    lines, found = _scan(text)
    if row_id == "tier3":
        if v.kind != "tier3":
            raise InvalidVerdict("tier3 row takes a tier3 verdict")
        _write_tier3(lines, qr_id, today)
        return "".join(lines)
    if v.kind == "tier3":
        raise InvalidVerdict("tier3 verdict is only for the tier3 row")
    hit = next((f for f in found if f[0] == qr_id and f[4] == row_id), None)
    if hit is None:
        raise UnknownRow("%s/%s" % (qr_id, row_id))
    _, kind, i, j, _, _ = hit
    if kind == "flag":
        para = " ".join(l.strip() for l in lines[i:j + 1])
        head, rest = _split_flag(para)
        old = _status_of(rest)
    else:
        old = _status_of(_row_cells(lines[i])[1])
    if old:
        raise InvalidVerdict("%s is already %s" % (row_id, old))
    status, why_text = _verdict_parts(v, today)
    nl = _eol(lines[j])
    if kind == "row":
        c = _row_cells(lines[i])
        while len(c) < 4:
            c.append("")
        c = [x.strip() for x in c]
        c[1] = "%s **%s**" % (_strike(c[1]), status)
        c[2] = "%s %s" % (_strike(c[2]), why_text)
        c[3] = _strike(c[3]) if c[3] else c[3]
        lines[i] = "| " + " | ".join(c) + " |" + nl
    else:
        new = head + (" " + _strike(rest) if rest else "")
        new += " **%s** %s" % (status, why_text)
        lines[i:j + 1] = [new + nl]
    return "".join(lines)


def _strike(s):
    s = s.strip()
    if not s or (s.startswith("~~") and s.endswith("~~")):
        return s
    return "~~%s~~" % s


if __name__ == "__main__":
    for q in parse(open(sys.argv[1], encoding="utf-8", newline="").read()):
        for r in q.rows:
            print(q.id, r.id, r.status or "open", r.file, r.start, r.end)
