import base64
import unittest.mock
from typing import Any, Callable
from owt.summat.io import Install
from owt import pipe
from owt.summat.syntax import Owt
import pytest
import json
import logging
from flask.testing import FlaskClient
from owt.server import app, Server


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(autouse=True, scope="module")
def init_server():
    app.config["TESTING"] = True
    Server.serve(address="127.0.0.1", port=9876, auth=None)


def assert_owt_exec(
    client: FlaskClient,
    expected: str,
    args: Any = None,
    extra_params: dict | None = None,
    method: str = "GET",
    path: str = "/test",
    code: str = "",
):
    if not args:
        args = {}
    if not extra_params:
        extra_params = {}

    code_b64 = base64.b64encode(code.encode()).decode()
    kwargs_b64 = base64.b64encode(json.dumps(args).encode()).decode()
    params = {
        "code_b64": code_b64,
        "kwargs_b64": kwargs_b64,
        **extra_params,
    }

    if method == "GET":
        response = client.get(
            path,
            query_string=params,
        )
    elif method == "POST":
        response = client.post(
            path,
            data=json.dumps(params),
            headers={"Content-Type": "application/json"},
        )
    else:
        raise ValueError(f"Unsupported method: {method}")

    logging.info(response.data)

    assert response.status_code == 200
    assert response.data.decode() == expected


def test_hello_world(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="Hello World!",
        args={"name": "World"},
        code="""
def run(name):
    return f"Hello {name}!"
""",
    )


def test_hello_world_from_path(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="Hello World!",
        code="""run = pipe().path().f(lambda names: f"Hello {names[0]}!").done()""",
        path="/World",
    )


def test_hello_world_from_multipath(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="Hello one|two|three!",
        code="""run = pipe().path().f(lambda p: f"Hello {'|'.join(p)}!").done()""",
        path="/one/two/three",
    )


def test_hello_world_path_last(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="Hello three!",
        code="""run = pipe().path().last().f(lambda p: f"Hello {p}!").done()""",
        path="/one/two/three",
    )


def test_const_string(client: FlaskClient):
    assert_owt_exec(client, expected="abc", code="""run = pipe().const("abc").done()""")


def test_const_int(client: FlaskClient):
    assert_owt_exec(client, expected="123", code="""run = pipe().const(123).done()""")


def test_const_object(client: FlaskClient):
    assert_owt_exec(
        client,
        expected='{"x": 123, "y": "abc"}',
        code="""
class Obj(dict):
    def __init__(self, x: int, y: str):
        self["x"] = x
        self["y"] = y

run = pipe().const(Obj(123, "abc")).done()
""",
    )


def test_f_implicit_last(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="6",
        args=5,
        code="""
run = pipe().f(lambda x: str(x + 1)).done()
""",
    )


def test_f_path(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="6",
        path="/some/path/5",
        code="""
run = pipe().path().last().cast(int).f(lambda x: int(x) + 1).done()
""",
    )


def test_identity(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="test",
        args={"__last__": "test"},
        code="""
run = pipe().identity().done()
""",
    )


def test_const(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="constant",
        code="""
run = pipe().const("constant").done()
""",
    )


def test_map_foldl1_path(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="emoshtap",
        path="/some/path",
        code="""
run = pipe().path().map(lambda x: x[::-1]).foldl1(lambda x, y: x + y).done()
""",
    )


def test_foldl(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="15",
        args=[1, 2, 3, 4, 5],
        code="""
run = pipe().foldl(lambda acc, x: acc + x, 0).f(str).done()
""",
    )


def test_ix(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="b",
        args=["a", "b", "c"],
        code="""
run = pipe().ix(1).done()
""",
    )


def test_clear_removes_kwargs(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="no kwargs",
        args={"x": 1, "y": 2},
        code="""
run = pipe().clear().f(lambda _: "no kwargs").done()
""",
    )


def test_kwargs_unused_args(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="unused args",
        code="""
run = pipe().kwargs(x=1, y=2).f(lambda **_: "unused args").done()
""",
    )


def test_kwargs_with_bound_args(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="6",
        args={"x": 0, "z": 4},
        code="""
run = pipe().kwargs(x=1, y=2).f(lambda x=None, y=None, z=1: x + y + z).done()
""",
    )


def test_importing(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="path",
        path="/some/path",
        code="""
run = (
    pipe()
    .importing("json")
    .path()
    .f(lambda p: json.dumps(p))
    .f(lambda x: json.loads(x))
    .last()
    .done()
)
""",
    )


@unittest.mock.patch.object(Install, "pip_install")
def test_pip_install(mock_pip_install, client: FlaskClient):
    mock_pip_install.return_value = None

    assert_owt_exec(
        client,
        expected="123",
        code="""
run = pipe().installing("pytest").const(123).done()
    """,
    )
    mock_pip_install.assert_called_once_with("pytest")


def test_query_source(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="123",
        path="/test",
        extra_params={"extra": "123"},
        code="""
run = pipe().const("no").query().get("extra").done()
    """,
    )


def test_data_source(client: FlaskClient):
    assert_owt_exec(
        client,
        expected="test data",
        method="POST",
        extra_params={"extra": "test data"},
        code="""
run = pipe().json().get("extra").done()
        """,
    )


def test_cond(client: FlaskClient):
    code = """
run = (pipe()
       .path()
       .last()
       .cast(int)
       .f(lambda x: x > 10)
       .cond(pipe().const("true"), pipe().const("false"))
       .done())
"""

    assert_owt_exec(client, path="/15", expected="true", code=code)
    assert_owt_exec(client, path="/5", expected="false", code=code)


def test_fork(client: FlaskClient):
    code = """
run = (
    pipe()
    .path()
    .last()
    .fork(pipe().f(len),
          pipe().const("right"))
    .cast(str)
   .done())
"""

    assert_owt_exec(client, path="/test", expected="(4, 'right')", code=code)


def test_raw_pipe() -> None:
    p: Owt[Any, int] = pipe().const(1).f(lambda x: x + 1)
    assert p() == (2, {"__last__": 2})
    run: Callable[[Any], int] = p.done()
    assert run(None) == 2
