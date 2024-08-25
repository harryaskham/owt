import argparse
import base64
import dataclasses
import hashlib
import json
import logging
import os
from dataclasses import dataclass
from logging.config import dictConfig
from typing import Any, Callable, Optional, TypedDict, Unpack
from owt import summat

from flask import Flask, Response, request, Request
from flask_cors import CORS
from flask_httpauth import HTTPBasicAuth

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
parser.add_argument(
    "--auth",
    default=os.environ.get("OWT_AUTH", None),
    help="Basic auth username:password_sha256. --auth for owt:owt",
)

try:
    args = parser.parse_args()
except argparse.ArgumentError as e:
    logging.error(f"Error parsing arguments: {e}")
    exit(1)


app = Flask(
    __name__  # , static_url_path="", static_folder="static", template_folder="example"
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
    usernameToSHA256: dict[str, str] = dataclasses.field(default_factory=dict)

    @classmethod
    def maybe_single_user(cls, auth_str: str | None) -> Optional["BasicAuth"]:
        if not auth_str:
            return None
        auth = cls()
        auth.add(*auth_str.split(":"))
        return auth

    def add(self, username: str, password_sha256: str):
        self.usernameToSHA256[username] = password_sha256
        return self

    def with_default_user(self) -> "BasicAuth":
        self.add("owt", PlaintextPassword("owt").sha256())
        return self

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
    auth: BasicAuth | None = None

    @classmethod
    def serve(cls, **kwargs):
        global _SERVER
        _SERVER = cls(**kwargs)
        print(f"Owt starting on {_SERVER.address}:{_SERVER.port}")
        if not app.config.get('TESTING'):
            app.run(port=_SERVER.port, host=_SERVER.address)

    @classmethod
    def sing(cls) -> "Server":
        global _SERVER
        if not _SERVER:
            raise RuntimeError("Server not started")
        return _SERVER


_SERVER: Server | None = None


@auth.verify_password
def verify(username, password):
    server = Server.sing()
    if not server.auth:
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
    # Code to run, defining a Callable[[Request, ...], Response] with a function of the expected name.
    code_b64: str

    # The function to run in the given code.
    # If not provided, defaults to "run". Must take request as its first argument; the remaining are any kwargs provided.
    fn_name: str = "run"

    # Kwargs to pass to the run function
    kwargs_b64: str | None = None

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
    def from_request(cls, request: Request) -> "Unsafe":
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

    def unsafe_exec_fn(self) -> Callable[[summat.Adaptor], Response]:
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

    def unsafe_exec(self) -> Any:
        try:
            logging.info("Running with kwargs: %s", self.kwargs)
            return self.unsafe_exec_fn()(**self.kwargs)
        except Exception as e:
            raise RuntimeError(f"Error executing Unsafe code: {e}")


@app.route("/<path:path>", methods=["GET", "POST"])
@app.route("/", methods=["GET", "POST"])
@auth.login_required
def unsafe_exec(path: str | None = None) -> Any:
    return _run_unsafe_exec(path, request)


def _run_unsafe_exec(maybe_path: str | None, request: Request) -> Any:
    path = maybe_path or "/"
    try:
        unsafe = Unsafe.from_request(request)
    except Exception as e:
        return f"Invalid Unsafe data in request: {e}", 400

    cache_key: CacheKey | None = None
    if unsafe.use_cache:
        match (unsafe.cache_key_override, unsafe.cache_kwargs):
            case (cache_key_override, _):
                cache_key = cache_key_override
            case (None, False):
                cache_key = CacheKey(path=path)
            case (None, True):
                cache_key = CacheKey(path=path, kwargs_b64=unsafe.kwargs_b64)
        logging.info(
            "Using cache for endpoint %s with key: %s",
            path,
            cache_key,
        )

        if cache_key in Server.sing().cache:
            logging.info("Cache hit; returning for %s", cache_key)
            return Server.sing().cache[cache_key]
        else:
            logging.info("Cache miss: %s", cache_key)

    try:
        result = unsafe.unsafe_exec()
        if cache_key:
            Server.sing().cache[cache_key] = result
            logging.info("Cached result for %s", cache_key)
        return result
    except Exception as e:
        return f"Error executing Unsafe code: {e}", 500



def main():
    Server.serve(
        address=args.address,
        port=args.port,
        auth=BasicAuth.maybe_single_user(args.auth),
    )


if __name__ == "__main__":
    main()