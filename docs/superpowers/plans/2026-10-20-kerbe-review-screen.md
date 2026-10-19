# rwalk review screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `/kerbe:rwalk --screen` walks a QR in a local browser window (explanation, wrapped diff, discussion with pickable options, verdicts and detailed fix rulings) and writes `REVIEW.md` exactly as the terminal walk does.

**Architecture:** Three stdlib scripts in `skills/rwalk/scripts/`: `qr.py` parses QRs and rewrites one row; `bundle.py` turns the open QR plus `git diff` into one JSON bundle; `serve.py` is a token-protected `ThreadingHTTPServer` on 127.0.0.1 that serves `skills/rwalk/screen/index.html`, writes verdicts through `qr.py`, and runs the discussion command through `discuss.py`. The host agent starts the server, waits for it to exit, then does the commit, `kerbe:bug` and the fix batch in the terminal as today.

**Tech Stack:** Python 3 stdlib only (`http.server`, `subprocess`, `json`, `secrets`, `threading`), `unittest`; one vanilla HTML/CSS/JS file, no CDN, no build step.

**Spec:** `docs/specs/2026-10-20-review-screen.md` — read it first; decisions D1–D11 are cited by number below. **Screen design:** `docs/superpowers/plans/2026-10-20-kerbe-review-screen-design.md`.

## Global Constraints

- **This repo is PUBLIC.** No client-identifying strings. Fixtures use the invented `cards` domain.
- **Python:** stdlib only, `#!/usr/bin/env python3`, executable (`chmod +x`). No pip installs, no YAML parsing: the host agent reads `kerbe.yml` and passes values as arguments.
- **Harness neutrality:** skill bodies name no harness mechanism (`tests/test_portability.py` `HARNESS_TOKENS`). `skills/rwalk/SKILL.md` stays ≤ 6,000 bytes (`MAIN_SKILL_BYTE_BUDGETS`). Move text out only into a reference file that `SKILL.md` links; never delete a rule to fit.
- **No hidden-folder state.** Bundles go to a `tempfile.mkdtemp()` path. The screen uses no `localStorage`.
- **Never execute a QR Open cell** (D4). Editor launches go through `classify_editor_open.py` and run as argv with `shell=False`.
- **Git:** stage files one by one; every commit scoped with `-- <paths>`; no co-author line in commit messages.
- Tests run with `python3 -m unittest tests.<module>` from the repo root.

## Review Focus

1. User text containing `|`, backticks or line breaks must not break the QR table. Pinned in Task 2 (`test_fix_detail_is_cell_escaped`).
2. `REVIEW.md` edited in the terminal while the screen is open must not be overwritten with stale content. Every write re-reads the file under a lock. Pinned in Task 2 (`test_write_uses_current_text`) and Task 5 (`test_verdict_rereads_file`).
3. A discussion command that hangs, exits non-zero or is missing must give an error message in the panel, not a hung request. Pinned in Task 4 (`test_timeout_returns_error`, `test_missing_command_returns_error`).
4. A request from another origin or without the token must change nothing. Pinned in Task 5 (`test_missing_token_403`, `test_wrong_host_403`).
5. A row whose file is not in the diff (deleted file, renamed file, range outside every hunk) must still render, as context lines from `Reviewed at`. Pinned in Task 3 (`test_row_outside_hunks_shows_context`).

---

### Task 1: Bring the editor-open classifier onto main

**Files:**
- Modify (by cherry-pick): `skills/rwalk/SKILL.md`, `kerbe.yml.example`
- Create (by cherry-pick): `skills/rwalk/scripts/classify_editor_open.py`, `tests/test_editor_open.py`

**Interfaces:**
- Produces: `classify_editor_open.classify(template: str, file_name: str, line: int) -> dict` with keys `classification`, `argv`, `approval_prefix`, `shell_command`; raises `UnsafeEditorCommand`.

- [ ] **Step 1:** `git cherry-pick 45809a5 755e075` onto `main`. Branch `fix/editor-open-permission-classifier` is based on an older main; take only these two commits, never merge the branch.
- [ ] **Step 2:** Resolve conflicts in favour of main's current text, keeping the "Open safely" paragraph and the `kerbe.yml.example` note.
- [ ] **Step 3:** Run `python3 -m unittest tests.test_editor_open tests.test_portability`. Expected: PASS. If the rwalk byte budget fails, move the Glue batching paragraph of `SKILL.md` into a new `references/turns.md` linked from "Item turn", and rerun.
- [ ] **Step 4:** Commit with a pathspec listing the files above (plus `references/turns.md` if created).

### Task 2: QR parser and row writer

**Files:**
- Create: `skills/rwalk/scripts/qr.py`
- Test: `tests/test_rwalk_qr.py`

**Interfaces:**
- Produces:
  - `Row` dataclass: `qr: str, id: str, tier: str ("B"|"G"|"F"), title: str, file: str | None, start: int | None, end: int | None, why: str, status: str | None, line_no: int`
  - `QR` dataclass: `id: str, rows: list[Row], tier3_status: str | None, reviewed_at: str | None`
  - `parse(text: str) -> list[QR]`
  - `is_closed(row: Row) -> bool`, `is_decided(row: Row) -> bool` (`FIX QUEUED`, `BUG PENDING`)
  - `current_qr(qrs: list[QR]) -> QR | None` (newest QR with a row neither closed nor decided)
  - `Verdict` dataclass: `kind: str ("verified"|"fix"|"bug"|"defer"|"tier3"), mechanism="", option="", detail="", proves="", reason=""`
  - `write_verdict(text: str, qr_id: str, row_id: str, v: Verdict, today: str) -> str`
  - `escape_cell(s: str) -> str`
  - `UnknownRow(KeyError)`, `InvalidVerdict(ValueError)`

Rows are table rows whose first cell matches `[BG]\d+` in Business-logic and Glue, and flag paragraphs opening `**F<n> — <severity>: …**` in Flags. `file` is the first backticked path; `start`/`end` come from `L(\d+)(?:[–-](\d+))?` or `:(\d+)`. `reviewed_at` is the QR's `**Reviewed at:**` value. Status is the unstruck bold token from the closed list in `SKILL.md`, plus `FIX QUEUED` and `BUG PENDING`.

- [ ] **Step 1: Write the failing tests.** Use the `GOOD` text from `tests/test_check_review.py` extended with a `**Reviewed at:** \`a41c9e2\`` line, a second B row and a flag paragraph `**F1 — Medium: draft cards readable by id** …`.

```python
def test_parse_rows_and_order(self):
    qr = qr_mod.parse(TEXT)[0]
    self.assertEqual([r.id for r in qr.rows], ["B1", "B2", "G1", "F1"])
    b1 = qr.rows[0]
    self.assertEqual((b1.file, b1.start, b1.end), ("src/Controller/CardController.php", 20, 41))
    self.assertEqual(qr.reviewed_at, "a41c9e2")

def test_verified_row_syntax(self):
    out = qr_mod.write_verdict(TEXT, "QR-1", "B1", Verdict("verified", mechanism="findVisibleFor() filters on owner"), "2026-10-20")
    row = next(l for l in out.splitlines() if l.startswith("| B1 "))
    self.assertIn("**RESOLVED (VERIFIED) 2026-10-20**", row)
    self.assertIn("Confirmed: findVisibleFor() filters on owner", row)
    self.assertTrue(row.startswith("| B1 | ~~"))

def test_fix_with_option_and_detail(self):
    v = Verdict("fix", option="O2: owner gets a restore page", detail="30-day window only\nno change to findVisibleFor()", proves="owner at 10 days gets 200")
    row = next(l for l in qr_mod.write_verdict(TEXT, "QR-1", "B1", v, "2026-10-20").splitlines() if l.startswith("| B1 "))
    self.assertIn("**FIX QUEUED 2026-10-20**", row)
    self.assertIn("Ruled: O2: owner gets a restore page<br>30-day window only<br>no change to findVisibleFor() · proves it: owner at 10 days gets 200", row)

def test_fix_detail_is_cell_escaped(self):
    v = Verdict("fix", detail="use a | b\nthen `x`", proves="p")
    out = qr_mod.write_verdict(TEXT, "QR-1", "B1", v, "2026-10-20")
    row = next(l for l in out.splitlines() if l.startswith("| B1 "))
    self.assertIn("use a \\| b<br>then `x`", row)
    self.assertEqual(qr_mod.parse(out)[0].rows[0].status, "FIX QUEUED")

def test_other_bytes_identical(self):
    out = qr_mod.write_verdict(TEXT, "QR-1", "B2", Verdict("defer", reason="later"), "2026-10-20")
    changed = [i for i, (a, b) in enumerate(zip(TEXT.splitlines(), out.splitlines())) if a != b]
    self.assertEqual(len(changed), 1)
    self.assertEqual(len(TEXT.splitlines()), len(out.splitlines()))

def test_flag_paragraph_bug_pending(self):
    out = qr_mod.write_verdict(TEXT, "QR-1", "F1", Verdict("bug", detail="drafts leak"), "2026-10-20")
    self.assertIn("**BUG PENDING 2026-10-20**", out)
    self.assertTrue(qr_mod.is_decided(qr_mod.parse(out)[0].rows[3]))

def test_tier3_accept_line(self):
    out = qr_mod.write_verdict(TEXT, "QR-1", "tier3", Verdict("tier3"), "2026-10-20")
    self.assertRegex(out, r"### Boilerplate[^\n]*\n\n\*\*TIER 3 ACCEPTED 2026-10-20\*\* — 1 files")

def test_unknown_row_and_closed_row_rejected(self):
    with self.assertRaises(qr_mod.UnknownRow):
        qr_mod.write_verdict(TEXT, "QR-1", "B9", Verdict("verified", mechanism="m"), "2026-10-20")
    once = qr_mod.write_verdict(TEXT, "QR-1", "B1", Verdict("verified", mechanism="m"), "2026-10-20")
    with self.assertRaises(qr_mod.InvalidVerdict):
        qr_mod.write_verdict(once, "QR-1", "B1", Verdict("verified", mechanism="m"), "2026-10-20")

def test_fix_needs_ruling_and_proof(self):
    with self.assertRaises(qr_mod.InvalidVerdict):
        qr_mod.write_verdict(TEXT, "QR-1", "B1", Verdict("fix", proves="p"), "2026-10-20")
    with self.assertRaises(qr_mod.InvalidVerdict):
        qr_mod.write_verdict(TEXT, "QR-1", "B1", Verdict("fix", detail="d"), "2026-10-20")

def test_write_uses_current_text(self):
    edited = TEXT.replace("ownership check", "ownership check (edited in terminal)")
    out = qr_mod.write_verdict(edited, "QR-1", "B2", Verdict("verified", mechanism="m"), "2026-10-20")
    self.assertIn("(edited in terminal)", out)

def test_written_review_still_passes_checker(self):
    out = qr_mod.write_verdict(TEXT, "QR-1", "B1", Verdict("verified", mechanism="m"), "2026-10-20")
    # run fixtures/check_review.py on `out` as tests/test_check_review.run() does; expect exit 0
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_rwalk_qr`. Expected: FAIL, `qr` not found.
- [ ] **Step 3:** Implement `qr.py`. Row syntax is exactly `references/recording.md`: id cell unstruck, the concern cell struck with the bold status appended, Why cell replaced by `~~{why}~~ Confirmed: …` / `Ruled: … · proves it: …` / `Bug: …` / `Deferred: …`, Open cell struck. A fix ruling is `{option}<br>{detail}` with empty parts dropped. A fix needs `proves` and at least one of `option`/`detail`. Verified needs `mechanism`. Flag paragraphs: strike the paragraph text after the bold id and append status and ruling.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit `-- skills/rwalk/scripts/qr.py tests/test_rwalk_qr.py`.

### Task 3: Bundle builder

**Files:**
- Create: `skills/rwalk/scripts/bundle.py`
- Test: `tests/test_rwalk_bundle.py`

**Interfaces:**
- Consumes: `qr.parse`, `qr.current_qr`, `Row`.
- Produces: `build(review_path: Path, repo: Path, base: str, slice_name: str) -> dict` and CLI `bundle.py --review P --repo P --base REF --slice NAME --out P`. Bundle shape:

```json
{"slice": "cards", "qr": "QR-1", "reviewed_at": "a41c9e2", "tier3": {"status": null, "files": 1},
 "rows": [{"id": "B1", "tier": "B", "title": "…", "file": "src/…", "start": 20, "end": 41,
           "why": "…", "status": null,
           "diff": [{"t": "h", "text": "@@ …"}, {"t": "a|d|c", "old": 21, "new": null, "text": "…", "in": true}]}]}
```

Diff per row: `git -C repo diff -U3 {base}...{reviewed_at} -- {file}` (`HEAD` when `reviewed_at` is missing). Keep hunks whose new-side range overlaps `[start-5, end+5]`. `in` marks lines within `[start, end]`. No hunk overlaps, or the file has no diff: emit `c` lines `start..end` from `git show {reviewed_at}:{file}`. File missing at `reviewed_at`: a single `h` line `file not present at {sha}`. Rows without a file get `diff: []`.

- [ ] **Step 1: Write the failing tests.** `setUp` builds a temp git repo: commit `src/Controller/CardController.php` (40 lines) on `main`, branch `slice/cards`, change lines 20–24, commit, and write `REVIEW.md` from Task 2's fixture with `Reviewed at` set to the new sha.

```python
def test_rows_and_meta(self):
    b = bundle.build(self.review, self.repo, "main", "cards")
    self.assertEqual(b["qr"], "QR-1"); self.assertEqual([r["id"] for r in b["rows"]], ["B1", "B2", "G1", "F1"])

def test_row_diff_marks_in_range(self):
    d = self.row("B1")["diff"]
    self.assertTrue(any(l["t"] == "a" and l["in"] for l in d))
    self.assertEqual(d[0]["t"], "h")

def test_row_outside_hunks_shows_context(self):
    d = self.row("G1")["diff"]   # G1 cites L12, outside the changed hunk
    self.assertTrue(d and all(l["t"] == "c" for l in d))
    self.assertEqual(d[0]["new"], 12)

def test_missing_file_header(self):
    # point B2 at src/Gone.php
    self.assertIn("not present", self.row("B2")["diff"][0]["text"])

def test_cli_writes_json(self):
    # run bundle.py with --out in a mkdtemp dir; json.load succeeds; exit code 0
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_rwalk_bundle`. Expected: FAIL.
- [ ] **Step 3:** Implement `bundle.py`; parse unified diff hunk headers `@@ -a,b +c,d @@`. All git calls are argv lists, never `shell=True`.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit `-- skills/rwalk/scripts/bundle.py tests/test_rwalk_bundle.py`.

### Task 4: Discussion bridge

**Files:**
- Create: `skills/rwalk/scripts/discuss.py`
- Test: `tests/test_rwalk_discuss.py`

**Interfaces:**
- Consumes: a bundle row dict (Task 3).
- Produces:
  - `build_prompt(row: dict, history: list[tuple[str, str]], question: str, kind: str ("ask"|"preread")) -> str`
  - `run(cmd: str, prompt: str, cwd: Path, timeout: int = 300) -> tuple[bool, str]` → `(ok, text_or_error)`
  - `parse_options(text: str) -> tuple[str, list[tuple[str, str]]]` → `(body, [("O0", "…"), …])`
  - `append_discussion(path: Path, qr_id: str, row: dict, question: str, answer: str, when: str) -> None`

Prompt rules (fixed text in `discuss.py`): the agent may read files but never edits them; for `preread`, explain the mechanism in at most two sentences and state uncertainty; for `ask`, answer the question and, when there is more than one reasonable choice, end with lines `O0: …`, `O1: …`. `run` uses `shlex.split(cmd)`, `stdin=prompt`, `shell=False`, the given timeout.

`REVIEW-discussion.md` format: one `## QR-1/B1 — {title}` section per row, created at the end on first use; each exchange appends `**You ({when}):** {question}` and `**Agent:** {answer}` under it.

- [ ] **Step 1: Write the failing tests.** Fake commands are small scripts written into the temp dir and called by `sys.executable`.

```python
def test_parse_options(self):
    body, opts = discuss.parse_options("It returns 404.\nOptions:\nO0: keep it\nO1: 410 Gone\nO2: restore page")
    self.assertEqual(opts, [("O0", "keep it"), ("O1", "410 Gone"), ("O2", "restore page")])
    self.assertEqual(body.strip(), "It returns 404.\nOptions:")

def test_no_options(self):
    self.assertEqual(discuss.parse_options("plain")[1], [])

def test_prompt_replays_history(self):
    p = discuss.build_prompt(ROW, [("q1", "a1")], "q2", "ask")
    self.assertLess(p.index("q1"), p.index("a1")); self.assertLess(p.index("a1"), p.index("q2"))
    self.assertIn("O0:", p)

def test_run_passes_stdin(self):
    ok, out = discuss.run(f"{sys.executable} {self.echo}", "hello", self.tmp)
    self.assertTrue(ok); self.assertIn("hello", out)

def test_timeout_returns_error(self):
    ok, out = discuss.run(f"{sys.executable} {self.sleeper}", "x", self.tmp, timeout=1)
    self.assertFalse(ok); self.assertIn("timed out", out)

def test_missing_command_returns_error(self):
    ok, out = discuss.run("no-such-binary-kerbe", "x", self.tmp)
    self.assertFalse(ok); self.assertIn("not found", out)

def test_nonzero_exit_returns_stderr(self):
    ok, out = discuss.run(f"{sys.executable} {self.failer}", "x", self.tmp)
    self.assertFalse(ok); self.assertIn("boom", out)

def test_append_discussion_groups_by_row(self):
    # two appends for B1 and one for B2 → exactly one "## QR-1/B1" heading, B1's two exchanges under it
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_rwalk_discuss`. Expected: FAIL.
- [ ] **Step 3:** Implement `discuss.py`.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5:** Commit `-- skills/rwalk/scripts/discuss.py tests/test_rwalk_discuss.py`.

### Task 5: Local server

**Files:**
- Create: `skills/rwalk/scripts/serve.py`
- Test: `tests/test_rwalk_serve.py`

**Interfaces:**
- Consumes: `qr.parse`, `qr.write_verdict`, `Verdict`, `bundle.build`, `discuss.*`, `classify_editor_open.classify`.
- Produces: CLI

```
serve.py --review P --repo P --base REF --slice NAME --discussion P
         --discuss-cmd CMD [--editor-template T] [--idle-minutes 30] [--no-window] [--today YYYY-MM-DD]
```

On start it prints one JSON line `{"url": "http://127.0.0.1:{port}/#t={token}"}` and flushes. On exit it prints `{"finished": true|false, "reason": "finish"|"idle", "counts": {"verified": n, "fix": n, "bug": n, "defer": n, "open": n}}` and exits 0.

Routes as in the spec. Every `/api/*` request needs header `X-Kerbe-Token: {token}` and `Host: 127.0.0.1:{port}`, else 403 with no side effect. POST bodies are JSON:

| Route | Body | Response |
|---|---|---|
| `GET /api/bundle` | — | bundle with each row's `status` re-read from `REVIEW.md` |
| `GET /api/preread?row=B1` | — | `{"status": "pending"|"ready"|"error", "text": "…"}` |
| `POST /api/verdict` | `{"row": "B1"|"tier3", "kind": …, "mechanism"?, "option"?, "detail"?, "proves"?, "reason"?}` | `{"ok": true, "status": "FIX QUEUED"}`; 400 `{"error": …}` on `UnknownRow`/`InvalidVerdict` |
| `POST /api/ask` | `{"row": "B1", "question": "…"}` | NDJSON, `Connection: close`: `{"type":"status","elapsed":s}` every 2 s, then `{"type":"answer","text":…,"options":[[id,text]]}` or `{"type":"error","text":…}` |
| `POST /api/open` | `{"row": "B1"}` | `{"ok": true}` or `{"ok": false, "reason": …}` |
| `POST /api/finish` | `{}` | `{"ok": true}`, then shutdown |

`verdict` and `discussion` writes hold one `threading.Lock` and re-read the file inside it. Mechanism for `verified` defaults to the row's ready pre-read when the body omits it. Pre-reads run in one background thread over the QR's rows; `GET /api/preread` for a row not yet started moves it to the front. `open` resolves the absolute file from `repo` and the row, never from the request. The window opens with Chrome or Edge `--app={url}` when found (`open -na "Google Chrome" --args --app=…` on macOS, `google-chrome`/`chromium`/`microsoft-edge` on Linux), else `webbrowser.open`. `--no-window` skips it for tests.

- [ ] **Step 1: Write the failing tests.** Start `serve.py --no-window --idle-minutes 1` as a subprocess against Task 3's temp repo, with `--discuss-cmd` pointing at a fake script that prints `Answer.\nO0: a\nO1: b`. Read the URL line, then use `http.client`.

```python
def test_index_served_without_token(self): self.assertEqual(self.get("/", token=None).status, 200)
def test_missing_token_403(self): self.assertEqual(self.get("/api/bundle", token=None).status, 403)
def test_wrong_host_403(self): self.assertEqual(self.get("/api/bundle", host="evil.test").status, 403)
def test_bundle(self): self.assertEqual([r["id"] for r in self.json("GET", "/api/bundle")["rows"]], ["B1", "B2", "G1", "F1"])

def test_verdict_writes_row(self):
    r = self.json("POST", "/api/verdict", {"row": "B1", "kind": "fix", "option": "O1: b", "detail": "d", "proves": "p"})
    self.assertEqual(r["status"], "FIX QUEUED")
    self.assertIn("**FIX QUEUED", self.review.read_text())

def test_verdict_rereads_file(self):
    self.review.write_text(self.review.read_text().replace("ownership check", "ownership check (edited)"))
    self.json("POST", "/api/verdict", {"row": "B2", "kind": "verified", "mechanism": "m"})
    self.assertIn("(edited)", self.review.read_text())

def test_bad_verdict_400_no_write(self):
    before = self.review.read_text()
    self.assertEqual(self.post("/api/verdict", {"row": "B9", "kind": "verified", "mechanism": "m"}).status, 400)
    self.assertEqual(self.review.read_text(), before)

def test_ask_streams_answer_and_logs(self):
    lines = self.ndjson("/api/ask", {"row": "B1", "question": "what if the deck was deleted?"})
    ans = lines[-1]; self.assertEqual(ans["type"], "answer"); self.assertEqual(ans["options"], [["O0", "a"], ["O1", "b"]])
    self.assertIn("## QR-1/B1", self.discussion.read_text())

def test_open_ignores_request_paths(self):
    r = self.json("POST", "/api/open", {"row": "B1", "file": "/etc/passwd", "cmd": "rm -rf /"})
    self.assertFalse(r["ok"])   # server started without --editor-template → refused, nothing run

def test_finish_exits_with_counts(self):
    self.json("POST", "/api/verdict", {"row": "B1", "kind": "verified", "mechanism": "m"})
    self.json("POST", "/api/finish", {})
    out = json.loads(self.proc.stdout.readline())
    self.assertEqual(out["counts"]["verified"], 1); self.assertEqual(self.proc.wait(timeout=5), 0)
```

Idle exit: a separate test sets `--idle-minutes` via a hidden `--idle-seconds 2` argument used only by tests, and asserts `reason == "idle"` within 10 s.

- [ ] **Step 2:** Run `python3 -m unittest tests.test_rwalk_serve`. Expected: FAIL.
- [ ] **Step 3:** Implement `serve.py` on `http.server.ThreadingHTTPServer`; `protocol_version = "HTTP/1.0"` so the NDJSON response ends on close. Token from `secrets.token_urlsafe(24)`.
- [ ] **Step 4:** Run the tests. Expected: PASS. Also confirm no listening port is left: `lsof -nP -iTCP:{port}` prints nothing after finish.
- [ ] **Step 5:** Commit `-- skills/rwalk/scripts/serve.py tests/test_rwalk_serve.py`.

### Task 6: The screen

**Files:**
- Create: `skills/rwalk/screen/index.html`
- Modify: `tests/test_rwalk_serve.py` (add two tests)

**Interfaces:**
- Consumes: Task 5's routes and response shapes; token from `location.hash` (`#t=…`), sent as `X-Kerbe-Token`.

Build the layout in `docs/superpowers/plans/2026-10-20-kerbe-review-screen-design.md` (layout, keys, fixture rows, worked fix example, colour tokens): rail of rows grouped B/G/F with status pills; main column with Why + mechanism, file header with Open in editor, wrapped diff (`white-space: pre-wrap; overflow-wrap: anywhere`), discussion with Pick buttons on options, verdict buttons, fix panel (chosen option, decision detail textarea, proves-it textarea, live `REVIEW.md` preview), Finish. Keys `a f b d s j k e` are ignored while a text field has focus. A tier-3 panel with Accept appears first while `tier3.status` is null; its other button says "Challenge in the terminal" and calls finish (D10). After Finish the page shows "Walk handed back to the terminal" and makes no further requests. Light and dark via `prefers-color-scheme`. No external URLs.

- [ ] **Step 1: Write the failing tests.**

```python
def test_index_has_no_external_urls(self):
    html = (REPO / "skills/rwalk/screen/index.html").read_text()
    self.assertNotRegex(html, r"https?://(?!127\.0\.0\.1)")

def test_index_reads_token_from_fragment(self):
    html = (REPO / "skills/rwalk/screen/index.html").read_text()
    self.assertIn("location.hash", html); self.assertIn("X-Kerbe-Token", html)
    self.assertNotIn("localStorage", html)
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_rwalk_serve`. Expected: the two new tests FAIL.
- [ ] **Step 3:** Implement `index.html`.
- [ ] **Step 4:** Run the tests. Expected: PASS.
- [ ] **Step 5: Manual walk.** Start `serve.py` against Task 3's temp repo with the fake discuss command. In the window: accept tier 3, verify B1, ask on B2 and Pick O1 then queue a fix with a two-line detail, raise a bug on F1, skip G1, Finish. Expected: `REVIEW.md` holds the tier-3 line, `RESOLVED (VERIFIED)`, `FIX QUEUED` with `<br>` in the ruling, `BUG PENDING`; G1 untouched; `fixtures/check_review.py` passes on it; no sideways scrollbar on the diff at 1280 px width.
- [ ] **Step 6:** Commit `-- skills/rwalk/screen/index.html tests/test_rwalk_serve.py`.

### Task 7: rwalk `--screen` mode

**Files:**
- Modify: `skills/rwalk/SKILL.md`, `skills/rwalk/references/recording.md`, `kerbe.yml.example`, `fixtures/ACCEPTANCE.md`
- Create: `skills/rwalk/references/screen.md`
- Test: `tests/test_portability.py` (existing budget and neutrality checks), `tests/test_rwalk_breakglass.py` (new)

**Interfaces:**
- Consumes: the CLIs of Tasks 3 and 5.
- Produces: config key `rwalk.discuss_cmd` (optional; default per host as in the spec); status `BUG PENDING` treated as decided.

Content:
- `SKILL.md`: argument `--screen` → read `references/screen.md` and follow it instead of the item turns. Without `--screen` the terminal walk runs as today (spec "Break glass"). Add `BUG PENDING` beside `FIX QUEUED` in "Resolve the position": the terminal walk raises each `BUG PENDING` row via `kerbe:bug` before its first item turn, then skips decided rows. Stay ≤ 6,000 bytes.
- `references/screen.md`: resolve slice and position as in `SKILL.md`; run `bundle.py` into `mktemp -d`; if it fails, or `serve.py` prints no URL line, or `serve.py` exits with no summary line, print one line `Screen failed: {error}. Continuing in the terminal.` and run the terminal walk from the current position; start `serve.py` in the background with values read from `kerbe.yml` (`planning_root`, `workspace.base_branch`, `editor_cmd`, `rwalk.discuss_cmd`), in a way the host can wait on without a time limit; print the URL for the human; when the process exits, read its summary line, then: replace each `BUG PENDING` via `kerbe:bug` with `BUG-{id} RAISED`; mirror each `DEFERRED` to Known Issues; commit per `recording.md` with `REVIEW-discussion.md` added to the pathspec; report the tally; run the fix batch. A tier-3 challenge from the screen continues as the terminal opening turn.
- `recording.md`: the `BUG PENDING` status line; fix rulings may carry `{option}<br>{detail}`; the commit pathspec includes `REVIEW-discussion.md` when present.
- `kerbe.yml.example`: commented `rwalk: discuss_cmd:` with both host defaults.
- `fixtures/ACCEPTANCE.md` rwalk gate: add step 5, a screen run on a scratch fixture QR that queues two fixes with multi-line detail and raises one bug; after Finish the bug is `BUG-{id} RAISED`, the fix batch starts with no question, and each fix worker's brief contains its detail text. Add step 6, break glass: start a screen run, verify one row and mark one `BUG PENDING`, kill `serve.py`; run `/kerbe:rwalk` without `--screen`. Expected: the bug is raised first, the walk resumes at the next open row, and the verified row is untouched. Then rename `skills/rwalk/scripts/serve.py` in the scratch plugin copy and run `--screen`. Expected: the "Screen failed" line, then a terminal item turn.

- [ ] **Step 1: Write the failing test** `tests/test_rwalk_breakglass.py`. It pins that the terminal walk never depends on screen files.

```python
SCREEN_FILES = ("bundle.py", "serve.py", "discuss.py", "qr.py", "index.html")

def test_terminal_walk_names_no_screen_script(self):
    for rel in ("skills/rwalk/SKILL.md", "skills/rwalk/references/recording.md"):
        text = (REPO / rel).read_text()
        for name in SCREEN_FILES:
            self.assertNotIn(name, text, f"{rel} must not depend on {name}")

def test_skill_routes_screen_to_reference(self):
    text = (REPO / "skills/rwalk/SKILL.md").read_text()
    self.assertIn("--screen", text); self.assertIn("references/screen.md", text)

def test_screen_reference_has_fallback(self):
    self.assertIn("Continuing in the terminal", (REPO / "skills/rwalk/references/screen.md").read_text())
```

- [ ] **Step 2:** Run `python3 -m unittest tests.test_rwalk_breakglass`. Expected: FAIL on the two `--screen` / `screen.md` assertions.
- [ ] **Step 3:** Write the content above.
- [ ] **Step 4:** Run `python3 -m unittest discover tests`. Expected: PASS, including the rwalk byte budget, harness-neutrality and break-glass checks.
- [ ] **Step 5:** Run the rwalk gate in `fixtures/ACCEPTANCE.md` on both hosts (Claude Code and Codex). Expected: all steps pass, including the new steps 5 and 6.
- [ ] **Step 6:** Commit with a pathspec listing the six files.

### Task 8: Release 0.13.0

**Files:**
- Modify: the three manifests, `README.md`, `docs/lifecycle.md`, `docs/lifecycle.svg`, `ROADMAP.md`, `tests/test_portability.py` (`PLUGIN_VERSION`)

- [ ] **Step 1:** Run the `kerbe-maintainer` skill for a minor release, 0.12.x → 0.13.0, with README and lifecycle diagram entries for `rwalk --screen`.
- [ ] **Step 2:** Run `python3 -m unittest discover tests`. Expected: PASS.
- [ ] **Step 3:** Tick the ROADMAP "rwalk review screen" entry, commit with a pathspec, and refresh the plugin cache on both hosts as the maintainer skill describes.
