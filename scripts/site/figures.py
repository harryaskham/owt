"""Figures and generated regions for the owt site, from data captured by running the server."""
import html
import json
from pathlib import Path

from diagrams import graph

DATA = Path(__file__).resolve().parent / "data"
METRICS = {"sans": 1.0, "mono": 0.6}


def load(name):
    return json.loads((DATA / name).read_text())


def request():
    return graph(
        "request", "What happens to a request",
        "How owt handles a request. Any path is accepted, by GET with query parameters or by POST with a JSON body, "
        "behind optional basic authentication. The body carries code and keyword arguments, both base64-encoded. The "
        "server tries the code three ways until one defines run: as written; as an expression assigned to run; and as a "
        "chain of calls appended to pipe(). It executes the code with the server module's own globals, calls run with the "
        "decoded arguments, and turns the result into the HTTP response.",
        940, 300,
        nodes=[
            dict(id="client", x=90, y=80, label="any client", sub="curl, Python, Haskell", kind="muted", w=170),
            dict(id="route", x=310, y=80, label="/any/path", sub="GET or POST · basic auth", kind="ink", w=200, mono=True),
            dict(id="decode", x=550, y=80, label="decode", sub="code_b64 · kwargs_b64", kind="b", w=190),
            dict(id="modes", x=550, y=220, label="find run", sub=["as written · as an expression", "· appended to pipe()"], kind="accent", w=230),
            dict(id="exec", x=310, y=220, label="exec", sub="with the server's globals", kind="err", w=200),
            dict(id="resp", x=90, y=220, label="response", sub="run(**kwargs)", kind="ok", w=170),
        ],
        edges=[
            {"from": "client", "to": "route", "kind": "ink"},
            {"from": "route", "to": "decode", "kind": "ink"},
            {"from": "decode", "to": "modes", "kind": "ink", "out": "b", "in": "t"},
            {"from": "modes", "to": "exec", "kind": "accent"},
            {"from": "exec", "to": "resp", "kind": "ok"},
        ],
    )


FIGS = {"request": request}


def _row(r, show_code=True):
    code = html.escape(r["code"])
    kw = html.escape(json.dumps(r["kwargs"])) if r["kwargs"] else ""
    extra = html.escape(json.dumps(r["extra"])) if r["extra"] else ""
    args = " ".join(x for x in (kw, extra) if x)
    cls = "ok" if r["status"] == 200 else "bad"
    return (f'<tr class="{cls}"><td>{html.escape(r["what"])}</td><td><pre class="cell"><code>{code}</code></pre></td>'
            f'<td><code>{args}</code></td><td class="st">{r["status"]}</td><td><code>{html.escape(r["response"])}</code></td></tr>')


def table(ids, caption):
    rs = {r["id"]: r for r in load("requests.json")}
    return lambda: (f'<table class="req"><caption>{caption}</caption><thead><tr><th scope="col">Shows</th>'
                    '<th scope="col">Code sent</th><th scope="col">Arguments</th><th scope="col">Status</th>'
                    '<th scope="col">Response</th></tr></thead><tbody>' + "".join(_row(rs[i]) for i in ids) + "</tbody></table>")


GEN = {
    "modes": table(["explicit", "implicit", "terse"], "The three ways code can define run, as sent to a local server"),
    "edges": table(["state-1", "state-2", "import-top", "error", "cache-1", "cache-2"], "Sharp edges, as sent to a local server"),
    "auth": table(["auth-none", "auth-ok"], "With --auth"),
    "tests": lambda: f'<p class="note">The test suite: {html.escape(load("tests.json")["summary"])}.</p>',
}
