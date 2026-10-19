import http.client
import json
import pathlib
import queue
import shlex
import subprocess
import sys
import tempfile
import threading
import unittest

from tests.test_rwalk_qr import TEXT

REPO = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO / "skills" / "rwalk" / "scripts" / "serve.py"
CTRL = "src/Controller/CardController.php"
FAKE = "import sys\nsys.stdin.read()\nprint('Answer.\\nO0: a\\nO1: b')\n"


class ServeTest(unittest.TestCase):
    extra = ()
    idle = ("--idle-minutes", "1")

    def git(self, *args):
        r = subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=t",
                            "-c", "user.email=t@example.com", *args],
                           capture_output=True, text=True, check=True)
        return r.stdout.strip()

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = pathlib.Path(self._tmp.name)
        self.repo = root / "repo"
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
        sha = self.git("rev-parse", "--short", "HEAD")
        self.review = self.repo / "REVIEW.md"
        self.review.write_text(TEXT.replace("a41c9e2", sha))
        self.discussion = root / "REVIEW-discussion.md"
        fake = root / "fake_agent.py"
        fake.write_text(FAKE)
        self.cmd = "%s %s" % (shlex.quote(sys.executable), shlex.quote(str(fake)))
        self.start()

    def start(self, *extra):
        args = [sys.executable, str(SCRIPT), "--review", str(self.review),
                "--repo", str(self.repo), "--base", "main", "--slice", "cards",
                "--discussion", str(self.discussion), "--discuss-cmd", self.cmd,
                "--no-window", "--today", "2026-10-20",
                *(self.idle), *self.extra, *extra]
        self.proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                     text=True)
        self.addCleanup(self.stop)
        self.lines = queue.Queue()
        threading.Thread(target=lambda: [self.lines.put(l) for l in self.proc.stdout],
                         daemon=True).start()
        url = json.loads(self.lines.get(timeout=10))["url"]
        hostport, frag = url[len("http://"):].split("/#t=")
        self.host, self.port = hostport, int(hostport.split(":")[1])
        self.token = frag

    def stop(self):
        if self.proc.poll() is None:
            self.proc.kill()
        self.proc.wait(timeout=5)
        self.proc.stdout.close()

    def request(self, method, path, body=None, token="default", host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        h = {"Host": host or self.host}
        tok = self.token if token == "default" else token
        if tok is not None:
            h["X-Kerbe-Token"] = tok
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

    def test_verified_defaults_to_preread(self):
        import time
        for _ in range(50):
            if self.json("GET", "/api/preread?row=B1")["status"] == "ready":
                break
            time.sleep(0.1)
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

    def test_preread_unknown_row_404(self):
        self.assertEqual(self.get("/api/preread?row=Z9").status, 404)

    def test_preread_ready(self):
        import time
        for _ in range(50):
            r = self.json("GET", "/api/preread?row=B2")
            if r["status"] != "pending":
                break
            time.sleep(0.1)
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

    def test_finish_exits_with_counts(self):
        self.json("POST", "/api/verdict", {"row": "B1", "kind": "verified", "mechanism": "m"})
        self.json("POST", "/api/finish", {})
        out = json.loads(self.lines.get(timeout=10))
        self.assertEqual(out["counts"]["verified"], 1)
        self.assertTrue(out["finished"])
        self.assertEqual(out["reason"], "finish")
        self.assertEqual(self.proc.wait(timeout=5), 0)

    def test_port_closed_after_finish(self):
        self.json("POST", "/api/finish", {})
        self.proc.wait(timeout=10)
        with self.assertRaises(OSError):
            http.client.HTTPConnection("127.0.0.1", self.port, timeout=2).request("GET", "/")


class ServeOpenTest(ServeTest):
    """Editor template present but unsafe: refused with a reason, nothing run."""
    extra = ("--editor-template", "sh -c {file}:{line}")

    def test_open_unsafe_template_refused(self):
        r = self.json("POST", "/api/open", {"row": "B1"})
        self.assertFalse(r["ok"])
        self.assertNotEqual(r["reason"], "no editor configured")


class ServeScreenTest(ServeTest):
    def test_serves_screen_file(self):
        page = pathlib.Path(self._tmp.name) / "index.html"
        page.write_text("<p>hello screen</p>")
        self.stop()
        self.start("--screen-file", str(page))
        self.assertIn(b"hello screen", self.get("/", token=None).data)


class ServeIdleTest(unittest.TestCase):
    def test_idle_exit(self):
        t = ServeTest("test_bundle")
        t.idle = ("--idle-seconds", "2")
        t.setUp()
        try:
            out = json.loads(t.lines.get(timeout=10))
            self.assertEqual(out["reason"], "idle")
            self.assertFalse(out["finished"])
            self.assertEqual(t.proc.wait(timeout=5), 0)
        finally:
            t.doCleanups()


if __name__ == "__main__":
    unittest.main()
