import contextlib
import http.client
import importlib.util
import io
import json
import os
import pathlib
import queue
import shlex
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from tests.test_rwalk_qr import TEXT

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "rwalk" / "scripts" / "serve.py"
CTRL = "src/Controller/CardController.php"
FAKE = "import sys\nsys.stdin.read()\nprint('Answer.\\nO0: a\\nO1: b')\n"
# Sleeps 3 s only for a question containing "slow please"; pre-reads stay instant.
FAKE_SLOW = ("import sys, time\np = sys.stdin.read()\n"
             "if 'slow please' in p:\n    time.sleep(3)\n"
             "print('Answer.\\nO0: a\\nO1: b')\n")
# Crashes (non-zero exit, no output) for any prompt that mentions the repository row.
FAKE_CRASH = ("import sys\np = sys.stdin.read()\n"
              "if 'CardRepository' in p:\n    sys.exit(3)\n"
              "print('Answer.\\nO0: a\\nO1: b')\n")


class Harness:
    """Server harness with no test methods. Subclasses set the class attributes
    or override configure(); every test starts exactly one server."""
    fake_src = FAKE
    idle = ("--idle-minutes", "1")
    extra = ()
    screen = "missing"   # "missing": --screen-file points at a file that does not exist

    def git(self, *args):
        r = subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t",
                            "-c", "user.email=t@example.com", *args],
                           capture_output=True, text=True, check=True)
        return r.stdout.strip()

    def configure(self):
        """Hook run after the repo exists and before the server starts."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = pathlib.Path(self._tmp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q", "-b", "main")
        f = self.repo / CTRL
        f.parent.mkdir(parents=True)
        f.write_text("".join("line %d\n" % n for n in range(1, 41)))
        self.git("add", CTRL)
        self.git("commit", "-q", "-m", "base")
        self.git("checkout", "-q", "-b", "slice/cards")
        f.write_text("".join(("changed %d\n" if 20 <= n <= 24 else "line %d\n") % n
                             for n in range(1, 41)))
        self.git("add", CTRL)
        self.git("commit", "-q", "-m", "change")
        self.sha = self.git("rev-parse", "--short", "HEAD")
        self.review = self.repo / "REVIEW.md"
        self.review.write_text(TEXT.replace("a41c9e2", self.sha))
        self.discussion = self.root / "REVIEW-discussion.md"
        fake = self.root / "fake_agent.py"
        fake.write_text(self.fake_src)
        self.cmd = "%s %s" % (shlex.quote(sys.executable), shlex.quote(str(fake)))
        self.configure()
        self.start()

    def start(self):
        args = [sys.executable, str(SCRIPT), "--review", str(self.review),
                "--repo", str(self.repo), "--base", "main", "--slice", "cards",
                "--discussion", str(self.discussion), "--discuss-cmd", self.cmd,
                "--no-window", "--today", "2026-10-20", *self.idle, *self.extra]
        if self.screen == "missing":
            args += ["--screen-file", str(self.root / "missing.html")]
        self.proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     text=True)
        self.addCleanup(self.stop)
        self.lines = queue.Queue()

        def pump():
            try:
                for l in self.proc.stdout:
                    self.lines.put(l)
            except (ValueError, OSError):
                pass
        threading.Thread(target=pump, daemon=True).start()
        url = json.loads(self.lines.get(timeout=10))["url"]
        hostport, frag = url[len("http://"):].split("/#t=")
        self.host, self.port = hostport, int(hostport.split(":")[1])
        self.token = frag

    def stop(self):
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait(timeout=5)
        self.proc.stdout.close()

    def headers(self, token="default", host=None):
        h = {"Host": host or self.host}
        tok = self.token if token == "default" else token
        if tok is not None:
            h["X-Kerbe-Token"] = tok
        return h

    def request(self, method, path, body=None, token="default", host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = self.headers(token, host)
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            h["Content-Type"] = "application/json"
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        r.data = r.read()
        c.close()
        return r

    def get(self, path, token="default", host=None):
        return self.request("GET", path, token=token, host=host)

    def post(self, path, body, token="default", host=None):
        return self.request("POST", path, body, token=token, host=host)

    def json(self, method, path, body=None):
        r = self.request(method, path, body)
        self.assertEqual(r.status, 200, r.data)
        return json.loads(r.data)

    def ndjson(self, path, body):
        r = self.post(path, body)
        self.assertEqual(r.status, 200)
        return [json.loads(l) for l in r.data.decode().splitlines() if l.strip()]

    def wait_preread(self, rid, tries=50):
        for _ in range(tries):
            r = self.json("GET", "/api/preread?row=" + rid)
            if r["status"] != "pending":
                return r
            time.sleep(0.1)
        return r


class ServeTest(Harness, unittest.TestCase):
    def test_index_served_without_token(self):
        self.assertEqual(self.get("/", token=None).status, 200)

    def test_missing_token_403(self):
        self.assertEqual(self.get("/api/bundle", token=None).status, 403)

    def test_wrong_token_403(self):
        self.assertEqual(self.get("/api/bundle", token="nope").status, 403)

    def test_wrong_host_403(self):
        self.assertEqual(self.get("/api/bundle", host="evil.test").status, 403)

    def test_403_post_has_no_side_effect(self):
        before = self.review.read_text()
        r = self.post("/api/verdict", {"row": "B1", "kind": "verified", "mechanism": "m"},
                      token=None)
        self.assertEqual(r.status, 403)
        self.assertEqual(self.review.read_text(), before)

    def test_unknown_path_404(self):
        self.assertEqual(self.get("/etc/passwd", token=None).status, 404)

    def test_fallback_page_when_screen_missing(self):
        r = self.get("/", token=None)
        self.assertIn(b"Review screen file missing", r.data)

    def test_bundle(self):
        self.assertEqual([r["id"] for r in self.json("GET", "/api/bundle")["rows"]],
                         ["B1", "B2", "G1", "F1"])

    def test_bundle_rereads_status_after_all_decided(self):
        for rid in ("B1", "B2", "G1", "F1"):
            self.json("POST", "/api/verdict", {"row": rid, "kind": "verified", "mechanism": "m"})
        rows = self.json("GET", "/api/bundle")["rows"]
        self.assertTrue(all(r["status"] == "RESOLVED (VERIFIED)" for r in rows))

    def test_verdict_writes_row(self):
        r = self.json("POST", "/api/verdict", {"row": "B1", "kind": "fix", "option": "O1: b",
                                               "detail": "d", "proves": "p"})
        self.assertEqual(r["status"], "FIX QUEUED")
        self.assertIn("**FIX QUEUED", self.review.read_text())

    def test_verdict_rereads_file(self):
        self.review.write_text(self.review.read_text().replace(
            "ownership check", "ownership check (edited)"))
        self.json("POST", "/api/verdict", {"row": "B2", "kind": "verified", "mechanism": "m"})
        self.assertIn("(edited)", self.review.read_text())

    def test_verdict_leaves_no_temp_files(self):
        self.json("POST", "/api/verdict", {"row": "B1", "kind": "verified", "mechanism": "m"})
        self.assertEqual([p.name for p in self.repo.glob("REVIEW.md.*")], [])

    def test_verified_defaults_to_preread(self):
        self.wait_preread("B1")
        self.json("POST", "/api/verdict", {"row": "B1", "kind": "verified"})
        self.assertIn("Confirmed: Answer.", self.review.read_text())

    def test_bad_verdict_400_no_write(self):
        before = self.review.read_text()
        self.assertEqual(self.post("/api/verdict", {"row": "B9", "kind": "verified",
                                                    "mechanism": "m"}).status, 400)
        self.assertEqual(self.post("/api/verdict", {"row": "B1", "kind": "nonsense"}).status, 400)
        self.assertEqual(self.review.read_text(), before)

    def test_bad_json_400(self):
        self.assertEqual(self.post("/api/verdict", b"{not json").status, 400)

    def test_missing_field_400(self):
        self.assertEqual(self.post("/api/verdict", {"kind": "verified"}).status, 400)

    def test_oversize_body_413(self):
        before = self.review.read_text()
        r = self.post("/api/verdict", {"row": "B1", "kind": "defer", "reason": "x" * 70000})
        self.assertEqual(r.status, 413)
        self.assertEqual(self.review.read_text(), before)

    def test_negative_content_length_400(self):
        before = self.review.read_text()
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = self.headers()
        h["Content-Length"] = "-5"
        c.request("POST", "/api/verdict", headers=h)
        r = c.getresponse()
        self.assertEqual(r.status, 400)
        c.close()
        self.assertEqual(self.review.read_text(), before)

    def test_non_integer_content_length_400(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = self.headers()
        h["Content-Length"] = "abc"
        c.request("POST", "/api/verdict", headers=h)
        self.assertEqual(c.getresponse().status, 400)
        c.close()

    def test_preread_unknown_row_404(self):
        self.assertEqual(self.get("/api/preread?row=Z9").status, 404)

    def test_preread_ready(self):
        r = self.wait_preread("B2")
        self.assertEqual(r["status"], "ready")
        self.assertTrue(r["text"].startswith("Answer."))

    def test_ask_streams_answer_and_logs(self):
        lines = self.ndjson("/api/ask", {"row": "B1", "question": "what if the deck was deleted?"})
        ans = lines[-1]
        self.assertEqual(ans["type"], "answer")
        self.assertEqual(ans["options"], [["O0", "a"], ["O1", "b"]])
        self.assertIn("## QR-1/B1", self.discussion.read_text())

    def test_ask_unknown_row_400(self):
        self.assertEqual(self.post("/api/ask", {"row": "Z9", "question": "q"}).status, 400)

    def test_open_ignores_request_paths(self):
        r = self.json("POST", "/api/open", {"row": "B1", "file": "/etc/passwd",
                                            "cmd": "rm -rf /"})
        self.assertFalse(r["ok"])
        self.assertEqual(r["reason"], "no editor configured")

    def test_finish_exits_with_counts(self):
        self.json("POST", "/api/verdict", {"row": "B1", "kind": "verified", "mechanism": "m"})
        self.json("POST", "/api/finish", {})
        out = json.loads(self.lines.get(timeout=10))
        self.assertEqual(out["counts"]["verified"], 1)
        self.assertTrue(out["finished"])
        self.assertEqual(out["reason"], "finish")
        self.assertEqual(self.proc.wait(timeout=5), 0)

    def test_finish_challenge_reason(self):
        self.json("POST", "/api/finish", {"challenge": True})
        out = json.loads(self.lines.get(timeout=10))
        self.assertTrue(out["finished"])
        self.assertEqual(out["reason"], "challenge")
        self.assertEqual(self.proc.wait(timeout=5), 0)

    def test_port_closed_after_finish(self):
        self.json("POST", "/api/finish", {})
        self.proc.wait(timeout=10)
        with self.assertRaises(OSError):
            http.client.HTTPConnection("127.0.0.1", self.port, timeout=2).request("GET", "/")


class ServeOpenTest(Harness, unittest.TestCase):
    """Editor template present but unsafe: refused with a reason, nothing run."""
    extra = ("--editor-template", "sh -c {file}:{line}")

    def test_open_unsafe_template_refused(self):
        r = self.json("POST", "/api/open", {"row": "B1"})
        self.assertFalse(r["ok"])
        self.assertNotEqual(r["reason"], "no editor configured")


class ServeOpenOutsideTest(Harness, unittest.TestCase):
    """A row whose file resolves outside the repo is refused before any launch."""
    extra = ("--editor-template", "sh -c {file}:{line}")

    def configure(self):
        (self.root / "outside.php").write_text("<?php\n")
        text = self.review.read_text()
        old = "| B2 | `src/Repository/CardRepository.php` ·"
        self.assertIn(old, text)
        self.review.write_text(text.replace(old, "| B2 | `src/../../outside.php` ·"))

    def test_open_outside_repo_refused(self):
        r = self.json("POST", "/api/open", {"row": "B2"})
        self.assertFalse(r["ok"])
        self.assertIn("outside the repository", r["reason"])


class ServeScreenTest(Harness, unittest.TestCase):
    screen = "file"

    def configure(self):
        page = self.root / "index.html"
        page.write_text("<p>hello screen</p>")
        self.extra = ("--screen-file", str(page))

    def test_serves_screen_file(self):
        self.assertIn(b"hello screen", self.get("/", token=None).data)


class ServeSlowAskTest(Harness, unittest.TestCase):
    fake_src = FAKE_SLOW

    def test_ask_sends_status_before_answer_and_closes(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        h = self.headers()
        h["Content-Type"] = "application/json"
        c.request("POST", "/api/ask", headers=h,
                  body=json.dumps({"row": "B1", "question": "slow please"}).encode())
        r = c.getresponse()
        self.assertEqual(r.status, 200)
        self.assertEqual(r.getheader("Connection"), "close")
        lines = [json.loads(l) for l in r.read().decode().splitlines() if l.strip()]
        c.close()
        self.assertGreaterEqual(len([m for m in lines if m["type"] == "status"]), 1)
        self.assertEqual(lines[-1]["type"], "answer")
        self.assertEqual(lines[0]["type"], "status")

    def test_client_disconnect_mid_ask_leaves_server_working(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=15)
        h = self.headers()
        h["Content-Type"] = "application/json"
        c.request("POST", "/api/ask", headers=h,
                  body=json.dumps({"row": "B1", "question": "slow please"}).encode())
        r = c.getresponse()
        first = json.loads(r.fp.readline())
        self.assertEqual(first["type"], "status")
        c.close()
        time.sleep(1.5)   # let the server hit the closed socket
        self.assertEqual(self.get("/api/bundle").status, 200)


class ServePrereadCrashTest(Harness, unittest.TestCase):
    """The agent command dies for the B2 row only; the other rows keep working."""
    fake_src = FAKE_CRASH

    def test_failed_preread_does_not_stop_the_worker(self):
        self.assertEqual(self.wait_preread("B2")["status"], "error")
        self.assertEqual(self.wait_preread("B1")["status"], "ready")
        self.assertEqual(self.wait_preread("F1")["status"], "ready")
        self.json("POST", "/api/verdict", {"row": "B1", "kind": "verified"})
        self.assertIn("Confirmed: Answer.", self.review.read_text())


class ServeCrlfTest(Harness, unittest.TestCase):
    """A CRLF REVIEW.md keeps CRLF on every line after a screen verdict."""

    def configure(self):
        text = self.review.read_text()
        self.review.write_bytes(text.replace("\n", "\r\n").encode("utf-8"))

    def test_verdict_preserves_crlf(self):
        self.json("POST", "/api/verdict", {"row": "B1", "kind": "verified", "mechanism": "m"})
        data = self.review.read_bytes()
        self.assertIn(b"RESOLVED (VERIFIED)", data)
        self.assertEqual(data.count(b"\r\n"), data.count(b"\n"))


class ServeSymlinkTest(Harness, unittest.TestCase):
    """A symlinked REVIEW.md is written through and keeps its link."""

    def configure(self):
        real = self.root / "planning-REVIEW.md"
        real.write_text(self.review.read_text())
        self.review.unlink()
        self.review.symlink_to(real)
        self.real = real

    def test_verdict_keeps_symlink(self):
        self.json("POST", "/api/verdict", {"row": "B1", "kind": "verified", "mechanism": "m"})
        self.assertTrue(self.review.is_symlink())
        self.assertIn("RESOLVED (VERIFIED)", self.real.read_text())


class ServeLongPrereadTest(Harness, unittest.TestCase):
    """A long pre-read is capped when it becomes a Verified mechanism."""
    fake_src = "import sys\nsys.stdin.read()\nprint('word ' * 400)\n"

    def test_verified_mechanism_capped(self):
        self.assertEqual(self.wait_preread("B1")["status"], "ready")
        self.json("POST", "/api/verdict", {"row": "B1", "kind": "verified"})
        line = next(l for l in self.review.read_text().splitlines() if "| B1 |" in l)
        self.assertIn("…", line)
        self.assertLess(line.count("word"), 130)


class ScreenFileTest(unittest.TestCase):
    """Static checks on the screen file; no server needed."""

    def test_index_has_no_external_urls(self):
        html = (REPO / "skills/rwalk/screen/index.html").read_text()
        self.assertNotRegex(html, r"https?://(?!127\.0\.0\.1)")

    def test_index_reads_token_from_fragment(self):
        html = (REPO / "skills/rwalk/screen/index.html").read_text()
        self.assertIn("location.hash", html); self.assertIn("X-Kerbe-Token", html)
        self.assertNotIn("localStorage", html)


def load_serve():
    spec = importlib.util.spec_from_file_location("rwalk_serve", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ServeStartupErrorTest(Harness, unittest.TestCase):
    """Startup failures exit 2 with an error line and no URL, so the skill falls back."""

    def start(self):
        self.args = ["--review", str(self.review), "--repo", str(self.repo), "--base", "main",
                     "--slice", "cards", "--discussion", str(self.discussion),
                     "--discuss-cmd", self.cmd, "--no-window"]

    def test_refuses_inside_codex_sandbox(self):
        r = subprocess.run([sys.executable, str(SCRIPT), *self.args], capture_output=True,
                           text=True, timeout=10, env={**os.environ, "CODEX_SANDBOX": "seatbelt"})
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, "")
        self.assertRegex(r.stderr, r"^error: .*sandbox")

    def test_bind_failure_is_an_error_line(self):
        serve = load_serve()

        def refuse(*a, **k):
            raise PermissionError(1, "Operation not permitted")
        err = io.StringIO()
        with mock.patch.object(serve, "ThreadingHTTPServer", side_effect=refuse), \
                mock.patch.dict(os.environ, {}, clear=False), \
                contextlib.redirect_stderr(err):
            os.environ.pop("CODEX_SANDBOX", None)
            self.assertEqual(serve.main(self.args), 2)
        self.assertRegex(err.getvalue(), r"^error: cannot listen on 127\.0\.0\.1: .*not permitted")


class ServeIdleTest(Harness, unittest.TestCase):
    idle = ("--idle-seconds", "2")

    def test_idle_exit(self):
        out = json.loads(self.lines.get(timeout=10))
        self.assertEqual(out["reason"], "idle")
        self.assertFalse(out["finished"])
        self.assertEqual(self.proc.wait(timeout=5), 0)


if __name__ == "__main__":
    unittest.main()
