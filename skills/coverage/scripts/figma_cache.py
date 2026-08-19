#!/usr/bin/env python3
"""Snapshot a Figma file for a kerbe:coverage extraction.

Fetched ONCE per extraction, before the first extractor runs. Every extraction and
verification pass reads this snapshot instead of calling the Figma API — a live fetch is
a moving input. Re-fetching starts a NEW extraction (a new ledger with a new SOURCES pin);
the script refuses to overwrite an existing snapshot without --refetch for that reason.

Token resolution: $FIGMA_API_TOKEN, else the output of --token-cmd.

Usage:
  figma_cache.py --file <key> --out <dir> [--page <name>] [--refetch] [--token-cmd <cmd>]
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

API = "https://api.figma.com/v1"


def resolve_token(args):
    token = os.environ.get("FIGMA_API_TOKEN")
    if token:
        return token.strip()
    if args.token_cmd:
        r = subprocess.run(args.token_cmd, shell=True, capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
        raise SystemExit("token-cmd failed (exit %d): %s" % (r.returncode, r.stderr.strip()[:300]))
    raise SystemExit("no Figma API token: set FIGMA_API_TOKEN or pass --token-cmd")


def get(url, token):
    req = urllib.request.Request(url, headers={"X-Figma-Token": token})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def count_nodes(node):
    return 1 + sum(count_nodes(c) for c in node.get("children", []))


# Pure render geometry: vector path data and the effect-inclusive bbox. A coverage
# review reads names, ids, types, text, layout boxes, colours, radii, fonts and
# spacing — none of which live here — and these keys are ~2/3 of the payload.
# `effects` (shadows) and `absoluteBoundingBox` (the layout box) are KEPT: both are
# measurements the review checks. Every dropped key is listed in the manifest, so a
# pass can tell the difference between "not in the design" and "not in the cache".
DROPPED_KEYS = ("fillGeometry", "strokeGeometry", "absoluteRenderBounds", "exportSettings")


def compact(node):
    if isinstance(node, dict):
        return {k: compact(v) for k, v in node.items() if k not in DROPPED_KEYS}
    if isinstance(node, list):
        return [compact(v) for v in node]
    return node


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="Figma file key")
    ap.add_argument("--out", required=True, help="snapshot directory (in the slice planning folder)")
    ap.add_argument("--page", default=None, help="page name to record in the manifest")
    ap.add_argument("--token-cmd", default=None,
                    help="shell command printing the API token (fallback when FIGMA_API_TOKEN is unset)")
    ap.add_argument("--refetch", action="store_true",
                    help="overwrite an existing snapshot — STARTS A NEW EXTRACTION, see SKILL.md")
    args = ap.parse_args()

    out = pathlib.Path(args.out)
    payload = out / "file.json"
    if payload.exists() and not args.refetch:
        print("REFUSED: " + str(payload) + " already exists.\n"
              "A snapshot is fetched once, before the first extraction pass. Re-fetching\n"
              "changes the search space, so it starts a NEW extraction with a new ledger\n"
              "SOURCES pin. If that is what you intend, pass --refetch.", file=sys.stderr)
        return 2

    token = resolve_token(args)
    try:
        meta = get(API + "/files/" + args.file + "?depth=1", token)
        full = get(API + "/files/" + args.file, token)
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print("Figma API " + str(e.code) + ": " + body, file=sys.stderr)
        return 1

    out.mkdir(parents=True, exist_ok=True)
    full = compact(full)
    text = json.dumps(full, sort_keys=True, separators=(",", ":"))
    payload.write_text(text)
    sha = hashlib.sha256(text.encode()).hexdigest()

    pages = [{"name": p.get("name"), "id": p.get("id"),
              "nodes": count_nodes(p)} for p in full.get("document", {}).get("children", [])]

    manifest = {
        "file_key": args.file,
        "file_name": meta.get("name"),
        "page": args.page,
        "figma_version": meta.get("version"),
        "figma_last_modified": meta.get("lastModified"),
        "fetched_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "payload": "file.json",
        "payload_note": "whole file, all pages; keys dropped: " + ", ".join(DROPPED_KEYS),
        "dropped_keys": list(DROPPED_KEYS),
        "payload_sha256": sha,
        "payload_bytes": len(text),
        "pages": pages,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    lines = [
        "# Figma snapshot — extraction-scoped",
        "",
        "Fetched **once** for this extraction. Every pass reads `file.json`; no pass calls",
        "the Figma API. Re-fetching starts a new extraction (`figma_cache.py --refetch`).",
        "",
        "| Field | Value |",
        "|---|---|",
        "| File | `" + str(args.file) + "` — " + str(meta.get("name")) + " |",
        "| Page | " + (str(args.page) if args.page else "(whole file)") + " |",
        "| Figma version | `" + str(meta.get("version")) + "` |",
        "| Figma lastModified | " + str(meta.get("lastModified")) + " |",
        "| Fetched (UTC) | " + manifest["fetched_utc"] + " |",
        "| Payload | `file.json`, " + f"{len(text):,}" + " bytes (all pages) |",
        "| Keys dropped | " + ", ".join("`" + k + "`" for k in DROPPED_KEYS) + " — pure render geometry; names, ids, text, layout boxes, colours, radii, fonts, spacing and effects are all retained |",
        "| Payload sha256 | `" + sha + "` |",
        "",
        "## Pages in the snapshot",
        "",
        "| Page | Node id | Nodes |",
        "|---|---|---|",
    ]
    for p in pages:
        lines.append("| " + str(p["name"]) + " | `" + str(p["id"]) + "` | " + str(p["nodes"]) + " |")
    (out / "MANIFEST.md").write_text("\n".join(lines) + "\n")

    print(json.dumps({k: manifest[k] for k in
                      ("file_key", "file_name", "figma_version", "figma_last_modified",
                       "fetched_utc", "payload_sha256", "payload_bytes")}, indent=2))
    print("pages: " + ", ".join(f"{p['name']} ({p['nodes']} nodes)" for p in pages))
    return 0


if __name__ == "__main__":
    sys.exit(main())
