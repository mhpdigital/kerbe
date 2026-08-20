#!/usr/bin/env python3
"""Shared token + file-key resolution for the kerbe figma scripts.

Token order: $FIGMA_API_TOKEN, else the shell command in $KERBE_FIGMA_TOKEN_CMD
(set it from kerbe.yml's design.token_cmd). No project-specific fallbacks live
here — secrets-manager lookups belong in the configured command.
"""
import os
import re
import subprocess
import sys


def get_api_token():
    token = os.environ.get("FIGMA_API_TOKEN")
    if token:
        return token.strip()
    cmd = os.environ.get("KERBE_FIGMA_TOKEN_CMD")
    if cmd:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
        print("token command failed (exit %d): %s" % (r.returncode, r.stderr.strip()[:300]),
              file=sys.stderr)
        sys.exit(1)
    print("Error: no Figma API token. Set FIGMA_API_TOKEN, or set KERBE_FIGMA_TOKEN_CMD "
          "to the shell command from kerbe.yml design.token_cmd.", file=sys.stderr)
    sys.exit(1)


def parse_file_key(args):
    """Extract --file key from args. Returns (file_key, remaining_args).

    Accepts a bare key or a full Figma URL (figma.com/design/<key>/... or
    figma.com/file/<key>/...).
    """
    file_key = None
    remaining = []
    i = 0
    while i < len(args):
        if args[i] == "--file" and i + 1 < len(args):
            raw = args[i + 1]
            match = re.search(r"figma\.com/(?:design|file)/([^/?]+)", raw)
            file_key = match.group(1) if match else raw
            i += 2
        else:
            remaining.append(args[i])
            i += 1
    if not file_key:
        print("Error: --file <key-or-url> is required.", file=sys.stderr)
        sys.exit(1)
    return file_key, remaining
