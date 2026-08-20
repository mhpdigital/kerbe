#!/usr/bin/env python3
"""Render the kerbe lifecycle poster as a hand-laid SVG (and PDF via Chrome).

Why not mermaid for the poster: neither dagre nor ELK lets you say which side an
edge takes. This layout is explicit, and it holds one rule —

    every BACKWARD (upward) edge runs in the right-hand gutter, one lane each,
    so no two ever overlap; every forward edge runs on the spine or in the
    left-hand gutter.

docs/lifecycle.md keeps the same graph in mermaid for GitHub/inline viewing.

usage: python3 docs/render-lifecycle.py [out.pdf]
"""
import pathlib
import subprocess
import sys

# ── geometry ────────────────────────────────────────────────────────────────
W = 1400
SPINE_X, SPINE_W = 455, 330
LEFT_X, LEFT_W = 70, 300
SIDE_X, SIDE_W = 860, 300
LANES = [1215, 1265, 1315, 1365]          # right-hand gutter, one per back edge
LEFT_LANES = [40, 20]                      # left-hand gutter for skip-forward edges
ROW_GAP, LINE_H, PAD = 46, 17, 13

FILL = {
    "skill":    ("#1f6feb", "#0b3a80", "#ffffff"),
    "planned":  ("#eef3fb", "#1f6feb", "#0b3a80"),
    "gate":     ("#fff4e5", "#bc4c00", "#24292f"),
    "artifact": ("#f6f8fa", "#57606a", "#24292f"),
    "seam":     ("#eef6ec", "#2da44e", "#24292f"),
    "done":     ("#2da44e", "#1a7f37", "#ffffff"),
}

# id, column, kind, row, lines
NODES = [
    ("SEAM",    "left",  "seam",     0, ["kerbe.yml + adapters/", "every path, command and dispatch", "mechanism resolves here"]),
    ("CUT",     "spine", "gate",     0, ["Cut a vertical slice — sized for efficiency,", "not minimalism: a coherent capability that", "ships and reviews on its own · in INDEX.md"]),
    ("START",   "spine", "skill",    1, ["kerbe:start", "slice folder + tailored doc set"]),
    ("DGATE",   "spine", "gate",     2, ["design_required?", "asked, never inferred"]),
    ("FIGMA",   "spine", "skill",    3, ["kerbe:figma", "leaves + node ids"]),
    ("SPECS",   "spine", "artifact", 4, ["Fill the specs", "UI_ELEMENTS · ENTITIES · ROUTES · SECURITY", "DONE_CRITERIA · REQUIREMENTS"]),
    ("PLAN",    "spine", "skill",    5, ["kerbe:plan"]),
    ("DFRESH",  "spine", "gate",     6, ["Design gate: node ids present?", "measured after the last change?"]),
    ("PLANMD",  "spine", "artifact", 7, ["PLAN.md — FROZEN", "the HOW, with code"]),
    ("COVPRE",  "spine", "skill",    8, ["kerbe:coverage — pre-impl", "is every promise tasked?"]),
    ("IMPL",    "spine", "skill",    9, ["kerbe:implement", "workspace · claude-progress.md", "one worker per task"]),
    ("TGATE",   "spine", "gate",    10, ["Per-task gate: global-effect", "artifact in the diff?"]),
    ("FULLRUN", "side",  "artifact",11, ["Full suite + schema applied", "the pasted output IS the evidence"]),
    ("MORE",    "spine", "gate",    12, ["More tasks?"]),
    ("COVAUD",  "spine", "skill",   13, ["kerbe:coverage — audit", "EXTRACT the ledger, then VERIFY every row"]),
    ("LEDGER",  "spine", "artifact",14, ["PROMISES.md — FROZEN", "one row per leaf promise · the denominator"]),
    ("VERDICT", "spine", "gate",    15, ["verdict.py", "computed, never asserted"]),
    ("REVIEW",  "spine", "planned", 16, ["kerbe:review  (planned — sdlc-code-review today)", "risk-tier the diff · tier 1 read line by line", "tier 3 trusted only behind a FULL-suite run", "adversarial pass · recorded as QR-n in REVIEW.md"]),
    ("DONE",    "spine", "done",    17, ["Slice FINISHED · merge → INDEX: done"]),
    ("REPORTED","left",  "artifact",18, ["A bug is reported,", "outside any loop"]),
    ("CLASS",   "spine", "gate",    18, ["What kind of open row?", "absent · partial · GAP"]),
    ("SPECDEC", "left",  "artifact",19, ["Spec decision FIRST — add the leaf", "to the specs, or a dated drop", "in DECISIONS.md"]),
    ("BUG",     "spine", "skill",   19, ["kerbe:bug", "impact table BEFORE the fix", "one commit per root cause"]),
    ("MANUAL",  "side",  "artifact",19, ["Verify by hand", "operational / live-service rows"]),
    ("FIXWORK", "spine", "skill",   20, ["kerbe:plan → FIX_PLAN.md citing ledger ids", "then kerbe:implement in remediation mode"]),
    ("REVERIFY","spine", "artifact",21, ["Re-verify the closed rows", "against the SAME frozen ledger"]),
]

# (from, to, label, route) — route: spine | left:<lane> | back:<lane> | side
EDGES = [
    ("CUT", "START", "", "spine"),
    ("START", "DGATE", "", "spine"),
    ("DGATE", "FIGMA", "true", "spine"),
    ("DGATE", "SPECS", "false + dated reason", "left:0"),
    ("FIGMA", "SPECS", "", "spine"),
    ("SPECS", "PLAN", "", "spine"),
    ("PLAN", "DFRESH", "", "spine"),
    ("DFRESH", "PLANMD", "fresh", "spine"),
    ("PLANMD", "COVPRE", "", "spine"),
    ("COVPRE", "IMPL", "everything tasked", "spine"),
    ("IMPL", "TGATE", "", "spine"),
    ("TGATE", "FULLRUN", "yes", "side"),
    ("TGATE", "MORE", "no — a scoped run is enough", "spine"),
    ("FULLRUN", "MORE", "", "side"),
    ("MORE", "COVAUD", "no", "spine"),
    ("COVAUD", "LEDGER", "", "spine"),
    ("LEDGER", "VERDICT", "", "spine"),
    ("VERDICT", "REVIEW", "nothing open", "spine"),
    ("REVIEW", "DONE", "clean", "spine"),
    ("VERDICT", "CLASS", "open rows remain", "left:1"),
    ("REVIEW", "BUG", "defects found", "left:0"),
    ("REPORTED", "BUG", "", "side"),
    ("CLASS", "SPECDEC", "design-only, never spec'd", "side"),
    ("CLASS", "BUG", "defect with blast radius", "spine"),
    ("CLASS", "MANUAL", "repo cannot evidence it", "side"),
    ("SPECDEC", "FIXWORK", "accepted, now it is work", "side"),
    ("BUG", "REVERIFY", "", "spine"),
    ("CLASS", "FIXWORK", "build work", "left:0"),
    ("MANUAL", "REVERIFY", "", "side"),
    ("FIXWORK", "REVERIFY", "", "spine"),
    # backward edges — right gutter, one lane each, never overlapping
    ("DFRESH", "FIGMA", "unfilled / stale", "back:0"),
    ("COVPRE", "PLAN", "a promise is untasked", "back:1"),
    ("MORE", "IMPL", "yes", "back:0"),
    ("REVERIFY", "COVAUD", "re-verify against the same ledger", "back:2"),
]

BANDS = [("Loop 1 — build the slice", "START", "MORE"),
         ("Loop 2 — remediation, repeats until the verdict clears", "CLASS", "REVERIFY")]


def layout():
    cols = {"spine": (SPINE_X, SPINE_W), "left": (LEFT_X, LEFT_W), "side": (SIDE_X, SIDE_W)}
    rows, boxes = {}, {}
    for _, _, _, row, lines in NODES:
        rows[row] = max(rows.get(row, 0), len(lines) * LINE_H + 2 * PAD)
    y, row_y = 110, {}
    for row in sorted(rows):
        row_y[row] = y
        y += rows[row] + ROW_GAP
    for nid, col, kind, row, lines in NODES:
        x, w = cols[col]
        boxes[nid] = dict(x=x, y=row_y[row], w=w, h=len(lines) * LINE_H + 2 * PAD,
                          kind=kind, lines=lines, col=col, row_i=row)
    return boxes, y


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def label(x, y, text, anchor="middle"):
    if not text:
        return ""
    w = len(text) * 6.0 + 10
    lx = x - w / 2 if anchor == "middle" else x
    return (f'<rect x="{lx:.0f}" y="{y-11:.0f}" width="{w:.0f}" height="16" rx="3" '
            f'fill="#ffffff" stroke="#d0d7de"/>'
            f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="{anchor}" class="edge">{esc(text)}</text>')


def render():
    boxes, height = layout()
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height+30}" width="{W}">',
           '<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
           'markerHeight="7" orient="auto-start-reverse">'
           '<path d="M 0 0 L 10 5 L 0 10 z" fill="#57606a"/></marker></defs>',
           '<style>text{font-family:-apple-system,"Helvetica Neue",Arial,sans-serif}'
           '.n{font-size:13px}.nb{font-size:13px;font-weight:600}'
           '.edge{font-size:11px;fill:#6639ba}.band{font-size:13px;fill:#57606a;font-weight:600}'
           '</style>', f'<rect width="{W}" height="{height+30}" fill="#ffffff"/>']

    for title, first, last in BANDS:
        t, b = boxes[first], boxes[last]
        out.append(f'<rect x="{LEFT_X-30}" y="{t["y"]-34:.0f}" width="{SIDE_X+SIDE_W-LEFT_X+70}" '
                   f'height="{b["y"]+b["h"]-t["y"]+52:.0f}" rx="14" fill="#f7f9fd" stroke="#c9d4e6"/>')
        tw = len(title) * 7.2 + 16
        out.append(f'<rect x="{LEFT_X-22}" y="{t["y"]-28:.0f}" width="{tw:.0f}" height="20" '
                   f'fill="#f7f9fd"/>')
        out.append(f'<text x="{LEFT_X-14}" y="{t["y"]-14:.0f}" class="band">{esc(title)}</text>')

    for nid, box in boxes.items():
        fill, stroke, fg = FILL[box["kind"]]
        dash = ' stroke-dasharray="6 4"' if box["kind"] == "planned" else ""
        out.append(f'<rect x="{box["x"]}" y="{box["y"]:.0f}" width="{box["w"]}" height="{box["h"]:.0f}" '
                   f'rx="7" fill="{fill}" stroke="{stroke}" stroke-width="1.5"{dash}/>')
        for i, line in enumerate(box["lines"]):
            cls = "nb" if i == 0 else "n"
            out.append(f'<text x="{box["x"]+box["w"]/2}" y="{box["y"]+PAD+13+i*LINE_H:.0f}" '
                       f'text-anchor="middle" class="{cls}" fill="{fg}">{esc(line)}</text>')

    for src, dst, text, route in EDGES:
        a, b = boxes[src], boxes[dst]
        ax, ay = a["x"] + a["w"] / 2, a["y"] + a["h"]
        bx, by = b["x"] + b["w"] / 2, b["y"]
        if route == "spine":
            pts = f"{ax},{ay} {ax},{(ay+by)/2:.0f} {bx},{(ay+by)/2:.0f} {bx},{by}"
            out.append(label((ax + bx) / 2, (ay + by) / 2 - 5, text))
        elif route == "side":
            span = b["row_i"] - a["row_i"] if "row_i" in a else 0
            if by > ay and span > 1 and a["col"] in ("side", "left"):
                # crosses a spine row — go out to a gutter rather than through it
                gut = SIDE_X + SIDE_W + 25 if a["col"] == "side" else LEFT_X - 25
                sx = a["x"] + a["w"] if a["col"] == "side" else a["x"]
                pts = (f"{sx},{a['y']+a['h']/2:.0f} {gut},{a['y']+a['h']/2:.0f} "
                       f"{gut},{by-18:.0f} {bx},{by-18:.0f} {bx},{by}")
                out.append(label(gut + 6, (a["y"] + by) / 2, text, "start"))
            elif by > ay:
                mid = (ay + by) / 2
                pts = f"{ax},{ay} {ax},{mid:.0f} {bx},{mid:.0f} {bx},{by}"
                out.append(label((ax + bx) / 2, mid - 5, text))
            else:                                   # same row — go sideways
                ay2, by2 = a["y"] + a["h"] / 2, b["y"] + b["h"] / 2
                sx = a["x"] + a["w"] if b["x"] > a["x"] else a["x"]
                ex = b["x"] if b["x"] > a["x"] else b["x"] + b["w"]
                pts = f"{sx},{ay2:.0f} {(sx+ex)/2:.0f},{ay2:.0f} {(sx+ex)/2:.0f},{by2:.0f} {ex},{by2:.0f}"
                out.append(label((sx + ex) / 2, ay2 - 6, text))
        elif route.startswith("left"):
            lane = LEFT_LANES[int(route.split(":")[1])]
            pts = (f"{a['x']},{a['y']+a['h']/2:.0f} {lane},{a['y']+a['h']/2:.0f} "
                   f"{lane},{by-16:.0f} {bx},{by-16:.0f} {bx},{by}")
            out.append(label(lane + 6, (a["y"] + b["y"]) / 2, text, "start"))
        else:                                       # back:<lane> — right gutter
            lane = LANES[int(route.split(":")[1])]
            ay2, by2 = a["y"] + a["h"] / 2, b["y"] + b["h"] / 2
            pts = (f"{a['x']+a['w']},{ay2:.0f} {lane},{ay2:.0f} {lane},{by2:.0f} "
                   f"{b['x']+b['w']},{by2:.0f}")
            out.append(label(lane + 6, (ay2 + by2) / 2, text, "start"))
        out.append(f'<polyline points="{pts}" fill="none" stroke="#57606a" stroke-width="1.6" '
                   f'marker-end="url(#a)"/>')

    for target in ("START", "COVAUD", "CLASS"):
        s, t = boxes["SEAM"], boxes[target]
        out.append(f'<polyline points="{s["x"]+s["w"]/2},{s["y"]+s["h"]} '
                   f'{s["x"]+s["w"]/2},{t["y"]+t["h"]/2:.0f} {t["x"]},{t["y"]+t["h"]/2:.0f}" '
                   f'fill="none" stroke="#2da44e" stroke-width="1.2" stroke-dasharray="4 4" '
                   f'marker-end="url(#a)" opacity="0.55"/>')
    out.append("</svg>")
    return "\n".join(out), height


def main():
    svg, height = render()
    pathlib.Path("docs/lifecycle.svg").write_text(svg)
    out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                       else pathlib.Path.home() / "Downloads" / "kerbe-lifecycle.pdf")
    page_w = 420
    page_h = round(page_w * ((height + 30) / W) + 58)
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Kerbe lifecycle</title>
<style>@page {{ size: {page_w}mm {page_h}mm; margin: 10mm; }}
html,body{{margin:0;padding:0}}
body{{font-family:-apple-system,"Helvetica Neue",Arial,sans-serif;color:#24292f}}
h1{{font-size:19pt;margin:0 0 2mm}}
p.sub{{font-size:10pt;line-height:1.45;color:#57606a;margin:0 0 5mm}}
svg{{width:100%;height:auto}}
footer{{font-size:8pt;color:#57606a;margin-top:4mm}}</style></head><body>
<h1>The kerbe lifecycle — one project, many slices, two loops</h1>
<p class="sub">A project is cut into vertical slices, sized for efficiency rather than
minimalism — a slice is whatever ships and reviews on its own. <b>Loop 1</b> builds one and
refuses to guess at three gates. The frozen promise ledger then <b>measures</b> what shipped,
<b>kerbe:review</b> risk-tiers the diff, and <b>Loop 2</b> closes whatever is still missing,
repeating until <code>verdict.py</code> reports nothing open — the denominator never moves
while it runs, which is what makes “6 of 36 closed” a measurement rather than a feeling.
Every backward arrow runs in the right-hand gutter; everything else runs on the spine or the
left.</p>
{svg}
<footer>kerbe · docs/lifecycle.md (mermaid source) · docs/render-lifecycle.py (this layout) ·
solid blue = ported skill · dashed blue = planned · orange = gate that stops rather than
guesses · grey = artifact · green = config seam</footer></body></html>"""
    tmp = pathlib.Path("/tmp/kerbe-lifecycle-poster.html")
    tmp.write_text(html)
    chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    subprocess.run([chrome, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=5000", f"--print-to-pdf={out}", f"file://{tmp}"],
                   check=True, capture_output=True)
    print(f"wrote {out}  ({page_w}mm x {page_h}mm)")


if __name__ == "__main__":
    main()
