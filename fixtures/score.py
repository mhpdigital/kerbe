#!/usr/bin/env python3
"""Score a produced promise ledger against a fixture's EXPECTED.json.

Acceptance harness for kerbe:coverage: every skill change must keep all
require checks passing and all forbid checks clean on every fixture.
"""
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "skills" / "coverage" / "scripts"))
from verdict import Malformed, parse  # noqa: E402


def main(argv):
    if len(argv) < 3:
        print("usage: score.py EXPECTED.json PROMISES.md [OUT_OF_SCOPE.md]", file=sys.stderr)
        return 1
    expected = json.loads(pathlib.Path(argv[1]).read_text())
    try:
        _, rows = parse(argv[2])
    except Malformed as e:
        print("FAIL ledger is malformed: " + str(e))
        return 1
    failures = 0
    for req in expected.get("require", []):
        rx = re.compile(req["match_re"])
        hit = any(r[req["column"]] == req["value"]
                  and (rx.search(r["promise"]) or rx.search(r["evidence"]))
                  for r in rows)
        print(("PASS " if hit else "FAIL ") + "require: " + req["desc"])
        failures += 0 if hit else 1
    for forb in expected.get("forbid", []):
        # A decoy is "counted" when it became a promise row, so match the promise
        # cell only — evidence legitimately cites decoys as context (e.g. a dead
        # helper mentioned while proving a dead link).
        rx = re.compile(forb["any_re"])
        hit = [r["id"] for r in rows if rx.search(r["promise"])]
        ok = not hit
        print(("PASS " if ok else "FAIL ") + "forbid: " + forb["desc"]
              + ("" if ok else " (counted in " + " ".join(hit) + ")"))
        failures += 0 if ok else 1
    print("score: %d checks, %d failed" % (
        len(expected.get("require", [])) + len(expected.get("forbid", [])), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
