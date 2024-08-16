from typing import Callable, Any, reveal_type
import hashlib
import urllib
import asyncio
from collections import defaultdict
import base64
import logging
import os
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
    default=os.environ.get("OWT_ADDRESS", "0.0.0.0"),
    help="Address to serve from ('0.0.0.0' to accept all connections)",
)
parser.add_argument(
    "--port", default=os.environ.get("OWT_PORT", 9876), help="Port to serve from"
)
parser.add_argument("--auth-enabled", action=argparse.BooleanOptionalAction)
parser.add_argument(
    "--auth",
    default=os.environ.get(
        "OWT_BASIC_AUTH",
        "owt:cbdde0ca6618426b57782672d5d1f74525379f6d06812db55d4e1e918e88d54",
    ),
    help="Basic auth username:password_sha256 (default: owt:sha256(owt))",
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
CORS(app)


@dataclass(frozen=True)
class PlaintextPassword:
    password: str

    def sha256(self) -> str:
        return hashlib.sha256(self.password.encode("utf-8")).hexdigest()


@dataclass(frozen=True, kw_only=True)
class BasicAuth:
    enabled: bool
    usernameToSHA256: dict[str, str] = dataclasses.field(default_factory=dict)

    def add(self, username: str, password_sha256: str):
        self.usernameToSHA256[username] = password_sha256

    def authenticate(self, username: str, password: PlaintextPassword) -> bool:
        if username not in self.usernameToSHA256:
            logging.warning("User not known to auth: %s", username)
            return False
        logging.info("Checking sha256 for %s", username)
        return self.usernameToSHA256.get(username) == password.sha256()


@dataclass(frozen=True, kw_only=True)
class Server:
    address: str
    port: int
    cache: dict["CacheKey", Any] = dataclasses.field(default_factory=dict)
    auth: BasicAuth

    @classmethod
    def serve(cls, **kwargs):
        global _SERVER
        _SERVER = cls(**kwargs)
        print(f"Owt starting on {_SERVER.address}:{_SERVER.port}")
        app.run(port=_SERVER.port, host=_SERVER.address)

    @classmethod
    def sing(cls) -> "Server":
        global _SERVER
        if not _SERVER:
            raise RuntimeError("Server not started")
        return _SERVER


_SERVER: Server = None


@auth.verify_password
def verify(username, password):
    server = Server.sing()
    if not server.auth.enabled:
        return True

    return server.auth.authenticate(username, PlaintextPassword(password))


@dataclass(frozen=True, kw_only=True)
class CacheKey:
    path: str
    kwargs_b64: str | None = None

    def __repr__(self):
        if self.kwargs_b64:
            return f"CacheKey({self.path}, {self.kwargs})"
        else:
            return f"CacheKey({self.path})"

    def __hash__(self):
        return hash((self.path, self.kwargs_b64))


@dataclass(frozen=True, kw_only=True)
class Unsafe:
    # Code to run, defining a Callable[[...], Response] with a function of the expected name.
    code_b64: str

    # The function to run in the given code.
    # If not provided, defaults to "run". Must take request as its first argument; the remaining are any kwargs provided.
    fn_name: str = "run"

    # Kwargs to pass to the run function
    kwargs_b64: str = None

    # If true, results will be cached according to the name of the endpoint provided
    use_cache: bool = False

    # If true, cache key will include kwargs so that the same endpoint can simulate per-arg determinism
    cache_kwargs: bool = False

    # If provided, the cache key will be overridden with this value
    cache_key_override: CacheKey | None = None

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
            logging.info(
                "Unsafe parsed from JSON POST data: \n\n%s", unsafe.code_indented(4)
            )
            return unsafe
        except Exception as e:
            logging.error(e)
            logging.debug(f"POST data: {request.data}")
            logging.error(
                "Failed to parse Unsafe from JSON POST data, trying GET params"
            )

        try:
            logging.debug("GET params: %s", request.args.to_dict())
            params = {}
            for key, value in request.args.to_dict().items():
                params[key] = value
            logging.debug("Decoded code:")
            logging.debug(base64.b64decode(params["code_b64"]))
            unsafe = Unsafe(**params)
            logging.info(
                "Unsafe parsed from GET params: \n\n%s", unsafe.code_indented(4)
            )
            return unsafe
        except Exception as e:
            logging.error(e)
            logging.error("Failed to parse Unsafe from GET data")
            raise e

    def lines(self, indent: int = 0) -> list[str]:
        return [" " * indent + line for line in self.code.split("\n")]

    def code_indented(self, indent: int) -> str:
        return "\n".join(self.lines(indent=indent))

    def unsafe_exec_fn(self) -> Callable[[], Response]:
        _globals = globals()
        _locals = locals()
        logging.info("Running code:\n\n%s", self.code_indented(4))
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

    def unsafe_exec(self, request) -> Any:
        try:
            logging.info("Running with kwargs: %s", self.kwargs)
            return self.unsafe_exec_fn()(request, **self.kwargs)
        except Exception as e:
            raise RuntimeError(f"Error executing Unsafe code: {e}")


@app.route("/<path:path>", methods=["GET", "POST"])
@app.route("/", methods=["GET", "POST"])
@auth.login_required
def unsafe_exec(path: str | None = None):
    try:
        unsafe = Unsafe.from_request()
    except Exception as e:
        return f"Invalid Unsafe data in request: {e}", 400

    cache_key: CacheKey | None = None
    if unsafe.use_cache:
        match (unsafe.cache_key_override, unsafe.cache_kwargs):
            case (cache_key_override, _):
                cache_key = cache_key_override
            case (None, False):
                cache_key = CacheKey(path)
            case (None, True):
                cache_key = CacheKey(path, unsafe.kwargs_b64)
        logging.info(
            "Using cache for endpoint %s with key: %s",
            path,
            cache_key,
        )

        if cache_key in _SERVER.cache:
            logging.info("Cache hit; returning for %s", cache_key)
            return _SERVER.cache[cache_key]
        else:
            logging.info("Cache miss: %s", cache_key)

    try:
        result = unsafe.unsafe_exec(request)
        if cache_key:
            _SERVER.cache[cache_key] = result
            logging.info("Cached result for %s", cache_key)
        return result
    except Exception as e:
        return f"Error executing Unsafe code: {e}", 500


if __name__ == "__main__":
    auth = BasicAuth(enabled=args.auth_enabled)
    auth.add(*args.auth.split(":"))
    Server.serve(address=args.address, port=args.port, auth=auth)
