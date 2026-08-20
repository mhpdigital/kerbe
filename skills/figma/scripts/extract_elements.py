#!/usr/bin/env python3
"""Extract all UI elements from a Figma file with full styling details.

Source is either the live API (--file <key-or-url>) or a committed snapshot
(--from-json <path to file.json>, e.g. a slice's design-cache — no network, no
token). --page <name> selects a page by name; default is the first page.
"""

import json
import sys
import urllib.request


def rgba_to_hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))


def extract_fills(node):
    results = []
    for f in node.get("fills", []):
        if f.get("type") == "SOLID" and f.get("visible", True):
            c = f.get("color", {})
            hex_val = rgba_to_hex(c.get("r", 0), c.get("g", 0), c.get("b", 0))
            opacity = f.get("opacity", 1.0)
            results.append({"hex": hex_val, "opacity": opacity})
    return results


def extract_strokes(node):
    results = []
    for s in node.get("strokes", []):
        if s.get("type") == "SOLID" and s.get("visible", True):
            c = s.get("color", {})
            results.append(rgba_to_hex(c.get("r", 0), c.get("g", 0), c.get("b", 0)))
    weight = node.get("strokeWeight", 0)
    if results:
        return {"colour": results[0], "weight": weight}
    return None


def extract_text_style(node):
    style = node.get("style", {})
    return {
        "font": style.get("fontFamily", "?"),
        "weight": style.get("fontWeight", "?"),
        "size": style.get("fontSize", "?"),
        "lineHeight": style.get("lineHeightPx", "?"),
        "letterSpacing": style.get("letterSpacing", 0),
        "textCase": style.get("textCase", "ORIGINAL"),
    }


def extract_element(node):
    t = node.get("type", "?")
    element = {
        "type": t,
        "name": node.get("name", "?"),
        "id": node.get("id", "?"),
        "fills": extract_fills(node),
        "stroke": extract_strokes(node),
        "cornerRadius": node.get("cornerRadius", None),
        "opacity": node.get("opacity", 1.0),
    }
    bbox = node.get("absoluteBoundingBox", {})
    if bbox:
        element["width"] = bbox.get("width")
        element["height"] = bbox.get("height")
    if t in ("FRAME", "COMPONENT", "COMPONENT_SET", "INSTANCE"):
        element["layout"] = {
            "mode": node.get("layoutMode", "NONE"),
            "gap": node.get("itemSpacing"),
            "paddingTop": node.get("paddingTop"),
            "paddingRight": node.get("paddingRight"),
            "paddingBottom": node.get("paddingBottom"),
            "paddingLeft": node.get("paddingLeft"),
        }
    if t == "TEXT":
        element["textStyle"] = extract_text_style(node)
        element["characters"] = node.get("characters", "")
    return element


def walk(node, depth=0, output_lines=None):
    if output_lines is None:
        output_lines = []
    el = extract_element(node)
    prefix = "  " * depth
    parts = [f'{el["type"]} {el["id"]}: "{el["name"]}"']
    for fill in el.get("fills", []):
        opacity_str = f" opacity={fill['opacity']:.0%}" if fill["opacity"] < 1.0 else ""
        parts.append(f"fill={fill['hex']}{opacity_str}")
    stroke = el.get("stroke")
    if stroke:
        parts.append(f"stroke={stroke['colour']} {stroke['weight']}px")
    if el.get("cornerRadius"):
        parts.append(f"radius={el['cornerRadius']}")
    layout = el.get("layout", {})
    if layout.get("mode") and layout["mode"] != "NONE":
        parts.append(f"layout={layout['mode']}")
    if layout.get("gap") is not None:
        parts.append(f"gap={layout['gap']}")
    if any(layout.get(k) for k in ("paddingTop", "paddingRight", "paddingBottom", "paddingLeft")):
        parts.append(
            f"pad={layout.get('paddingTop', 0)}/{layout.get('paddingRight', 0)}"
            f"/{layout.get('paddingBottom', 0)}/{layout.get('paddingLeft', 0)}"
        )
    w, h = el.get("width"), el.get("height")
    if w and h:
        parts.append(f"size={w:.0f}x{h:.0f}")
    if el.get("opacity", 1.0) != 1.0:
        parts.append(f"opacity={el['opacity']:.0%}")
    ts = el.get("textStyle")
    if ts:
        parts.append(f"font={ts['font']} {ts['weight']} {ts['size']}px lh={ts['lineHeight']}px")
        parts.append(f'text="{el.get("characters", "")[:60]}"')
    output_lines.append(f"{prefix}{' | '.join(parts)}")
    for child in node.get("children", []):
        walk(child, depth + 1, output_lines)
    return output_lines


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


def main():
    args = sys.argv[1:]
    from_json = None
    page_name = None
    if "--from-json" in args:
        i = args.index("--from-json")
        from_json = args[i + 1]
        del args[i:i + 2]
    if "--page" in args:
        i = args.index("--page")
        page_name = args[i + 1]
        del args[i:i + 2]

    if from_json:
        with open(from_json) as f:
            data = json.load(f)
    else:
        from figma_token import get_api_token, parse_file_key
        file_key, _ = parse_file_key(args)
        api_token = get_api_token()
        url = f"https://api.figma.com/v1/files/{file_key}"
        req = urllib.request.Request(url, headers={"X-Figma-Token": api_token})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read())

    print(f"File: {data.get('name')}")
    print(f"Last modified: {data.get('lastModified', '(snapshot)')}")
    print()

    page = pick_page(data, page_name)
    lines = []
    for child in page.get("children", []):
        walk(child, 0, lines)
    print("\n".join(lines))

    print("\n=== COLOUR PALETTE ===")
    colours = {}

    def collect_colours(node):
        for f in node.get("fills", []):
            if f.get("type") == "SOLID" and f.get("visible", True):
                c = f.get("color", {})
                h = rgba_to_hex(c.get("r", 0), c.get("g", 0), c.get("b", 0))
                colours[h] = colours.get(h, 0) + 1
        for child in node.get("children", []):
            collect_colours(child)

    for child in page.get("children", []):
        collect_colours(child)
    for hex_val, count in sorted(colours.items(), key=lambda x: -x[1]):
        print(f"  {hex_val} — used {count}x")

    print("\n=== FONTS ===")
    fonts = {}

    def collect_fonts(node):
        if node.get("type") == "TEXT":
            style = node.get("style", {})
            key = f"{style.get('fontFamily', '?')} {style.get('fontWeight', '?')} {style.get('fontSize', '?')}px"
            fonts[key] = fonts.get(key, 0) + 1
        for child in node.get("children", []):
            collect_fonts(child)

    for child in page.get("children", []):
        collect_fonts(child)
    for font_key, count in sorted(fonts.items(), key=lambda x: -x[1]):
        print(f"  {font_key} — used {count}x")


if __name__ == "__main__":
    main()
