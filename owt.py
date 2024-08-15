from typing import Callable, Any, reveal_type
import base64
import logging
import os
from http import server
import json
from dataclasses import dataclass
import dataclasses
from multiprocessing.connection import Client
from flask import (
    Flask,
    request,
    Response,
    jsonify,
    send_file,
    send_from_directory,
    render_template,
    url_for,
    current_app,
)
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth
import requests
from multiprocessing import Process
import bark
import argparse
from logging.config import dictConfig

dictConfig(
    {
        "version": 1,
        "formatters": {
            "default": {
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "default",
            }
        },
        "root": {"level": "DEBUG", "handlers": ["console"]},
    }
)

parser = argparse.ArgumentParser(
    description="Owt - Lightweight endpoints for serving owt yer like"
)
parser.add_argument(
    "--address",
    default=os.environ.get("OWT_ADDRESS", "127.0.0.1"),
    help="Address to serve from ('0.0.0.0' to accept all connections)",
)
parser.add_argument(
    "--port", default=os.environ.get("OWT_PORT", 9876), help="Port to serve from"
)
parser.add_argument("--enable-auth", action=argparse.BooleanOptionalAction)
parser.add_argument(
    "--auth",
    default=os.environ.get("OWT_BASIC_AUTH", "owt:owt"),
    help="Basic auth username:password",
)

try:
    args = parser.parse_args()
except argparse.ArgumentError as e:
    logging.error(f"Error parsing arguments: {e}")
    exit(1)


app = Flask(
    __name__, static_url_path="", static_folder="static", template_folder="example"
)
app.config["TEMPLATES_AUTO_RELOAD"] = True
auth = HTTPBasicAuth()
AUTH_USERNAME, AUTH_PASSWORD = args.auth.split(":")
CORS(app)


@auth.verify_password
def verify(username, password):
    if not args.enable_auth:
        return True

    if not (username and password):
        return False
    return AUTH_DATA.get(username) == password


@dataclass(frozen=True)
class Server:
    address: str
    port: int

    def serve(self):
        print(f"Owt started on {self.address}:{self.port}")
        app.run(port=self.port, host=self.address)


@dataclass(frozen=True, kw_only=True)
class Unsafe:
    # Code to run, defining a Callable[[...], Response] with a function of the expected name.
    code_b64: str

    # The function to run in the given code
    fn_name: str = "run"

    # Kwargs to pass to the run function
    kwargs_b64: str = None

    @property
    def code(self) -> str:
        return base64.b64decode(self.code_b64).decode("utf-8")

    @property
    def kwargs(self) -> dict[str, Any]:
        if not self.kwargs_b64:
            return {}
        try:
            raw_kwargs = base64.b64decode(self.kwargs_b64).decode("utf-8")
            logging.info("Raw kwargs: %s", raw_kwargs)
            decoded_kwargs = eval(raw_kwargs)
            logging.info("Decoded kwargs: %s", decoded_kwargs)
            return decoded_kwargs
        except Exception as e:
            raise ValueError(f"Failed to decode kwargs: {e}")

    def to_json(self) -> str:
        return json.dumps(self.__dict__)

    @classmethod
    def from_json(cls, json_str: str) -> "Unsafe":
        try:
            json_dict = json.loads(json_str)
            logging.info("Got Unsafe JSON: %s", json_dict)
            unsafe = cls(**json_dict)
            logging.info(f"Unsafe parsed from JSON POST data: {unsafe.code}")
            return unsafe
        except Exception as e:
            raise ValueError(f"Failed to parse Unsafe from JSON: {e}")

    @classmethod
    def from_request(cls) -> "Unsafe":
        try:
            unsafe = cls.from_json(request.data)
            logging.info(f"Unsafe parsed from JSON POST data: {unsafe.code}")
            return unsafe
        except Exception as e:
            logging.error(
                f"Failed to parse Unsafe from JSON POST data, trying GET params: {e}"
            )

        try:
            return cls(**request.args.to_dict())
        except Exception as e:
            logging.error(f"Failed to parse Unsafe from POST or GET data: {e}")
            logging.debug(f"POST data: {request.data}")
            logging.debug(f"POST JSON: {request.json}")
            logging.debug(f"GET params: {request.args.to_dict()}")
            raise e

    def lines(self, indent: int = 0) -> list[str]:
        return [" " * indent + line for line in self.code.split("\n")]

    def code_indented(self, indent: int) -> str:
        return "\n".join(self.lines(indent=indent))

    def unsafe_exec_fn(self) -> Callable[[], Response]:
        _globals = globals()
        _locals = locals()
        logging.info("Running code: %s", self.code)
        try:
            exec(self.code, _globals, _locals)
        except Exception as e:
            raise RuntimeError(
                f"Error compiling Unsafe code: {e}\n\n{self.code_indented(4)}"
            )
        run_fn = _locals.get(self.fn_name) or _globals.get(self.fn_name)
        if not run_fn:
            raise ValueError(f"No '{self.fn_name}' method defined in code")
        return run_fn

    def unsafe_exec(self) -> Any:
        try:
            reveal_type(self.kwargs)
            logging.info("Running with kwargs: %s", self.kwargs)
            return self.unsafe_exec_fn()(**self.kwargs)
        except Exception as e:
            raise RuntimeError(f"Error executing Unsafe code: {e}")


@app.route("/unsafe/exec/<string:anything>", methods=["GET", "POST"])
@auth.login_required
def unsafe_exec(anything: str):
    try:
        unsafe = Unsafe.from_request()
    except Exception as e:
        return f"Invalid Unsafe data in request: {e}", 400

    try:
        return unsafe.unsafe_exec()
    except Exception as e:
        return f"Error executing Unsafe code: {e}", 500


@app.route("/bark", methods=["GET"])
@auth.login_required
def bark():
    return render_template("bark.html")


if __name__ == "__main__":
    Server(args.address, args.port).serve()
