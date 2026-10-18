#!/usr/bin/env python3
"""Record real owt requests and responses for the site.

    python3 scripts/site/capture.py PYTHON

PYTHON must have flask, flask-cors, flask-httpauth and requests. Starts `owt.server` on
127.0.0.1 at a free port (never on all interfaces) in a scratch HOME, makes each request in
REQUESTS, and records what came back. A second server with --auth shows the 401 a request gets
without credentials. Also runs tests/test_owt.py. Writes scripts/site/data/{requests.json, tests.json}.
"""
import base64
import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

# (id, what it shows, code, kwargs, extra request fields)
REQUESTS = [
    ("explicit", "code that defines run", 'def run(name):\n    return f"hello, {name}"', {"name": "owt"}, {}),
    ("implicit", "an expression becomes run", "lambda word: word[::-1]", {"word": "stressed"}, {}),
    ("terse", "a chain of calls is appended to pipe()", "kwarg('text').f(str.upper)", {"text": "quiet please"}, {}),
    ("error", "an exception is a 500", 'def run():\n    raise ValueError("nope")', {}, {}),
    ("state-1", "server globals persist between requests",
     "def run():\n    global hits\n    hits = globals().get('hits', 0) + 1\n    return str(hits)", {}, {}),
    ("state-2", "the same request again", "def run():\n    global hits\n    hits = globals().get('hits', 0) + 1\n    return str(hits)", {}, {}),
    ("import-top", "a module-level import is not visible inside run",
     "import time\ndef run():\n    return str(time.time_ns())", {}, {}),
    ("cache-1", "cached by path", "def run():\n    import time\n    return str(time.time_ns())", {}, {"use_cache": True}),
    ("cache-2", "the same path again: the cached answer", "def run():\n    import time\n    return str(time.time_ns())", {}, {"use_cache": True}),
]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def post(url, body, auth=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    if auth:
        req.add_header("Authorization", "Basic " + base64.b64encode(auth.encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def serve(python, env, *args):
    port = free_port()
    p = subprocess.Popen([python, "-m", "owt.server", "--address", "127.0.0.1", "--port", str(port), *args],
                         cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    return p, f"http://127.0.0.1:{port}"


def body(code, kwargs, extra):
    return {"code_b64": base64.b64encode(code.encode()).decode(),
            "kwargs_b64": base64.b64encode(repr(kwargs).encode()).decode(), **extra}


def main():
    python = sys.argv[1]
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        env = {"PATH": os.path.dirname(python) + ":/usr/bin:/bin", "HOME": tmp, "PYTHONPATH": str(ROOT)}
        server, base = serve(python, env)
        try:
            for key, what, code, kwargs, extra in REQUESTS:
                status, text = post(f"{base}/demo/{key.rsplit('-', 1)[0] if key[-1].isdigit() else key}", body(code, kwargs, extra))
                out.append({"id": key, "what": what, "code": code, "kwargs": kwargs, "extra": extra,
                            "status": status, "response": text})
        finally:
            server.terminate()
            server.wait()
        digest = hashlib.sha256(b"example-password").hexdigest()
        server, base = serve(python, env, "--auth", f"owt:{digest}")
        try:
            status, text = post(f"{base}/demo", body("lambda: 'hi'", {}, {}))
            out.append({"id": "auth-none", "what": "no credentials", "code": "lambda: 'hi'", "kwargs": {}, "extra": {},
                        "status": status, "response": text})
            status, text = post(f"{base}/demo", body("lambda: 'hi'", {}, {}), auth="owt:example-password")
            out.append({"id": "auth-ok", "what": "with credentials", "code": "lambda: 'hi'", "kwargs": {}, "extra": {},
                        "status": status, "response": text})
        finally:
            server.terminate()
            server.wait()
    with tempfile.TemporaryDirectory() as tmp:
        env = {"PATH": os.path.dirname(python) + ":/usr/bin:/bin", "HOME": tmp}
        r = subprocess.run([python, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_owt.py"], cwd=ROOT,
                           env=env, capture_output=True, text=True)
        summary = [l for l in r.stdout.splitlines() if " passed" in l or " failed" in l][-1:]
    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "data" / "requests.json").write_text(json.dumps(out, indent=1) + "\n")
    (HERE / "data" / "tests.json").write_text(json.dumps({"summary": summary[0] if summary else r.stdout[-200:]}) + "\n")
    for r in out:
        print(r["id"], r["status"], r["response"][:100].replace("\n", " "))


if __name__ == "__main__":
    main()
