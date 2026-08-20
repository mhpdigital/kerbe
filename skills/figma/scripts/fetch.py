#!/usr/bin/env python3
"""Fetch Figma file data via REST API."""

import json
import sys
import urllib.request

from figma_token import get_api_token, parse_file_key


def fetch(api_token, file_key, node_id=None, depth=None, metadata_only=False):
    if metadata_only:
        url = f"https://api.figma.com/v1/files/{file_key}?depth=1"
    elif node_id:
        url = f"https://api.figma.com/v1/files/{file_key}/nodes?ids={node_id}"
    else:
        url = f"https://api.figma.com/v1/files/{file_key}"
        if depth:
            url += f"?depth={depth}"

    req = urllib.request.Request(url, headers={"X-Figma-Token": api_token})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())

    if metadata_only:
        print(json.dumps({
            "name": data.get("name"),
            "lastModified": data.get("lastModified"),
            "version": data.get("version"),
            "role": data.get("role"),
        }, indent=2))
    else:
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    file_key, remaining = parse_file_key(sys.argv[1:])
    api_token = get_api_token()

    node_id = None
    depth = None
    metadata_only = False

    i = 0
    while i < len(remaining):
        if remaining[i] == "--node" and i + 1 < len(remaining):
            node_id = remaining[i + 1]
            i += 2
        elif remaining[i] == "--depth" and i + 1 < len(remaining):
            depth = int(remaining[i + 1])
            i += 2
        elif remaining[i] == "--metadata":
            metadata_only = True
            i += 1
        else:
            print(f"Unknown arg: {remaining[i]}", file=sys.stderr)
            sys.exit(1)

    fetch(api_token, file_key, node_id, depth, metadata_only)
