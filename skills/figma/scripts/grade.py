#!/usr/bin/env python3
"""Grade a Figma file against the design handoff gates.

--page <name> selects a page by name; default is the first page.
"""

import json
import re
import sys
import urllib.request
from datetime import datetime

from figma_token import get_api_token, parse_file_key


def pick_page(data, page_name):
    pages = data["document"]["children"]
    if page_name:
        for p in pages:
            if p.get("name") == page_name:
                return p
        print("Error: no page named %r (pages: %s)"
              % (page_name, ", ".join(p.get("name", "?") for p in pages)), file=sys.stderr)
        sys.exit(1)
    return pages[0]


def grade_file(api_token, file_key, page_name=None):
    url = f"https://api.figma.com/v1/files/{file_key}"
    req = urllib.request.Request(url, headers={"X-Figma-Token": api_token})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    print(f"File: {data.get('name')}")
    print(f"Last modified: {data.get('lastModified')}")
    print(f"Graded: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()

    page = pick_page(data, page_name)

    stats = {
        "frame_count": 0,
        "group_count": 0,
        "frame_n_names": [],
        "generic_names": [],
        "no_layout_frames": [],
        "has_layout_frames": [],
        "component_properties": [],
        "groups_as_containers": [],
    }

    def walk(node, depth=0):
        t = node.get("type", "?")
        name = node.get("name", "?")
        mode = node.get("layoutMode", "NONE")
        children = node.get("children", [])

        if t == "FRAME":
            stats["frame_count"] += 1
            if mode == "NONE" and children:
                stats["no_layout_frames"].append((name, depth))
            else:
                stats["has_layout_frames"].append((name, depth))
        if t == "GROUP":
            stats["group_count"] += 1
            if children:
                stats["groups_as_containers"].append((name, depth))
        if re.match(r"^Frame \d+$", name) or name == "Frame":
            stats["frame_n_names"].append((name, depth, t))
        if re.match(r"^(Ellipse|Rectangle|Vector|Group|Line) \d*$", name):
            stats["generic_names"].append((name, depth, t))
        if t == "COMPONENT" and "=" in name:
            prop_name = name.split("=")[0]
            if re.match(r"^Property \d+$", prop_name):
                stats["component_properties"].append(name)
        for child in children:
            walk(child, depth + 1)

    for child in page.get("children", []):
        walk(child)

    print("=" * 60)
    print("GATE 1: MUST PASS")
    print("=" * 60)

    content_frames_with_layout = [f for f in stats["has_layout_frames"] if f[1] >= 1]
    no_layout_content = [f for f in stats["no_layout_frames"] if f[1] >= 1]

    if no_layout_content:
        print("  [1] Auto-layout on page sections: FAIL")
        print("      Frames without layout (depth >= 1):")
        for name, depth in no_layout_content:
            print(f'        - "{name}" (depth {depth})')
    else:
        print("  [1] Auto-layout on page sections: PASS")
        print(f"      {len(content_frames_with_layout)} content frames all have auto-layout")

    print("  [2] Colours use variables: UNVERIFIABLE (API limitation)")

    top2_generic = [(n, d, t) for n, d, t in stats["frame_n_names"] if d <= 1]
    deep_generic = [(n, d, t) for n, d, t in stats["frame_n_names"] if d > 1]

    if top2_generic:
        print("  [3] Semantic frame names (top 2 levels): FAIL")
        for name, depth, ntype in top2_generic:
            print(f'        - "{name}" ({ntype}, depth {depth})')
    else:
        print("  [3] Semantic frame names (top 2 levels): PASS")
    if deep_generic:
        print(f"      Note: {len(deep_generic)} generic name(s) at deeper levels:")
        for name, depth, ntype in deep_generic:
            print(f'        - "{name}" ({ntype}, depth {depth})')

    print()
    print("=" * 60)
    print("GATE 2: SHOULD PASS")
    print("=" * 60)
    print("  [4] Spacing uses variables: UNVERIFIABLE (API limitation)")

    if stats["component_properties"]:
        print("  [5] Component variant naming: FAIL")
        for prop in stats["component_properties"]:
            print(f'        - "{prop}"')
    else:
        print("  [5] Component variant naming: PASS")

    if stats["groups_as_containers"]:
        print(f"  [6] No GROUPs as containers: FAIL ({len(stats['groups_as_containers'])} found)")
        for name, depth in stats["groups_as_containers"]:
            print(f'        - "{name}" (depth {depth})')
    else:
        print("  [6] No GROUPs as containers: PASS")

    print("  [7] Text styles shared/named: UNVERIFIABLE (designer certification)")

    print()
    print("=" * 60)
    print("GATE 3: NICE TO HAVE")
    print("=" * 60)
    pages = data["document"].get("children", [])
    has_mobile = any("mobile" in p.get("name", "").lower() for p in pages)
    print(f"  [8] Mobile variant exists: {'PASS' if has_mobile else 'NOT PRESENT'}")
    print("  [9] Interaction state annotations: NOT CHECKED (manual)")
    print("  [10] Code Connect: N/A (requires Enterprise)")

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Frames: {stats['frame_count']}")
    print(f"  Groups: {stats['group_count']}")
    print(f"  Generic 'Frame N' names: {len(stats['frame_n_names'])}")
    print(f"  Non-semantic property names: {len(stats['component_properties'])}")
    print(f"  Groups used as containers: {len(stats['groups_as_containers'])}")


if __name__ == "__main__":
    args = sys.argv[1:]
    page_name = None
    if "--page" in args:
        i = args.index("--page")
        page_name = args[i + 1]
        del args[i:i + 2]
    file_key, _ = parse_file_key(args)
    api_token = get_api_token()
    grade_file(api_token, file_key, page_name)
