#!/usr/bin/env python3
"""Local HTTP server for the rwalk review screen. Stdlib only.

Serves the screen, the bundle, agent pre-reads and asks, and writes verdicts into
REVIEW.md through qr.write_verdict(). Binds 127.0.0.1 on a random port, checks a
per-run token and the Host header on every /api/* request, and exits on Finish or
after an idle period. stdout is a two-line JSON protocol: the URL on start, the
result on exit. Anything else goes to stderr.
"""
import argparse
import hmac
import importlib.util
import json
import os
import queue
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from contextlib import contextmanager
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
MAX_BODY = 64 * 1024
FALLBACK_PAGE = ("<!doctype html><meta charset=utf-8><title>rwalk</title>"
                 "<p>Review screen file missing. Close this window and run rwalk "
                 "without --screen.</p>")


def _load(name):
    spec = importlib.util.spec_from_file_location("rwalk_" + name, HERE / (name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["rwalk_" + name] = mod
    spec.loader.exec_module(mod)
    return mod


qr_mod = _load("qr")
bundle_mod = _load("bundle")
discuss = _load("discuss")
editor = _load("classify_editor_open")

MECHANISM_CAP = 600


def cap(text, limit=MECHANISM_CAP):
    """Cap a pre-read stored as a Verified mechanism at limit characters, ending in …."""
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


DECIDED_MAP = {"FIX QUEUED": "fix", "BUG PENDING": "bug", "DEFERRED": "defer"}


def count_key(status):
    if status is None:
        return "open"
    if status in DECIDED_MAP:
        return DECIDED_MAP[status]
    if status.startswith("BUG-"):
        return "bug"
    return "verified"


def atomic_write(path, text):
    """Write text to a temp file beside path, then os.replace it over path, so a
    concurrent reader sees the old file or the new one, never half of it. The path is
    resolved first, so a symlinked file is written through and keeps its link."""
    path = Path(path).resolve()
    tmp = tempfile.NamedTemporaryFile("w", dir=str(path.parent), delete=False,
                                      encoding="utf-8", newline="",
                                      prefix=path.name + ".", suffix=".tmp")
    try:
        with tmp:
            tmp.write(text)
        try:
            shutil.copymode(str(path), tmp.name)
        except OSError:
            pass
        os.replace(tmp.name, str(path))
    except BaseException:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
        raise


@contextmanager
def stdout_to_stderr():
    """stdout is the JSON protocol; point fd 1 at stderr while a browser launcher runs."""
    try:
        sys.stdout.flush()
        saved = os.dup(1)
    except (OSError, ValueError):
        yield
        return
    try:
        os.dup2(2, 1)
        yield
    finally:
        os.dup2(saved, 1)
        os.close(saved)


class App:
    def __init__(self, a):
        self.review = Path(a.review)
        self.repo = Path(a.repo).resolve()
        self.discussion = Path(a.discussion)
        self.discuss_cmd = a.discuss_cmd
        self.editor_template = a.editor_template
        self.today = a.today
        self.screen = Path(a.screen_file) if a.screen_file else \
            HERE.parent / "screen" / "index.html"
        self.token = secrets.token_urlsafe(24)
        self.port = None
        self.lock = threading.Lock()
        self.last_request = time.monotonic()
        self.finished = False
        self.reason = None
        self.done = threading.Event()
        # Row text (title, why) is frozen here at startup; statuses are re-read from
        # REVIEW.md on every GET /api/bundle. bundle.build cannot be re-run live because
        # it errors once every row is decided (there is no current QR left to build).
        self.bundle = bundle_mod.build(self.review, self.repo, a.base, a.slice)
        self.qr_id = self.bundle["qr"]
        self.rows = {r["id"]: r for r in self.bundle["rows"]}
        self.history = {rid: [] for rid in self.rows}
        self.preread = {rid: {"status": "pending", "text": ""} for rid in self.rows}
        self.pq = queue.PriorityQueue()
        self.seq = 0
        self.started = set()
        self.bumped = set()
        self.pcond = threading.Lock()
        for i, rid in enumerate(self.rows):
            self.pq.put((i + 1, rid))
        self.seq = len(self.rows) + 1

    # -- REVIEW.md ----------------------------------------------------------
    # Writers hold app.lock and replace the file atomically (atomic_write); readers
    # (current, live_bundle, counts) take no lock and rely on that atomic replace.
    # Only main() holds the lock around the final counts() and exit line.
    def read_review(self):
        # newline="" keeps CRLF intact, so write_verdict sees and keeps the file's EOLs.
        with open(self.review, encoding="utf-8", newline="") as f:
            return f.read()

    def current(self):
        text = self.read_review()
        for q in qr_mod.parse(text):
            if q.id == self.qr_id:
                return q
        return None

    def live_bundle(self):
        q = self.current()
        b = dict(self.bundle)
        if q is not None:
            st = {r.id: r.status for r in q.rows}
            b["rows"] = [dict(r, status=st.get(r["id"], r["status"])) for r in self.bundle["rows"]]
            b["tier3"] = {"status": q.tier3_status, "files": q.tier3_files}
        return b

    def counts(self):
        c = {"verified": 0, "fix": 0, "bug": 0, "defer": 0, "open": 0}
        q = self.current()
        for r in (q.rows if q else []):
            c[count_key(r.status)] += 1
        return c

    def when(self):
        return self.today or datetime.now().strftime("%Y-%m-%d %H:%M")

    # -- pre-reads ----------------------------------------------------------
    def preread_worker(self):
        while True:
            try:
                _, rid = self.pq.get(timeout=0.2)
            except queue.Empty:
                if self.done.is_set():
                    return
                continue
            if self.done.is_set():
                return
            with self.pcond:
                if rid in self.started:
                    continue
                self.started.add(rid)
            try:
                prompt = discuss.build_prompt(self.rows[rid], [], "", "preread")
                ok, text = discuss.run(self.discuss_cmd, prompt, self.repo)
                self.preread[rid] = {"status": "ready" if ok else "error",
                                     "text": text.strip()}
            except Exception as e:  # one bad row must not stop the others
                print("pre-read failed for %s: %s" % (rid, e), file=sys.stderr)
                self.preread[rid] = {"status": "error", "text": "pre-read failed"}

    def bump(self, rid):
        with self.pcond:
            if (rid not in self.started and rid not in self.bumped
                    and self.preread[rid]["status"] == "pending"):
                self.bumped.add(rid)
                self.pq.put((0, rid))

    # -- editor / window ----------------------------------------------------
    def open_row(self, rid):
        row = self.rows.get(rid)
        if row is None:
            return {"ok": False, "reason": "unknown row"}
        if not self.editor_template:
            return {"ok": False, "reason": "no editor configured"}
        if not row.get("file"):
            return {"ok": False, "reason": "row has no file"}
        path = (self.repo / row["file"]).resolve()
        if self.repo != path and self.repo not in path.parents:
            return {"ok": False, "reason": "file is outside the repository"}
        try:
            argv = editor.classify(self.editor_template, str(path), row.get("start") or 1)["argv"]
            subprocess.Popen(argv, shell=False, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except editor.UnsafeEditorCommand as e:
            return {"ok": False, "reason": str(e)}
        except OSError as e:
            return {"ok": False, "reason": "cannot launch editor: %s" % e}
        return {"ok": True}

    def finish(self, finished, reason):
        if self.done.is_set():
            return
        self.finished, self.reason = finished, reason
        self.done.set()

    def touch(self):
        self.last_request = time.monotonic()


def make_handler(app):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *a):
            pass

        def send_json(self, code, obj):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def authorised(self):
            tok = self.headers.get("X-Kerbe-Token", "")
            host = self.headers.get("Host", "")
            ok = hmac.compare_digest(tok.encode("utf-8"), app.token.encode("utf-8")) \
                and host == "127.0.0.1:%d" % app.port
            if not ok:
                self.send_json(403, {"error": "forbidden"})
            return ok

        def read_body(self):
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                self.send_json(400, {"error": "bad Content-Length"})
                return None
            if n < 0:
                self.send_json(400, {"error": "bad Content-Length"})
                return None
            if n > MAX_BODY:
                self.send_json(413, {"error": "body too large"})
                return None
            raw = self.rfile.read(n) if n else b""
            try:
                obj = json.loads(raw.decode("utf-8") or "{}")
            except (ValueError, UnicodeDecodeError):
                self.send_json(400, {"error": "bad JSON"})
                return None
            if not isinstance(obj, dict):
                self.send_json(400, {"error": "body must be a JSON object"})
                return None
            return obj

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == "/":
                app.touch()
                try:
                    body = app.screen.read_bytes()
                except OSError:
                    body = FALLBACK_PAGE.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if not u.path.startswith("/api/"):
                return self.send_json(404, {"error": "not found"})
            if not self.authorised():
                return
            app.touch()
            try:
                if u.path == "/api/bundle":
                    return self.send_json(200, app.live_bundle())
                if u.path == "/api/preread":
                    rid = (parse_qs(u.query).get("row") or [""])[0]
                    if rid not in app.rows:
                        return self.send_json(404, {"error": "unknown row"})
                    app.bump(rid)
                    return self.send_json(200, app.preread[rid])
            except (bundle_mod.BundleError, OSError, UnicodeDecodeError) as e:
                return self.send_json(500, {"error": str(e)})
            except Exception as e:  # never drop the connection or send a trace
                print("internal error on %s: %r" % (u.path, e), file=sys.stderr)
                return self.send_json(500, {"error": "internal error"})
            self.send_json(404, {"error": "not found"})

        def do_POST(self):
            path = urlparse(self.path).path
            if not path.startswith("/api/"):
                return self.send_json(404, {"error": "not found"})
            if not self.authorised():
                return
            app.touch()
            body = self.read_body()
            if body is None:
                return
            h = {"/api/verdict": self.verdict, "/api/ask": self.ask,
                 "/api/open": self.open, "/api/finish": self.fin}.get(path)
            if h is None:
                return self.send_json(404, {"error": "not found"})
            try:
                h(body)
            except (OSError, UnicodeDecodeError) as e:
                self.send_json(500, {"error": str(e)})
            except Exception as e:  # never drop the connection or send a trace
                print("internal error on %s: %r" % (path, e), file=sys.stderr)
                self.send_json(500, {"error": "internal error"})

        def need(self, body, key):
            v = body.get(key)
            if not isinstance(v, str) or not v:
                self.send_json(400, {"error": "missing field: %s" % key})
                return None
            return v

        def verdict(self, body):
            rid = self.need(body, "row")
            if rid is None:
                return
            kind = body.get("kind") or ("tier3" if rid == "tier3" else None)
            if not isinstance(kind, str):
                return self.send_json(400, {"error": "missing field: kind"})
            fields = {}
            for k in ("mechanism", "option", "detail", "proves", "reason"):
                v = body.get(k, "")
                if v is None:
                    v = ""
                if not isinstance(v, str):
                    return self.send_json(400, {"error": "field %s must be a string" % k})
                fields[k] = v
            today = app.today or date.today().isoformat()
            with app.lock:
                if kind == "verified" and not fields["mechanism"].strip():
                    pr = app.preread.get(rid)
                    if pr and pr["status"] == "ready":
                        fields["mechanism"] = cap(pr["text"])
                try:
                    text = qr_mod.write_verdict(app.read_review(), app.qr_id, rid,
                                                qr_mod.Verdict(kind=kind, **fields), today)
                except (qr_mod.UnknownRow, qr_mod.InvalidVerdict) as e:
                    return self.send_json(400, {"error": str(e)})
                atomic_write(app.review, text)
                q = app.current()
            if rid == "tier3":
                status = q.tier3_status if q else None
            else:
                status = next((r.status for r in q.rows if r.id == rid), None) if q else None
            self.send_json(200, {"ok": True, "status": status})

        def open(self, body):
            rid = self.need(body, "row")
            if rid is None:
                return
            self.send_json(200, app.open_row(rid))

        def fin(self, body):
            self.send_json(200, {"ok": True})
            app.finish(True, "challenge" if body.get("challenge") is True else "finish")

        def ask(self, body):
            rid = self.need(body, "row")
            question = self.need(body, "question") if rid else None
            if rid is None or question is None:
                return
            row = app.rows.get(rid)
            if row is None:
                return self.send_json(400, {"error": "unknown row"})
            prompt = discuss.build_prompt(row, list(app.history[rid]), question, "ask")
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Connection", "close")
            self.end_headers()
            result = []
            t = threading.Thread(
                target=lambda: result.append(discuss.run(app.discuss_cmd, prompt, app.repo)),
                daemon=True)
            t.start()
            start = time.monotonic()
            try:
                while True:
                    t.join(2)
                    app.touch()
                    if not t.is_alive():
                        break
                    self.wfile.write((json.dumps({"type": "status", "elapsed":
                                                  int(time.monotonic() - start)}) + "\n").encode())
                    self.wfile.flush()
                ok, text = result[0]
                if ok:
                    answer, opts = discuss.parse_options(text)
                    answer = answer.strip()
                    with app.lock:
                        app.history[rid].append((question, answer))
                        discuss.append_discussion(app.discussion, app.qr_id, row, question,
                                                  answer, app.when())
                    msg = {"type": "answer", "text": answer, "options": [list(o) for o in opts]}
                else:
                    msg = {"type": "error", "text": text}
                self.wfile.write((json.dumps(msg) + "\n").encode())
                self.wfile.flush()
            except (BrokenPipeError, ConnectionError):
                pass
            except Exception as e:  # any failure becomes an error line, never a trace
                print("ask failed for %s: %r" % (rid, e), file=sys.stderr)
                err = str(e) if isinstance(e, OSError) else "internal error"
                try:
                    self.wfile.write((json.dumps({"type": "error", "error": err, "text": err})
                                      + "\n").encode())
                except OSError:
                    pass

    return Handler


def open_window(url):
    try:
        if sys.platform == "darwin":
            for app_name in ("Google Chrome", "Microsoft Edge"):
                if Path("/Applications/%s.app" % app_name).exists():
                    subprocess.Popen(["open", "-na", app_name, "--args", "--app=" + url],
                                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
                    return
        else:
            for exe in ("google-chrome", "chromium", "microsoft-edge"):
                if shutil.which(exe):
                    subprocess.Popen([exe, "--app=" + url], stdin=subprocess.DEVNULL,
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
        with stdout_to_stderr():
            webbrowser.open(url)
    except Exception as e:  # window is a convenience; never break the protocol
        print("could not open a window: %s" % e, file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--review", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--slice", required=True)
    ap.add_argument("--discussion", required=True)
    ap.add_argument("--discuss-cmd", required=True)
    ap.add_argument("--editor-template")
    ap.add_argument("--idle-minutes", type=float, default=30)
    ap.add_argument("--idle-seconds", type=float, help=argparse.SUPPRESS)
    ap.add_argument("--screen-file", help=argparse.SUPPRESS)
    ap.add_argument("--no-window", action="store_true")
    ap.add_argument("--today")
    a = ap.parse_args(argv)
    try:
        app = App(a)
    except (bundle_mod.BundleError, OSError, UnicodeDecodeError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 2
    idle = a.idle_seconds if a.idle_seconds is not None else a.idle_minutes * 60

    ThreadingHTTPServer.daemon_threads = True
    ThreadingHTTPServer.block_on_close = False
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
    app.port = server.server_address[1]
    url = "http://127.0.0.1:%d/#t=%s" % (app.port, app.token)

    threading.Thread(target=app.preread_worker, daemon=True).start()
    threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.2},
                     daemon=True).start()

    print(json.dumps({"url": url}), flush=True)
    if not a.no_window:
        open_window(url)

    while not app.done.wait(0.25):
        if time.monotonic() - app.last_request > idle:
            app.finish(False, "idle")
    time.sleep(0.2)  # let the /api/finish response flush
    server.shutdown()
    server.server_close()
    # Take the write lock and keep it until the exit line is out, so no handler
    # thread can be mid-write when the process exits.
    app.lock.acquire()
    print(json.dumps({"finished": app.finished, "reason": app.reason,
                      "counts": app.counts()}), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
